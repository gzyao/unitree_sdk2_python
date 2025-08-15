#!/usr/bin/env python3
"""
机器狗摄像头简单录制脚本
功能：自动录制10秒摄像头画面并保存视频
基于capture_image.py的实现
"""

import cv2
import time
import sys
import argparse
import numpy as np
from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.go2.video.video_client import VideoClient


def simple_record_camera(network_interface=None, duration=10):
    """简单录制摄像头画面"""
    
    # 初始化网络接口
    if network_interface:
        ChannelFactoryInitialize(0, network_interface)
        print(f"🌐 使用网络接口: {network_interface}")
    else:
        ChannelFactoryInitialize(0)
        print("🌐 使用默认网络接口")
    
    # 初始化摄像头客户端
    client = VideoClient()
    client.SetTimeout(3.0)
    client.Init()
    
    print(f"📹 开始自动录制 {duration} 秒摄像头画面...")
    
    # 获取第一帧来确定视频尺寸
    code, data = client.GetImageSample()
    if code != 0:
        print(f"❌ 无法获取摄像头画面，错误码: {code}")
        return False
    
    # 转换为numpy图像
    image_data = np.frombuffer(bytes(data), dtype=np.uint8)
    first_frame = cv2.imdecode(image_data, cv2.IMREAD_COLOR)
    
    height, width = first_frame.shape[:2]
    print(f"📐 视频尺寸: {width}x{height}")
    
    # 创建视频文件名
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"go2_camera_{timestamp}_{duration}s.mp4"
    
    # 创建视频写入器
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video_writer = cv2.VideoWriter(filename, fourcc, 10, (width, height))
    
    if not video_writer.isOpened():
        print("❌ 无法创建视频文件")
        return False
    
    print(f"🎬 开始录制: {filename}")
    print("⏱️  录制中...")
    
    start_time = time.time()
    frame_count = 0
    
    try:
        while time.time() - start_time < duration:
            # 获取图像
            code, data = client.GetImageSample()
            if code != 0:
                print("❌ 无法获取图像")
                time.sleep(0.1)
                continue
            
            # 转换为numpy图像
            image_data = np.frombuffer(bytes(data), dtype=np.uint8)
            image = cv2.imdecode(image_data, cv2.IMREAD_COLOR)
            
            # 写入视频
            video_writer.write(image)
            frame_count += 1
            
            # 显示进度
            elapsed = time.time() - start_time
            remaining = duration - elapsed
            print(f"\r⏱️  录制中... {elapsed:.1f}s / {duration}s (剩余 {remaining:.1f}s)", end="", flush=True)
            
            time.sleep(0.1)  # 约10 FPS
        
        print(f"\n✅ 录制完成！")
        print(f"📊 统计信息:")
        print(f"   - 文件名: {filename}")
        print(f"   - 录制时长: {duration} 秒")
        print(f"   - 总帧数: {frame_count}")
        print(f"   - 平均帧率: {frame_count/duration:.1f} FPS")
        print(f"   - 视频尺寸: {width}x{height}")
        
        return True
        
    except KeyboardInterrupt:
        print("\n🛑 录制被用户中断")
        return False
    except Exception as e:
        print(f"\n❌ 录制过程中出错: {e}")
        return False
    finally:
        # 释放资源
        video_writer.release()
        print("🧹 资源已释放")


def main():
    parser = argparse.ArgumentParser(description='机器狗摄像头简单录制')
    parser.add_argument('--interface', '-i', type=str, help='网络接口 (如 eth0, wlan0)')
    parser.add_argument('--duration', '-d', type=int, default=10, help='录制时长(秒) (默认: 10)')
    
    args = parser.parse_args()
    
    print("📹 机器狗摄像头简单录制系统")
    print("=" * 50)
    print(f"⏱️  录制时长: {args.duration} 秒")
    print(f"🌐 网络接口: {args.interface or '默认'}")
    print("=" * 50)
    
    try:
        success = simple_record_camera(args.interface, args.duration)
        if success:
            print("🎉 录制成功！视频文件已保存到当前目录")
        else:
            print("❌ 录制失败")
    except Exception as e:
        print(f"❌ 程序运行出错: {e}")


if __name__ == "__main__":
    main() 