
import json
from re import L

from unitree_sdk2py.rpc.client import Client
from unitree_sdk2py.rpc.internal import *

"""
" service name
"""
ROBOT_STATE_SERVICE_NAME = "robot_state"


"""
" service api version
"""
ROBOT_STATE_API_VERSION = "1.0.0.1"


"""
" api id
"""
ROBOT_STATE_API_ID_SERVICE_SWITCH = 1001
ROBOT_STATE_API_ID_REPORT_FREQ = 1002
ROBOT_STATE_API_ID_SERVICE_LIST = 1003


"""
" error code
"""
ROBOT_STATE_ERR_SERVICE_SWITCH = 5201
ROBOT_STATE_ERR_SERVICE_PROTECTED = 5202

from unitree_sdk2py.core.channel import ChannelFactoryInitialize
import time
import sys

"""
" class ServiceState
"""
class ServiceState:
    def __init__(self, name: str = None, status: int = None, protect: bool = None):
        self.name = name
        self.status = status
        self.protect = protect

"""
" class RobotStateClient
"""
class RobotStateClient(Client):
    def __init__(self):
        super().__init__(ROBOT_STATE_SERVICE_NAME, False)

    def Init(self):
        # set api version
        self._SetApiVerson(ROBOT_STATE_API_VERSION)
        # regist api
        self._RegistApi(ROBOT_STATE_API_ID_SERVICE_SWITCH, 0)
        self._RegistApi(ROBOT_STATE_API_ID_REPORT_FREQ, 0)
        self._RegistApi(ROBOT_STATE_API_ID_SERVICE_LIST, 0)

    def ServiceList(self):
        p = {}
        parameter = json.dumps(p)

        code, data = self._Call(ROBOT_STATE_API_ID_SERVICE_LIST, parameter)

        if code != 0:
            print("code != 0")
            return code, None

        lst = []

        d = json.loads(data)
        for t in d:
            print("data not null")
            s = ServiceState()
            s.name = t["name"]
            s.status = t["status"]
            s.protect = t["protect"]
            lst.append(s)
            
        return code, lst
            

    def ServiceSwitch(self, name: str, switch: bool):
        p = {}
        p["name"] = name
        p["switch"] = int(switch)
        parameter = json.dumps(p)
        
        code, data = self._Call(ROBOT_STATE_API_ID_SERVICE_SWITCH, parameter)
        
        if code != 0:
            return code
      
        d = json.loads(data)

        status = d["status"]
    
        if status == 5:
            return ROBOT_STATE_ERR_SERVICE_PROTECTED

        if status != 0 and status != 1:
            return ROBOT_STATE_ERR_SERVICE_SWITCH
        
        return code

    def SetReportFreq(self, interval: int, duration: int):
        p = {}
        p["interval"] = interval
        p["duration"] = duration
        parameter = json.dumps(p)
        
        code, data = self._Call(ROBOT_STATE_API_ID_REPORT_FREQ, p)
        return code

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
    test_client = RobotStateClient()
    code, lst = test_client.ServiceList() 

    print(lst)
