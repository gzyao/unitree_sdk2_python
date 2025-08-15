#!/usr/bin/env python3
"""
简化的机器狗Move命令测试脚本
功能：测试指定速度和时间的Move命令
"""

import time
import sys
import argparse
from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.go2.sport.sport_client import SportClient


def safe_call(client, method_name, *args, **kwargs):
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


def test_move(vx, duration, network_interface=None):
    """测试Move命令"""
    print("🤖 简化的机器狗Move测试脚本")
    print("=" * 50)
    
    # 初始化
    if network_interface:
        ChannelFactoryInitialize(0, network_interface)
        print(f"🌐 使用网络接口: {network_interface}")
    else:
        ChannelFactoryInitialize(0)
        print("🌐 使用默认网络接口")
    
    # 创建客户端
    sport_client = SportClient()
    sport_client.SetTimeout(10.0)
    sport_client.Init()
    
    print(f"🧪 测试参数: vx={vx} m/s, 持续时间={duration} 秒")
    print("=" * 50)
    
    # 确保机器人站立
    print("🦵 确保机器人站立...")
    safe_call(sport_client, "StandUp")
    time.sleep(2)
    
    # 确保停止之前的移动
    print("🛑 停止之前的移动...")
    safe_call(sport_client, "StopMove")
    time.sleep(1)
    
    # 记录开始时间
    start_time = time.time()
    
    # 执行Move命令
    print(f"🚀 开始执行Move({vx}, 0, 0)...")
    ret = safe_call(sport_client, "Move", vx, 0, 0)
    print(f"📤 Move命令发送结果: {ret}")
    
    if ret == 0:
        print(f"✅ Move命令发送成功，等待 {duration} 秒...")
        
        # 等待指定时间
        time.sleep(duration)
        
        # 停止移动
        print("🛑 停止移动...")
        safe_call(sport_client, "StopMove")
        
        # 计算实际执行时间
        actual_duration = time.time() - start_time
        print(f"⏱️  实际执行时间: {actual_duration:.2f} 秒")
        
        if actual_duration >= duration * 0.8:  # 允许20%的误差
            print("✅ Move命令执行成功！")
        else:
            print(f"⚠️  Move命令执行时间不足，期望{duration}秒，实际{actual_duration:.2f}秒")
    else:
        print(f"❌ Move命令发送失败，错误码: {ret}")
    
    print("=" * 50)


def main():
    parser = argparse.ArgumentParser(description='机器狗Move命令测试')
    parser.add_argument('vx', type=float, help='前进速度 (m/s)')
    parser.add_argument('duration', type=float, help='持续时间 (秒)')
    parser.add_argument('--interface', '-i', type=str, help='网络接口 (如 eth0, wlan0)')
    
    args = parser.parse_args()
    
    # 参数验证
    if args.vx < 0:
        print("❌ 速度不能为负数")
        return
    
    if args.duration <= 0:
        print("❌ 持续时间必须大于0")
        return
    
    if args.vx > 2.0:
        print("⚠️  警告：速度较高，请确保环境安全")
        input("按Enter继续，或Ctrl+C取消...")
    
    try:
        test_move(args.vx, args.duration, args.interface)
    except KeyboardInterrupt:
        print("\n🛑 用户取消测试")
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")


if __name__ == "__main__":
    main() 