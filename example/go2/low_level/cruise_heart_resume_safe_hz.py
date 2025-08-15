#!/usr/bin/env python3
"""
避障检测 + 比心动作脚本（恢复友好版）

目标行为：
- 挡住机器狗并让其静止满 8 秒后，触发一次“比心”
- 比心完成后：
  - 如果继续挡住并保持静止满 8 秒，才会触发下一次“比心”（不额外强制冷却）
  - 在这段期间任意时刻让开，均应能恢复自动巡航

策略要点：
- 仅在触发时对机器人发送一次 Heart 指令，平时不干预导航与运动
- 比心结束后，尝试调用“恢复/平衡站立”类接口（若存在）+ 短暂宽限期，帮助自动巡航顺利接管
- 通过 IMU 检测真实运动后，才允许下一次比心
"""

import time
import sys
import math
import threading

from unitree_sdk2py.core.channel import ChannelSubscriber, ChannelFactoryInitialize
from unitree_sdk2py.idl.unitree_go.msg.dds_ import LowState_
from unitree_sdk2py.go2.sport.sport_client import SportClient
import logging

logging.basicConfig(
    filename='/home/unitree/unitree_sdk2_python/example/go2/low_level/cruise_heart_hzAI.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class CruiseHeartResumeSafeController:
    def __init__(self):
        # 状态变量
        self.low_state = None
        self.imu_state = None

        # 统计信息
        self.update_count = 0
        self.start_time = time.time()

        # 运动/动作状态
        self.is_stopped = False
        self.is_doing_heart = False

        # 静止检测参数
        self.static_threshold = 0.1  # 陀螺仪静止阈值（rad/s）
        self.static_duration = 8.0  # 静止持续时间阈值（秒）
        self.last_movement_time = time.time()

        # 比心动作状态机
        self.heart_phase = 0
        self.heart_start_time = 0.0
        self.heart_command_sent = False

        # 触发控制
        self.last_heart_time = 0.0
        self.heart_cooldown_s = 0.0  # 不额外冷却：保证“继续挡住 8 秒”即可再次触发
        self.has_moved_since_heart = True  # 必须检测到真实运动后才允许下一次触发

        # 比心完成后的宽限期（在此时间内忽略静止检测，给自动巡航恢复窗口）
        self.post_heart_grace_s = 3.0
        self.post_heart_grace_until = 0.0

        # 比心总等待时间，用于估计动作结束时刻
        self.action_total_time_s = 5.0

        # 比心结束后的恢复检测窗口：如果 IMU 检测到运动则置位 has_moved_since_heart
        self.resume_check_window_s = 3.0
        self.resume_motion_threshold = 0.2  # 认为发生运动的角速度阈值（rad/s）

        # 客户端
        self.sport_client = None

        # 并发锁
        self._lock = threading.Lock()

        # 定义全局比心次数
        self.heart_count=0

    # 统计某个时刻 所有全局变量的信息
    def show_param(self):
        logging.info('展示全局状态变量:')
        logging.info(f'self.is_stopped: {self.is_stopped}')
        logging.info(f'self.is_doing_heart: {self.is_doing_heart}')
        logging.info(f'self.last_movement_time: {self.last_movement_time}')
        logging.info(f'self.heart_phase: {self.heart_phase}')
        logging.info(f'self.heart_start_time: {self.heart_start_time}')
        logging.info(f'self.heart_command_sent: {self.heart_command_sent}')
        logging.info(f'self.last_heart_time: {self.last_heart_time}')
        logging.info(f'self.heart_cooldown_s: {self.heart_cooldown_s}')
        logging.info(f'self.has_moved_since_heart: {self.has_moved_since_heart}')
        logging.info(f'self.heart_count: {self.heart_count}')

    def Init(self):
        # 只订阅低层状态，不主动介入运动控制
        self.lowstate_subscriber = ChannelSubscriber("rt/lowstate", LowState_)
        logging.info(f'开启订阅监听...')
        self.lowstate_subscriber.Init(self.LowStateMessageHandler, 10)

        # 初始化 SportClient（用于比心动作）
        self.sport_client = SportClient()
        self.sport_client.SetTimeout(10.0)
        self.sport_client.Init()

    def Start(self):
        pass

    def safe_call(self, client, method_name, *args, **kwargs):
        """安全调用方法，如果方法不存在或出错则返回 None。"""
        try:
            method = getattr(client, method_name)
            if callable(method):
                return method(*args, **kwargs)
            else:
                print(f"⚠️  {method_name} 不是可调用的方法")
                return None
        except AttributeError:
            print(f"❌ 方法 {method_name} 不存在，跳过此动作")
            return None
        except Exception as e:
            print(f"❌ 调用 {method_name} 时出错: {e}")
            return None

    def LowStateMessageHandler(self, msg: LowState_):
        """低层状态消息回调：更新 IMU 状态并进行静止检测。"""
        with self._lock:
            self.low_state = msg
            self.imu_state = msg.imu_state
            self.update_count += 1
        # 在锁外进行检测，避免长时间占用锁
        self.CheckObstacleStatus()

    def _get_imu_snapshot(self):
        with self._lock:
            return self.imu_state

    def _mark_motion(self):
        with self._lock:
            self.is_stopped = False
            self.last_movement_time = time.time()
            # 比心期间的动作不计入“恢复运动”
            if not self.is_doing_heart:
                self.has_moved_since_heart = True

    def _mark_static_if_new(self):
        with self._lock:
            if not self.is_stopped:
                self.is_stopped = True
                self.last_movement_time = time.time()

    def _now_in_grace(self) -> bool:
        with self._lock:
            return time.time() < self.post_heart_grace_until

    def CheckObstacleStatus(self):
        """检测是否长时间静止，从而触发比心动作的候选条件。"""
        # 获取imu信息
        imu = self._get_imu_snapshot()

        if imu is None:
            print("未获取到当前的IMU状态信息!!")
            return

        # 动作完成后的宽限期：视为“正在运动”，避免立刻再次触发
        # 进一步解释宽限期 就是 狗在比心过程中，会随时走这，但是在比心中不应该判断比心，应该等一次比心结束再走
        if self._now_in_grace():
            self._mark_motion()
            logging.info(f'还在比心过程中 CheckObstacleStatus 不执行 观测...')
            return

        try:
            logging.info(f'第{self.heart_count} 次比心结束之后 开始新一轮判断是否继续比心')
            gyro = imu.gyroscope
            gyro_magnitude = math.sqrt(gyro[0] ** 2 + gyro[1] ** 2 + gyro[2] ** 2)

            if gyro_magnitude < self.static_threshold:
                logging.info(f'检测到人 发送静止信号...')
                # 静止
                self._mark_static_if_new()
            else:
                logging.info(f'没检测到人 运动中...')
                # 有运动
                self._mark_motion()

            # 触发条件：静止超过阈值 + 无冷却或冷却到期 + 比心后已再次运动 + 当前不在表演动作
            with self._lock:
                now = time.time()
                logging.info(f'判断是否满足比心条件')
                logging.info(f'(now - self.last_movement_time) > self.static_duration：{(now - self.last_movement_time) > self.static_duration}')
                logging.info(f'(now - self.last_heart_time) > self.heart_cooldown_s：{(now - self.last_heart_time) > self.heart_cooldown_s}')
                logging.info(f'self.has_moved_since_heart：{self.has_moved_since_heart}')
                logging.info(f'not self.is_doing_heart：{not self.is_doing_heart}')
                self.show_param()
                eligible = (
                        self.is_stopped
                        and (now - self.last_movement_time) > self.static_duration
                        and (now - self.last_heart_time) > self.heart_cooldown_s
                        and self.has_moved_since_heart
                        and not self.is_doing_heart
                )
                logging.info(f'{"满足比心" if eligible else "不满足比心"}')
            if eligible:
                logging.info(f'比心条件修改')
                self.StartHeartAction()
                self.show_param()

        except Exception as e:
            print(f"❌ 避障检测错误: {e}")
            self.CheckObstacleByAccelerometer()

    def CheckObstacleByAccelerometer(self):
        """使用加速度计作为静止检测的备选方案。"""
        imu = self._get_imu_snapshot()
        if imu is None:
            return

        try:
            accel = imu.accelerometer
            accel_magnitude = math.sqrt(accel[0] ** 2 + accel[1] ** 2 + accel[2] ** 2)
            if abs(accel_magnitude - 9.8) < 0.5:
                self._mark_static_if_new()
        except Exception as e:
            print(f"❌ 加速度计检测错误: {e}")

    def StartHeartAction(self):
        """开始比心动作：进入相位 0，并设置标记。"""
        with self._lock:
            print("💖 检测到静止达到条件，准备执行比心动作！")
            self.is_doing_heart = True
            self.heart_phase = 0
            self.heart_start_time = time.time()
            self.heart_command_sent = False
            # 比心即将发生：要求“必须再次运动后”才允许下一次触发
            self.has_moved_since_heart = False

    def ExecuteHeartAction(self):
        """执行比心动作状态机（由主循环周期性调用）。"""
        with self._lock:
            if not self.is_doing_heart:
                return
            current_time = time.time()
            elapsed_time = current_time - self.heart_start_time
            phase = self.heart_phase

        # 相位 0：准备阶段（等待 0.8s）
        if phase == 0:
            logging.info(f'phase:0 比心准备阶段')
            if elapsed_time > 0.8:
                with self._lock:
                    self.heart_phase = 1
                print("💖 开始比心动作...")

        # 相位 1：只发送一次 Heart 指令，然后进入等待完成阶段
        elif phase == 1:
            logging.info(f'phase:1 比心执行阶段')
            with self._lock:
                already_sent = self.heart_command_sent
            if not already_sent:
                logging.info(f'开始发送比心命令')
                ret = self.safe_call(self.sport_client, "Heart")
                logging.info(f'返回比心结果ret')
                self.heart_count+=1
                with self._lock:
                    self.heart_command_sent = True
                    self.heart_phase = 2  # 进入等待完成阶段
                    self.last_heart_time = time.time()
                    self.show_param()

        # 相位 2：等待动作完成（总时长约 4~5s），然后退出 + 恢复
        elif phase == 2:
            logging.info(f'phase:2 比心结束阶段')
            if elapsed_time > self.action_total_time_s:
                logging.info(f'比心动作结束...')
                self._finalize_heart_and_recover()


    def _finalize_heart_and_recover(self):
        print("✅ 比心动作完成！")
        # 状态清理 + 宽限期
        with self._lock:
            self.is_doing_heart = False
            self.is_stopped = False
            now = time.time()
            self.last_movement_time = now
            self.post_heart_grace_until = now + self.post_heart_grace_s
            self.show_param()
        logging.info(f'推出比心流程... 交环锁控制权')
        print("🔄 已退出比心流程，尝试恢复站立/平衡并交还控制权...")

        # # 试图将机器人带回“可被导航接管”的姿态（如果接口存在）
        # self.safe_call(self.sport_client, "RecoveryStand")
        # self.safe_call(self.sport_client, "RecoverStand")
        # self.safe_call(self.sport_client, "BalanceStand")
        # 有些固件可能需要一次轻量的站立以退出表演状态
        logging.info(f'发送让狗站立信息..')
        self.safe_call(self.sport_client, "StandUp")
        logging.info(f'信息发送完成....')
        # 在短窗口内观测 IMU，若检测到运动则置位“已再次运动”，便于下次触发放行
        # logging.info(f'短窗口内观测 IMU')
        # threading.Thread(target=self._resume_window_check, daemon=True).start()
        self.show_param()
    def _resume_window_check(self):
        deadline = time.time() + self.resume_check_window_s
        while time.time() < deadline:
            logging.info(f'在短窗口期内观测imu信息')
            imu = self._get_imu_snapshot()
            if imu is not None:
                try:
                    g = imu.gyroscope
                    gmag = math.sqrt(g[0] ** 2 + g[1] ** 2 + g[2] ** 2)
                    if gmag > self.resume_motion_threshold:
                        self._mark_motion()
                        print("▶️ 检测到已恢复运动，允许后续比心触发")
                        logging.info(f'短窗口期内测到已恢复运动，允许后续比心触发')
                        return
                except Exception:
                    pass
            time.sleep(0.05)

    def ProcessHeartAction(self):
        if self.is_doing_heart:
            self.ExecuteHeartAction()


def main():
    logging.info('狗避障检测脚本启动了....')
    print("🤖 避障检测 + 比心动作程序（恢复友好版）")
    print("=" * 60)
    print("🎯 功能：静止超 8s 触发一次‘比心’，表演结束后若持续挡住再静止 8s，才会再次触发")
    print("💡 表演期间不干预导航；表演结束后尝试恢复站立 + 短宽限，确保让路即可恢复巡航")
    print("💡 按 Ctrl+C 退出程序")
    print("=" * 60)
    input("按Enter键开始...")

    # 初始化通信
    if len(sys.argv) > 1:
        ChannelFactoryInitialize(0, sys.argv[1])
        print(f"🌐 使用网络接口: {sys.argv[1]}")
    else:
        ChannelFactoryInitialize(0)
        print("🌐 使用默认网络接口")

    controller = CruiseHeartResumeSafeController()
    controller.Init()
    controller.Start()

    print("🚀 程序运行中...")
    print("🔍 实时监控IMU状态进行静止检测与比心触发")
    print("🛡️ 已启用：一次性 Heart 调用、动作后恢复、短宽限、再次运动判定")
    print("-" * 60)

    try:
        while True:
            controller.ProcessHeartAction()
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n🛑 程序被用户中断")
        print(f"📈 总运行时间: {time.time() - controller.start_time:.1f}秒")
        print(f"📊 总更新次数: {controller.update_count}")
        sys.exit(0)


if __name__ == '__main__':
    main()
