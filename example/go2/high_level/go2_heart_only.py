#!/usr/bin/env python3
"""
机器狗巡航中的比心控制脚本
功能：在机器狗巡航过程中，临时控制比心动作，然后恢复巡航
"""

import time
import sys
from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.go2.sport.sport_client import SportClient


class HeartOnlyClient:
    def __init__(self):
        self.sport_client = SportClient()
        self.sport_client.SetTimeout(10.0)
        self.sport_client.Init()
        
        print("💖 机器狗巡航中的比心控制脚本")
        print("=" * 60)
        print("🎯 功能：在巡航过程中临时控制比心动作")
        print("💡 比心完成后自动恢复巡航状态")
        print("💡 按 Ctrl+C 退出程序")
        print("💡 直接回车也能触发比心动作")
        print("=" * 60)

    def safe_call(self, client, method_name, *args, **kwargs):
        """安全调用方法，如果方法不存在则跳过"""
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

    def perform_heart(self):
        """执行比心动作，然后恢复巡航"""
        print("💖 机器狗正在比心... 💖")
        
        # 执行比心动作
        ret = self.safe_call(self.sport_client, "Heart")
        print(f"比心动作执行结果: {ret}")
        
        # 等待比心动作完成
        time.sleep(4)
        
        print("✅ 比心动作完成！")
        print("🔄 恢复巡航状态...")
        
        # 这里不需要额外的恢复命令，因为巡航程序会自动接管控制
        # 比心动作完成后，巡航程序会继续工作
        print("✅ 已恢复巡航状态")

    def run(self):
        """运行主程序"""
        print("🚀 开始运行巡航比心控制脚本...")
        print("💡 输入任意内容或直接回车都会触发比心动作")
        print("💡 比心完成后自动恢复巡航")
        print("💡 按 Ctrl+C 退出")
        print("-" * 60)
        
        try:
            while True:
                # 获取用户输入
                user_input = input("输入任意内容或直接回车触发比心 (Ctrl+C退出): ")
                
                # 不管输入什么内容（包括空内容），都执行比心
                self.perform_heart()
                
        except KeyboardInterrupt:
            print("\n🛑 程序被用户中断")
        except Exception as e:
            print(f"❌ 程序运行出错: {e}")
        finally:
            print("✅ 程序已退出")


if __name__ == "__main__":
    print("🤖 机器狗巡航中的比心控制脚本")
    print("=" * 60)
    
    # 初始化网络连接
    if len(sys.argv) > 1:
        ChannelFactoryInitialize(0, sys.argv[1])
        print(f"🌐 使用网络接口: {sys.argv[1]}")
    else:
        ChannelFactoryInitialize(0)
        print("🌐 使用默认网络接口")

    # 创建并运行比心客户端
    heart_client = HeartOnlyClient()
    heart_client.run() 