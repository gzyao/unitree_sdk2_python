from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.go2.video.video_client import VideoClient
import cv2
import numpy as np
import sys
import subprocess as sp
import threading
import time

def start_rtsp_server():
    # RTSP服务器命令
    command = [
        'ffmpeg',
        '-f', 'rawvideo',
         '-pix_fmt', 'bgr24',
        '-s', '1920x1080',  # 使用更标准的分辨率
        '-r', '30',       # 帧率
        '-i', '-',        # 从管道读取输入
        '-c:v', 'libx264',
        '-preset', 'ultrafast',
        '-tune', 'zerolatency',
        '-f', 'rtsp',
        '-rtsp_transport', 'tcp',
        'rtsp://0.0.0.0:8554/go2_camera'  # RTSP URL
    ]
    
    try:
        # 启动FFmpeg进程
        process = sp.Popen(command, stdin=sp.PIPE, stderr=sp.PIPE)
        return process
    except Exception as e:
        print(f"启动RTSP服务器时出错: {e}")
        return None

if __name__ == "__main__":
    try:
        if len(sys.argv)>1:
            ChannelFactoryInitialize(0, sys.argv[1])
        else:
            ChannelFactoryInitialize(0)

        client = VideoClient()  # Create a video client
        client.SetTimeout(3.0)
        client.Init()

        # 启动RTSP服务器
        rtsp_process = start_rtsp_server()
        if rtsp_process is None:
            print("无法启动RTSP服务器，程序退出")
            sys.exit(1)
            
        print("RTSP流已启动，可以通过 rtsp://localhost:8554/go2_camera 访问")

        code, data = client.GetImageSample()
        if code != 0:
            print(f"获取图像样本失败，错误码: {code}")
            sys.exit(1)

        # Request normal when code==0
        while code == 0:
            try:
                # Get Image data from Go2 robot
                code, data = client.GetImageSample()
                if code != 0:
                    print(f"获取图像样本失败，错误码: {code}")
                    break
                # Convert to numpy image
                image_data = np.frombuffer(bytes(data), dtype=np.uint8)
                image = cv2.imdecode(image_data, cv2.IMREAD_COLOR)
                
                if image is None:
                    print("图像解码失败")
                    continue

                # 检查图像尺寸
                height, width = image.shape[:2]
                if width != 1920 or height != 1080:
                    print(f"图像尺寸不匹配: {width}x{height}，调整为1920x1080")
                    image = cv2.resize(image, (1920, 1080))

                # 将帧写入RTSP流
                try:
                    rtsp_process.stdin.write(image.tobytes())
                except Exception as e:
                    print(f"写入RTSP流时出错: {e}")
                    break

                # Display image
                #cv2.imshow("front_camera", image)
                # Press ESC to stop
                #if cv2.waitKey(20) == 27:
                #    break

            except Exception as e:
                print(f"处理图像时出错: {e}")
                break

    except Exception as e:
        print(f"程序运行出错: {e}")
    finally:
        if rtsp_process:
            try:
                rtsp_process.stdin.close()
                rtsp_process.wait(timeout=5)
            except Exception as e:
                print(f"清理资源时出错: {e}")

