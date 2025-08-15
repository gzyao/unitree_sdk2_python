#!/usr/bin/env python3
"""
机器狗Move命令测试脚本
功能：系统性地测试Move命令在不同参数下的行为
"""

import time
import sys
from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.go2.sport.sport_client import SportClient


class MoveTestClient:
    def __init__(self):
        self.sport_client = SportClient()
        self.sport_client.SetTimeout(10.0)
        self.sport_client.Init()
        
        print("🧪 机器狗Move命令测试脚本")
        print("=" * 60)
        print("🎯 功能：系统测试Move命令的行为")
        print("💡 按 Ctrl+C 退出程序")
        print("=" * 60)

    def safe_call(self, client, method_name, *args, **kwargs):
        """安全调用方法"""
        try:
            method = getattr(client, method_name)
            if callable(method):
                return method(*args, **kwargs)
            else:
                print(f"⚠️  {method_name} 不是可调用的方法")
                return None
        except AttributeError:
            print(f"❌ 方法 {method_name} 不存在")
            return None
        except Exception as e:
            print(f"❌ 调用 {method_name} 时出错: {e}")
            return None

    def test_single_move(self, vx, vy, vyaw, duration, description):
        """测试单个Move命令"""
        print(f"\n🧪 测试: {description}")
        print(f"📊 参数: vx={vx}, vy={vy}, vyaw={vyaw}, 持续时间={duration}秒")
        
        # 确保停止之前的移动
        self.safe_call(self.sport_client, "StopMove")
        time.sleep(1)
        
        # 记录开始时间
        start_time = time.time()
        
        # 执行Move命令
        print(f"🚀 开始执行Move({vx}, {vy}, {vyaw})...")
        ret = self.safe_call(self.sport_client, "Move", vx, vy, vyaw)
        print(f"📤 Move命令发送结果: {ret}")
        
        # 等待指定时间
        print(f"⏱️  等待 {duration} 秒...")
        time.sleep(duration)
        
        # 停止移动
        print("🛑 停止移动...")
        self.safe_call(self.sport_client, "StopMove")
        
        # 计算实际执行时间
        actual_duration = time.time() - start_time
        print(f"⏱️  实际执行时间: {actual_duration:.2f} 秒")
        
        return ret

    def test_speed_series(self):
        """测试不同速度的系列"""
        print("\n" + "="*60)
        print("🏃 测试不同速度的Move命令")
        print("="*60)
        
        speeds = [0.1, 0.3, 0.5, 0.8, 1.0, 1.5]
        
        for speed in speeds:
            self.test_single_move(
                vx=speed, 
                vy=0, 
                vyaw=0, 
                duration=3, 
                description=f"前进速度 {speed} m/s"
            )
            time.sleep(2)  # 测试间隔

    def test_direction_series(self):
        """测试不同方向的Move命令"""
        print("\n" + "="*60)
        print("🧭 测试不同方向的Move命令")
        print("="*60)
        
        directions = [
            (0.5, 0, 0, "前进"),
            (0, 0.5, 0, "右移"),
            (0, -0.5, 0, "左移"),
            (0, 0, 0.5, "逆时针转向"),
            (0, 0, -0.5, "顺时针转向"),
            (0.3, 0.3, 0, "斜向前进"),
        ]
        
        for vx, vy, vyaw, desc in directions:
            self.test_single_move(
                vx=vx, 
                vy=vy, 
                vyaw=vyaw, 
                duration=3, 
                description=desc
            )
            time.sleep(2)

    def test_duration_series(self):
        """测试不同持续时间的Move命令"""
        print("\n" + "="*60)
        print("⏱️  测试不同持续时间的Move命令")
        print("="*60)
        
        durations = [1, 2, 3, 5, 8]
        
        for duration in durations:
            self.test_single_move(
                vx=0.5, 
                vy=0, 
                vyaw=0, 
                duration=duration, 
                description=f"前进0.5m/s，持续{duration}秒"
            )
            time.sleep(2)

    def test_continuous_move(self):
        """测试连续Move命令"""
        print("\n" + "="*60)
        print("🔄 测试连续Move命令")
        print("="*60)
        
        print("🧪 测试: 连续发送Move命令")
        print("📊 参数: 连续发送前进命令")
        
        # 连续发送Move命令
        for i in range(5):
            print(f"🚀 发送第 {i+1} 个Move命令...")
            ret = self.safe_call(self.sport_client, "Move", 0.3, 0, 0)
            print(f"📤 Move命令 {i+1} 发送结果: {ret}")
            time.sleep(1)
        
        # 停止
        print("🛑 停止移动...")
        self.safe_call(self.sport_client, "StopMove")

    def test_rapid_commands(self):
        """测试快速发送命令"""
        print("\n" + "="*60)
        print("⚡ 测试快速发送命令")
        print("="*60)
        
        print("🧪 测试: 快速发送不同方向的Move命令")
        
        commands = [
            (0.3, 0, 0, "前进"),
            (0, 0.3, 0, "右移"),
            (0, 0, 0.3, "转向"),
            (-0.3, 0, 0, "后退"),
        ]
        
        for vx, vy, vyaw, desc in commands:
            print(f"🚀 快速发送: {desc}")
            ret = self.safe_call(self.sport_client, "Move", vx, vy, vyaw)
            print(f"📤 结果: {ret}")
            time.sleep(0.5)  # 快速切换
        
        print("🛑 停止移动...")
        self.safe_call(self.sport_client, "StopMove")

    def run_interactive_test(self):
        """交互式测试"""
        print("\n" + "="*60)
        print("🎮 交互式测试模式")
        print("="*60)
        print("💡 输入格式: vx,vy,vyaw,duration")
        print("💡 示例: 0.3,0,0,3")
        print("💡 输入 'quit' 退出")
        print("💡 输入 'stop' 停止移动")
        
        try:
            while True:
                user_input = input("\n请输入测试参数 (vx,vy,vyaw,duration): ")
                
                if user_input.lower() == 'quit':
                    break
                elif user_input.lower() == 'stop':
                    self.safe_call(self.sport_client, "StopMove")
                    print("✅ 已停止移动")
                    continue
                
                try:
                    # 解析输入
                    parts = user_input.split(',')
                    if len(parts) != 4:
                        print("❌ 输入格式错误，需要4个参数")
                        continue
                    
                    vx = float(parts[0])
                    vy = float(parts[1])
                    vyaw = float(parts[2])
                    duration = float(parts[3])
                    
                    self.test_single_move(
                        vx=vx, 
                        vy=vy, 
                        vyaw=vyaw, 
                        duration=duration, 
                        description=f"自定义测试: vx={vx}, vy={vy}, vyaw={vyaw}, duration={duration}"
                    )
                    
                except ValueError:
                    print("❌ 参数格式错误，请输入数字")
                except Exception as e:
                    print(f"❌ 测试出错: {e}")
                    
        except KeyboardInterrupt:
            print("\n🛑 用户中断测试")

    def run(self):
        """运行测试"""
        print("🚀 开始Move命令测试...")
        print("⚠️  请确保机器狗周围有足够空间")
        print("⚠️  建议在平坦地面上测试")
        input("按 Enter 键开始测试...")
        
        try:
            while True:
                print("\n" + "="*60)
                print("🧪 Move命令测试菜单")
                print("="*60)
                print("1. 测试不同速度")
                print("2. 测试不同方向")
                print("3. 测试不同持续时间")
                print("4. 测试连续Move命令")
                print("5. 测试快速发送命令")
                print("6. 交互式测试")
                print("0. 退出")
                print("="*60)
                
                choice = input("请选择测试类型 (0-6): ")
                
                if choice == '0':
                    break
                elif choice == '1':
                    self.test_speed_series()
                elif choice == '2':
                    self.test_direction_series()
                elif choice == '3':
                    self.test_duration_series()
                elif choice == '4':
                    self.test_continuous_move()
                elif choice == '5':
                    self.test_rapid_commands()
                elif choice == '6':
                    self.run_interactive_test()
                else:
                    print("❌ 无效选择")
                
                input("\n按 Enter 键继续...")
                
        except KeyboardInterrupt:
            print("\n🛑 程序被用户中断")
        except Exception as e:
            print(f"❌ 程序运行出错: {e}")
        finally:
            # 确保停止移动
            self.safe_call(self.sport_client, "StopMove")
            print("✅ 程序已退出")


if __name__ == "__main__":
    print("🤖 机器狗Move命令测试脚本")
    print("=" * 60)
    
    # 初始化网络连接
    if len(sys.argv) > 1:
        ChannelFactoryInitialize(0, sys.argv[1])
        print(f"🌐 使用网络接口: {sys.argv[1]}")
    else:
        ChannelFactoryInitialize(0)
        print("🌐 使用默认网络接口")

    # 创建并运行测试客户端
    test_client = MoveTestClient()
    test_client.run() 