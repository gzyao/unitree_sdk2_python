import time
import sys
from unitree_sdk2py.core.channel import ChannelSubscriber, ChannelFactoryInitialize
from unitree_sdk2py.idl.default import unitree_go_msg_dds__SportModeState_
from unitree_sdk2py.idl.unitree_go.msg.dds_ import SportModeState_
from unitree_sdk2py.go2.sport.sport_client import (
    SportClient,
    PathPoint,
    SPORT_PATH_POINT_SIZE,
)
import math

class TestOption:
    def __init__(self, name, id):
        self.name = name
        self.id = id

option_list = [
    TestOption(name="damp", id=0),         
    TestOption(name="stand_up", id=1),     
    TestOption(name="stand_down", id=2),   
    TestOption(name="move forward", id=3),         
    TestOption(name="move lateral", id=4),    
    TestOption(name="move rotate", id=5),  
    TestOption(name="stop_move", id=6),  
    TestOption(name="hand stand", id=7),
    TestOption(name="balanced stand", id=9),     
    TestOption(name="recovery", id=10),       
    TestOption(name="left flip", id=11),      
    TestOption(name="back flip", id=12),
    TestOption(name="free walk", id=13),  
    TestOption(name="free bound", id=14), 
    TestOption(name="free avoid", id=15),  
    TestOption(name="walk upright", id=17),
    TestOption(name="cross step", id=18),
    TestOption(name="free jump", id=19),
    TestOption(name="heart", id=20),
    TestOption(name="sit", id=21),
    TestOption(name="rise_sit", id=22),
    TestOption(name="hello", id=23),
    TestOption(name="stretch", id=24),
    TestOption(name="content", id=25),
    TestOption(name="dance1", id=26),
    TestOption(name="dance2", id=27),
    TestOption(name="front_flip", id=28),
    TestOption(name="front_jump", id=29),
    TestOption(name="front_pounce", id=30),
    TestOption(name="pose", id=31),
    TestOption(name="scrape", id=32),
    TestOption(name="static_walk", id=33),
    TestOption(name="trot_run", id=34),
    TestOption(name="classic_walk", id=35),
    TestOption(name="welcome_ceremony", id=36),
    TestOption(name="happy_dance", id=37),
    TestOption(name="exercise_routine_fixed", id=38),
    TestOption(name="back_flip_test", id=39),
    TestOption(name="obstacle_avoid_heart", id=40)
]

class UserInterface:
    def __init__(self):
        self.test_option_ = None

    def convert_to_int(self, input_str):
        try:
            return int(input_str)
        except ValueError:
            return None

    def terminal_handle(self):
        input_str = input("Enter id or name: \n")

        if input_str == "list":
            self.test_option_.name = None
            self.test_option_.id = None
            for option in option_list:
                print(f"{option.name}, id: {option.id}")
            return

        for option in option_list:
            if input_str == option.name or self.convert_to_int(input_str) == option.id:
                self.test_option_.name = option.name
                self.test_option_.id = option.id
                print(f"Test: {self.test_option_.name}, test_id: {self.test_option_.id}")
                return

        print("No matching test option found.")

def safe_call(client, method_name, *args, **kwargs):
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

if __name__ == "__main__":
    print("🤖 增强版Go2机器狗控制脚本 🐕")
    print("=" * 60)
    print("📋 可用指令列表：")
    print("=" * 60)
    print("🔧 基础动作：")
    print("  0 - damp (阻尼模式)")
    print("  1 - stand_up (站立)")
    print("  2 - stand_down (趴下)")
    print("  3 - move forward (前进)")
    print("  4 - move lateral (左右移动)")
    print("  5 - move rotate (转向)")
    print("  6 - stop_move (停止移动)")
    print("")
    print("🎭 特殊动作：")
    print("  7 - hand stand (倒立)")
    print("  9 - balanced stand (平衡站立)")
    print("  10 - recovery (恢复站立)")
    print("  11 - left flip (左空翻)")
    print("  12 - back flip (后空翻)")
    print("  13 - free walk (自由行走)")
    print("  14 - free bound (自由跳跃)")
    print("  15 - free avoid (自由避障)")
    print("  17 - walk upright (直立行走)")
    print("  18 - cross step (交叉步)")
    print("  19 - free jump (自由跳跃)")
    print("  20 - heart (比心) 💖")
    print("")
    print("🐕 手柄对应动作：")
    print("  21 - sit (坐下)")
    print("  22 - rise_sit (起立)")
    print("  23 - hello (打招呼)")
    print("  24 - stretch (伸展)")
    print("  25 - content (满意/拜年)")
    print("")
    print("💃 舞蹈和表演：")
    print("  26 - dance1 (跳舞1)")
    print("  27 - dance2 (跳舞2)")
    print("  28 - front_flip (前空翻)")
    print("  29 - front_jump (前跳)")
    print("  30 - front_pounce (前扑)")
    print("  31 - pose (摆姿势)")
    print("  32 - scrape (抓挠)")
    print("")
    print("🚶 行走模式：")
    print("  33 - static_walk (静态行走)")
    print("  34 - trot_run (小跑)")
    print("  35 - classic_walk (经典行走)")
    print("")
    print("🎉 动作组合：")
    print("  36 - welcome_ceremony (欢迎仪式)")
    print("  37 - happy_dance (快乐舞蹈)")
    print("  38 - exercise_routine_fixed (运动健身)")
    print("  39 - back_flip_test (后空翻测试)")
    print("  40 - obstacle_avoid_heart (避障比心组合) 🚶💖")
    print("")
    print("💡 使用说明：")
    print("  - 输入 'list' 查看所有指令")
    print("  - 输入数字ID或指令名称执行动作")
    print("  - 按 Ctrl+C 退出程序")
    print("")
    print("⚠️  安全提醒：")
    print("  - 确保机器狗周围没有障碍物")
    print("  - 建议在平坦地面上测试")
    print("  - 动作组合可能需要较长时间")
    print("=" * 60)
    input("按 Enter 键开始...")
    
    if len(sys.argv)>1:
        ChannelFactoryInitialize(0, sys.argv[1])
    else:
        ChannelFactoryInitialize(0)

    test_option = TestOption(name=None, id=None) 
    user_interface = UserInterface()
    user_interface.test_option_ = test_option

    sport_client = SportClient()  
    sport_client.SetTimeout(10.0)
    sport_client.Init()
    
    while True:
        user_interface.terminal_handle()
        print(f"Updated Test Option: Name = {test_option.name}, ID = {test_option.id}\n")

        if test_option.id == 0:
            safe_call(sport_client, "Damp")
        elif test_option.id == 1:
            safe_call(sport_client, "StandUp")
        elif test_option.id == 2:
            safe_call(sport_client, "StandDown")
        elif test_option.id == 3:
            print("🚶 机器人正在前进... ⬆️")
            # 1. 确保避障关闭
            safe_call(sport_client, "FreeAvoid", False)
            time.sleep(1)
            # 2. 确保停止之前的移动
            safe_call(sport_client, "StopMove")
            time.sleep(1)
            # 3. 开始移动
            ret = safe_call(sport_client, "Move", 0.3, 0, 0)
            print("前进指令执行结果: ", ret)
            print("等待3秒...")
            time.sleep(3)
            # 4. 明确停止
            safe_call(sport_client, "StopMove")
            print("前进动作完成！")
        elif test_option.id == 4:
            safe_call(sport_client, "Move", 0, 0.3, 0)
        elif test_option.id == 5:
            safe_call(sport_client, "Move", 0, 0, 0.5)
        elif test_option.id == 6:
            safe_call(sport_client, "StopMove")
        elif test_option.id == 7:
            safe_call(sport_client, "HandStand", True)
            time.sleep(4)
            safe_call(sport_client, "HandStand", False)
        elif test_option.id == 9:
            safe_call(sport_client, "BalanceStand")
        elif test_option.id == 10:
            safe_call(sport_client, "RecoveryStand")
        elif test_option.id == 11:
            ret = safe_call(sport_client, "LeftFlip")
            print("ret: ", ret)
        elif test_option.id == 12:
            ret = safe_call(sport_client, "BackFlip")
            print("ret: ", ret)
        elif test_option.id == 13:
            ret = safe_call(sport_client, "FreeWalk")
            print("ret: ", ret)
        elif test_option.id == 14:
            ret = safe_call(sport_client, "FreeBound", True)
            print("ret: ", ret)
            time.sleep(2)
            ret = safe_call(sport_client, "FreeBound", False)
            print("ret: ", ret)
        elif test_option.id == 15:
            ret = safe_call(sport_client, "FreeAvoid", True)
            print("ret: ", ret)
            time.sleep(2)
            ret = safe_call(sport_client, "FreeAvoid", False)
            print("ret: ", ret)
        elif test_option.id == 17:
            ret = safe_call(sport_client, "WalkUpright", True)
            print("ret: ", ret)
            time.sleep(4)
            ret = safe_call(sport_client, "WalkUpright", False)
            print("ret: ", ret)
        elif test_option.id == 18:
            ret = safe_call(sport_client, "CrossStep", True)
            print("ret: ", ret)
            time.sleep(4)
            ret = safe_call(sport_client, "CrossStep", False)
            print("ret: ", ret)
        elif test_option.id == 19:
            ret = safe_call(sport_client, "FreeJump", True)
            print("ret: ", ret)
            time.sleep(4)
            ret = safe_call(sport_client, "FreeJump", False)
            print("ret: ", ret)
        elif test_option.id == 20:
            print("🤖 机器人正在比心... 💖")
            ret = safe_call(sport_client, "Heart")
            print("比心动作执行结果: ", ret)
            time.sleep(4)
        elif test_option.id == 21:
            print("🐕 机器人正在坐下... 🪑")
            ret = safe_call(sport_client, "Sit")
            print("坐下动作执行结果: ", ret)
            time.sleep(3)
        elif test_option.id == 22:
            print("🔄 机器人正在起立... ⬆️")
            ret = safe_call(sport_client, "RiseSit")
            print("起立动作执行结果: ", ret)
            time.sleep(3)
        elif test_option.id == 23:
            print("👋 机器人正在打招呼... 🖐️")
            ret = safe_call(sport_client, "Hello")
            print("打招呼动作执行结果: ", ret)
            time.sleep(3)
        elif test_option.id == 24:
            print("🧘 机器人正在伸展... 🤸")
            ret = safe_call(sport_client, "Stretch")
            print("伸展动作执行结果: ", ret)
            time.sleep(3)
        elif test_option.id == 25:
            print("😊 机器人正在表达满意... 😄")
            ret = safe_call(sport_client, "Content")
            print("满意动作执行结果: ", ret)
            time.sleep(3)
        elif test_option.id == 26:
            print("💃 机器人正在跳舞1... 🕺")
            ret = safe_call(sport_client, "Dance1")
            print("跳舞1执行结果: ", ret)
            time.sleep(4)
        elif test_option.id == 27:
            print("💃 机器人正在跳舞2... 🕺")
            ret = safe_call(sport_client, "Dance2")
            print("跳舞2执行结果: ", ret)
            time.sleep(4)
        elif test_option.id == 28:
            print("🤸 机器人正在前空翻... ⬇️")
            ret = safe_call(sport_client, "FrontFlip")
            print("前空翻执行结果: ", ret)
            time.sleep(4)
        elif test_option.id == 29:
            print("🦘 机器人正在前跳... ⬇️")
            ret = safe_call(sport_client, "FrontJump")
            print("前跳执行结果: ", ret)
            time.sleep(3)
        elif test_option.id == 30:
            print("🐯 机器人正在前扑... 🦁")
            ret = safe_call(sport_client, "FrontPounce")
            print("前扑执行结果: ", ret)
            time.sleep(3)
        elif test_option.id == 31:
            print("🎭 机器人正在摆姿势... 📸")
            ret = safe_call(sport_client, "Pose", True)
            print("摆姿势执行结果: ", ret)
            time.sleep(3)
            safe_call(sport_client, "Pose", False)
        elif test_option.id == 32:
            print("🦵 机器人正在抓挠... 🐾")
            ret = safe_call(sport_client, "Scrape")
            print("抓挠执行结果: ", ret)
            time.sleep(3)
        elif test_option.id == 33:
            print("🚶 机器人正在静态行走... 🚶")
            ret = safe_call(sport_client, "StaticWalk")
            print("静态行走执行结果: ", ret)
            time.sleep(4)
        elif test_option.id == 34:
            print("🏃 机器人正在小跑... 🏃")
            ret = safe_call(sport_client, "TrotRun")
            print("小跑执行结果: ", ret)
            time.sleep(4)
        elif test_option.id == 35:
            print("🚶 机器人正在经典行走... 🚶")
            ret = safe_call(sport_client, "ClassicWalk", True)
            print("经典行走执行结果: ", ret)
            time.sleep(4)
            safe_call(sport_client, "ClassicWalk", False)
        elif test_option.id == 36:
            print("🎉 欢迎仪式开始... 🎊")
            # 欢迎仪式组合：站立 -> 打招呼 -> 比心 -> 跳舞
            safe_call(sport_client, "StandUp")
            time.sleep(2)
            safe_call(sport_client, "Hello")
            time.sleep(2)
            safe_call(sport_client, "Heart")
            time.sleep(2)
            safe_call(sport_client, "Dance1")
            time.sleep(3)
            print("🎉 欢迎仪式完成！")
        elif test_option.id == 37:
            print("🎵 快乐舞蹈开始... 🎶")
            # 快乐舞蹈组合：跳舞1 -> 跳舞2 -> 伸展
            safe_call(sport_client, "Dance1")
            time.sleep(3)
            safe_call(sport_client, "Dance2")
            time.sleep(3)
            safe_call(sport_client, "Stretch")
            time.sleep(2)
            print("🎵 快乐舞蹈完成！")
        elif test_option.id == 38:
            print("💪 修正版运动健身开始... 🏋️")
            # 修正版运动健身组合：伸展 -> 前跳 -> 前空翻 -> 伸展 -> 比心
            print("1. 伸展...")
            safe_call(sport_client, "Stretch")
            time.sleep(3)
            print("2. 前跳...")
            safe_call(sport_client, "FrontJump")
            time.sleep(3)
            print("3. 前空翻...")
            safe_call(sport_client, "FrontFlip")
            time.sleep(4)
            print("4. 再次伸展...")
            safe_call(sport_client, "Stretch")
            time.sleep(3)
            print("5. 比心...")
            safe_call(sport_client, "Heart")
            time.sleep(3)
            print("💪 修正版运动健身完成！")
        elif test_option.id == 39:
            print("🤸 单独测试后空翻...")
            ret = safe_call(sport_client, "BackFlip")
            print("后空翻测试结果: ", ret)
            time.sleep(5)
        elif test_option.id == 40:
            print("🚶 避障比心组合开始... 💖")
            # 避障比心组合：前进 -> 检测到障碍停止 -> 比心
            print("1. 开始前进...")
            safe_call(sport_client, "Move", 0.3, 0, 0)
            print("2. 等待最多10秒（遇到障碍会自动停止）...")
            time.sleep(10)  # 增加等待时间
            print("3. 停止移动...")
            safe_call(sport_client, "StopMove")
            time.sleep(2)
            print("4. 比心...")
            safe_call(sport_client, "Heart")

        time.sleep(1) 
