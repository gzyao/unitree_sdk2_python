#!/usr/bin/env python3
"""
避障检测 + 比心动作脚本

特性：
- 仅在进入比心阶段时发送一次 Heart 命令，不会重复发送
- 比心完成后增加宽限期（post_heart_grace），在窗口内忽略静止检测，给巡航恢复时间
- 冷却时间（heart_cooldown）与“比心后必须再次运动”双重条件，避免频繁触发
- 使用线程锁保护回调与主循环共享状态，避免并发竞态
"""

import time
import sys
import math
import threading

from unitree_sdk2py.core.channel import ChannelSubscriber, ChannelFactoryInitialize
from unitree_sdk2py.idl.default import unitree_go_msg_dds__LowState_
from unitree_sdk2py.idl.unitree_go.msg.dds_ import LowState_
from unitree_sdk2py.go2.sport.sport_client import SportClient
import logging
logging.basicConfig(
    filename='/home/unitree/unitree_sdk2_python/example/go2/low_level/cruise_heart_hzAI.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class ObstacleHeartController:
    def __init__(self):
        # 状态变量
        self.low_state = None
        self.imu_state = None

        # 统计信息
        self.update_count = 0
        self.start_time = time.time()

        # 运动/动作状态
        self.is_stopped = False # 狗是否在静止状态
        self.is_doing_heart = False# 比心是否在静止状态

        # 静止检测参数
        self.static_threshold = 0.1   # 陀螺仪静止阈值（rad/s）
        self.static_duration = 8    # 静止持续时间阈值（秒）
        self.last_movement_time = time.time()# 静止前最后移动时间

        # 比心动作状态机
        self.heart_phase = 0
        self.heart_start_time = 0.0
        self.heart_command_sent = False

        # 触发控制（防频繁）
        self.last_heart_time = 0.0
        self.heart_cooldown_s = 10.0  # 比心完成后的冷却时间（秒）
        self.has_moved_since_heart = True  # 比心后需检测到再次运动，才允许再次触发

        # 比心完成后的宽限期（在此时间内忽略静止检测，给自动巡航恢复时间）
        self.post_heart_grace_s = 4
        self.post_heart_grace_until = 0.0

        # 客户端
        self.sport_client = None

        # 并发锁
        self._lock = threading.Lock()

        # 比心次数
        self.heart_count=0

    def Init(self):
        # 只订阅低层状态，不主动介入运动控制
        self.lowstate_subscriber = ChannelSubscriber("rt/lowstate", LowState_)
        self.lowstate_subscriber.Init(self.LowStateMessageHandler, 10)# 注册一个监听

        # 初始化 SportClient（用于比心动作）
        self.sport_client = SportClient()
        self.sport_client.SetTimeout(10.0)
        self.sport_client.Init()

    def Start(self):
        # 当前不需要额外线程
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
            # 比心期间的“运动”不计入恢复运动
            if not self.is_doing_heart:
                self.has_moved_since_heart = True

    def _mark_motion_grace(self):
        """宽限期内的运动标记：
        仅将状态视为非静止并刷新时间戳，不改变 has_moved_since_heart。
        用于避免宽限期内的“伪运动”满足再次触发条件。
        """
        with self._lock:
            self.is_stopped = False
            self.last_movement_time = time.time()

    def _mark_static_if_new(self):
        with self._lock:
            if not self.is_stopped:
                self.is_stopped = True # stoped 是go在静止状态
                self.last_movement_time = time.time() # 最后移动时间

    def CheckObstacleStatus(self):
        """检测是否长时间静止，从而触发比心动作的候选条件。"""
        imu = self._get_imu_snapshot()
        if imu is None:
            print("未获取到当前的IMU状态信息!!")
            return

        # 动作完成后的宽限期内，视为正在运动，避免立刻再次触发
        with self._lock:
            in_grace_period = (time.time() < self.post_heart_grace_until)# 4s 内 是true
        if in_grace_period:
            self._mark_motion_grace()
            return

        try:
            gyro = imu.gyroscope
            gyro_magnitude = math.sqrt(gyro[0] ** 2 + gyro[1] ** 2 + gyro[2] ** 2)
            if gyro_magnitude < self.static_threshold:
                # 静止
                self._mark_static_if_new()
            else:
                # 有运动
                self._mark_motion()


            # 触发条件：静止持续超过阈值 + 冷却期结束 + 比心后发生过再次运动
            with self._lock:
                now = time.time()
                if self.heart_count > 1: # 看正常结束 哪几个是false 是false的都不正常
                    # print(self.is_stopped)
                    # print((now - self.last_movement_time) > self.static_duration)
                    # print((now - self.last_heart_time) > self.heart_cooldown_s)
                    # print(self.has_moved_since_heart)
                    # print(not self.is_doing_heart)
                    logging.info(f"is_stopped: {self.is_stopped}, last_movement_time: {now - self.last_movement_time}, last_heart_time: {now - self.last_heart_time}, has_moved_since_heart: {self.has_moved_since_heart}, is_doing_heart: {self.is_doing_heart}")
                eligible = (
                    self.is_stopped
                    and (now - self.last_movement_time) > self.static_duration
                    and (now - self.last_heart_time) > self.heart_cooldown_s
                    and self.has_moved_since_heart
                    and not self.is_doing_heart
                )
            if eligible:
                self.StartHeartAction()

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
            # 比心即将发生，要求“必须再次运动后”才允许下一次触发
            self.has_moved_since_heart = False

    def ExecuteHeartAction(self):
        """执行比心动作状态机（由主循环周期性调用）。"""
        with self._lock:
            if not self.is_doing_heart:
                return
            current_time = time.time()
            elapsed_time = current_time - self.heart_start_time
            phase = self.heart_phase

        # 相位 0：准备阶段（等待 1s）
        if phase == 0:
            print("💖 准备比心动作...")
            if elapsed_time > 1.0:
                with self._lock:
                    self.heart_phase = 1
                print("💖 开始比心动作...")

        # 相位 1：只发送一次 Heart 指令，然后进入等待完成阶段
        elif phase == 1:
            with self._lock:
                already_sent = self.heart_command_sent
            if not already_sent:
                ret = self.safe_call(self.sport_client, "Heart")# 0 成功
                self.heart_count+=1
                print(f"💖 比心动作执行结果: {ret}")
                with self._lock:
                    self.heart_command_sent = True
                    self.heart_phase = 2  # 进入等待完成阶段
                    self.last_heart_time = time.time()

        # 相位 2：等待动作完成（总时长约 4~5s），然后退出
        elif phase == 2:
            print(elapsed_time)
            if elapsed_time > 5.0:
                print("✅ 比心动作完成！")
                with self._lock:
                    self.is_doing_heart = False
                    self.is_stopped = False
                    # 动作完成后刷新时间戳，并开启宽限期，给自动巡航一个恢复窗口
                    self.last_movement_time = time.time()
                    self.post_heart_grace_until = time.time() + self.post_heart_grace_s
                    # 不在此处设置 has_moved_since_heart=True，必须检测到真实运动后再置真
                print("🔄 已退出比心流程，等待恢复巡航/再次运动...")

    def ProcessHeartAction(self):
        if self.is_doing_heart:
            self.ExecuteHeartAction()


def main():
    print("🤖 避障检测 + 比心动作程序（稳定版）")
    print("=" * 60)
    print("🎯 功能：检测静止超过阈值后自动触发一次‘比心’动作（会发送一次 Heart 命令）")
    print("💡 通过陀螺仪/加速度计推断是否静止，默认阈值：角速度<0.1rad/s 且持续>8s")
    print("💡 动作完成后进入冷却（默认10s），且需要再次发生运动后才允许再次触发")
    print("💡 动作完成后提供 4s 宽限期，避免立即再次触发，保障巡航恢复")
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

    controller = ObstacleHeartController()
    controller.Init()
    controller.Start()

    print("🚀 程序运行中...")
    print("🔍 实时监控IMU状态进行静止检测与比心触发")
    print("🛡️ 已启用：一次性 Heart 调用、冷却与并发保护、动作后宽限期")
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


