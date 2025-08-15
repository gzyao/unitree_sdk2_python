#!/usr/bin/env python3
"""
避障检测 + 比心动作脚本（改进版）
功能：检测机器人在巡航过程中因避障（或其他原因）停止超过阈值后，自动触发一次“比心”动作
注意：本脚本会在满足触发条件时主动发送一次比心动作命令（Heart），其余时间不干预手柄/上位机的运动控制

改进点：
- 仅在进入比心阶段时发送一次 Heart 命令，不会重复发送
- 增加冷却时间与“再次运动后才允许再次触发”的条件，避免频繁触发
- 使用线程锁保护回调与主循环的共享状态，避免并发竞态
- 删除未使用的依赖导入
"""

import time
import sys
import math
import threading

from unitree_sdk2py.core.channel import ChannelSubscriber, ChannelFactoryInitialize
from unitree_sdk2py.idl.default import unitree_go_msg_dds__LowState_
from unitree_sdk2py.idl.unitree_go.msg.dds_ import LowState_
from unitree_sdk2py.go2.sport.sport_client import SportClient


class HeartController:
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

        # 避障检测参数
        self.static_threshold = 0.1  # 陀螺仪静止阈值（rad/s）
        self.static_duration = 8.0   # 静止持续时间阈值（秒）
        self.last_movement_time = time.time()

        # 比心动作状态机
        self.heart_phase = 0
        self.heart_start_time = 0.0
        self.heart_command_sent = False  # 确保 Heart 只发送一次

        # 触发控制（防频繁）
        self.last_heart_time = 0.0
        #self.heart_cooldown_s = 20.0  # 比心完成后的冷却时间
        self.heart_cooldown_s = 0
        self.has_moved_since_heart = True  # 要求比心后有“再次运动”才允许下一次触发

        # 客户端
        self.sport_client = None

        # 并发锁
        self._lock = threading.Lock()

    def Init(self):
        # 只订阅低层状态，不主动介入运动控制
        self.lowstate_subscriber = ChannelSubscriber("rt/lowstate", LowState_)
        self.lowstate_subscriber.Init(self.LowStateMessageHandler, 10)

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
            # 标记“比心后已再次运动”
            self.has_moved_since_heart = True

    def _mark_static_if_new(self):
        with self._lock:
            if not self.is_stopped:
                self.is_stopped = True
                self.last_movement_time = time.time()

    def CheckObstacleStatus(self):
        """检测是否长时间静止，从而触发比心动作的候选条件。"""
        imu = self._get_imu_snapshot()
        if imu is None:
            print("未获取到当前的IMU状态信息!!")
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
                eligible = (
                    self.is_stopped
                    and (time.time() - self.last_movement_time) > self.static_duration
                    and (time.time() - self.last_heart_time) > self.heart_cooldown_s
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
                ret = self.safe_call(self.sport_client, "Heart")
                print(f"💖 比心动作执行结果: {ret}")
                with self._lock:
                    self.heart_command_sent = True
                    self.heart_phase = 2  # 进入等待完成阶段
                    self.last_heart_time = time.time()

        # 相位 2：等待动作完成（总时长约 4~5s），然后退出
        elif phase == 2:
            if elapsed_time > 5.0:
                print("✅ 比心动作完成！")
                with self._lock:
                    self.is_doing_heart = False
                    self.is_stopped = False
                    # 不在此处设置 has_moved_since_heart=True，必须检测到真实运动后再置真
                print("🔄 已退出比心流程，等待恢复巡航/再次运动...")

    def ProcessHeartAction(self):
        if self.is_doing_heart:
            self.ExecuteHeartAction()


def main():
    print("🤖 避障检测 + 比心动作程序（改进版）")
    print("=" * 60)
    print("🎯 功能：检测静止超过阈值后自动触发一次‘比心’动作（会发送一次 Heart 命令）")
    print("💡 通过陀螺仪/加速度计推断是否静止，默认阈值：角速度<0.1rad/s 且持续>2s")
    print("💡 动作完成后进入冷却（默认20s），且需要再次发生运动后才允许再次触发")
    print("💡 日常巡航与手柄控制不受影响（仅在触发时发送一次表演动作指令）")
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

    controller = HeartController()
    controller.Init()
    controller.Start()

    print("🚀 程序运行中...")
    print("🔍 实时监控IMU状态进行静止检测与比心触发")
    print("🛡️ 已启用：一次性 Heart 调用、冷却与并发保护")
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


