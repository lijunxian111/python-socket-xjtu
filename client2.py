# -*- coding: utf-8 -*-
import _thread
import json
import socket
import time
import cv2
import numpy as np
import sounddevice as sd

BufferSize = 409600
fs = 44200 # Sampling rate (Sampling Rate Must be same across Client And Server)
sd.default.samplerate = fs # Setting Default Sampling Rate

duration = 5 # sec


class SocketClient:
    def __init__(self):
        self.__socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.__isrun = False
        self.__index = -1
        self.__usermsg={}

        self.fs = fs
        self.duration = duration   #for voice sending

    def close(self):
        msg = {
            "code": 200,
            "sender": self.__index,
            "receiver": "host",
            "action": "close",
            "time": time.strftime("%Y/%m/%d %H:%M:%S", time.localtime()),
            "data": {
            }}
        self.__socket.send(bytes(json.dumps(msg), encoding="utf-8"))
        self.__isrun = False
        time.sleep(5)
        self.__socket.close()

    def register(self):   #注册
        msg = {
            "code": 200,
            "sender": self.__index,
            "receiver": "host",
            "action": "register",
            "time": time.strftime("%Y/%m/%d %H:%M:%S", time.localtime()),
            "data": self.__usermsg
        }
        self.__socket.send(bytes(json.dumps(msg), encoding="utf-8"))
        print("发送成功")


    def login(self):   #登录
        msg = {
            "code": 200,
            "sender": self.__index,
            "receiver": "host",
            "action": "login",
            "time": time.strftime("%Y/%m/%d %H:%M:%S", time.localtime()),
            "data": self.__usermsg
        }
        self.__socket.send(bytes(json.dumps(msg), encoding="utf-8"))
        print("发送成功")

    def send(self, address, msg):
        if not self.__isrun: return
        msg = {
            "code": 200,
            "sender": self.__index,
            "receiver": address,
            "action": "msg",
            "time": time.strftime("%Y/%m/%d %H:%M:%S", time.localtime()),
            "data": {
                "msg": msg
            }}  # 构造返回字符串
        self.__socket.send(bytes(json.dumps(msg), encoding="utf-8"))
        print("发送成功")

    def send_voice(self,address):
        if not self.__isrun: return
        print("<-- Recording Voice -->")
        myrecording = sd.rec(int(duration * fs), samplerate=fs, blocking=True, channels=1)
        sd.wait()
        sd.play(myrecording,fs)
        Voice = myrecording.tostring()
        msg = {
            "code": 200,
            "sender": self.__index,
            "receiver": address,
            "action": "voice",
            "time": time.strftime("%Y/%m/%d %H:%M:%S", time.localtime()),
            "data": {
            }}  # 构造返回字符串
        self.__socket.send(bytes(json.dumps(msg), encoding="utf-8"))
        time.sleep(5)
        self.__socket.sendall(Voice)
        time.sleep(30)
        self.__socket.send(bytes("-1", encoding="utf-8"))
        print("语音发送成功")


    def send_file(self,address,file_path,mode):
        if not self.__isrun: return
        file = open(file_path,"rb")
        msg = {
            "code": 200,
            "sender": self.__index,
            "receiver": address,
            "action": "file_sending",
            "time": time.strftime("%Y/%m/%d %H:%M:%S", time.localtime()),
            "data": { "mode":mode
            }}  # 构造返回字符串
        self.__socket.send(bytes(json.dumps(msg), encoding="utf-8"))
        time.sleep(20)
        if mode=='png' or mode=='jpg' or mode=='jpeg':
            img = cv2.imread(file_path)  # 这个是我本地的图片，和这个py文件在同一文件夹下，注意格式
            # '.jpg'表示把当前图片img按照jpg格式编码，按照不同格式编码的结果不一样
            img_encode = cv2.imencode(f'.{mode}', img)[1]

            data_encode = np.array(img_encode)
            str_encode = data_encode.tostring()
            self.__socket.sendall(str_encode)
        else:
            self.__socket.sendall(file.read())
        time.sleep(20)
        self.__socket.send(bytes("-1", encoding="utf-8"))
        file.close()
        print("发送成功")

    def checklive(self):  #查看活跃人数
        if not self.__isrun: return
        msg = {
            "code": 200,
            "sender": self.__index,
            "receiver": "host",
            "action": "live",
            "time": time.strftime("%Y/%m/%d %H:%M:%S", time.localtime()),
            "data": {
            }}  # 构造返回字符串
        self.__socket.send(bytes(json.dumps(msg), encoding="utf-8"))
        print("发送成功")

    def check_user(self):    #登陆函数
        if not self.__isrun: return
        msg = {
            "code": 200,
            "sender": self.__index,
            "receiver": "host",
            "action": "login",
            "time": time.strftime("%Y/%m/%d %H:%M:%S", time.localtime()),
            "data": {
            }}  # 构造返回字符串
        self.__socket.send(bytes(json.dumps(msg), encoding="utf-8"))
        print("发送成功")

    def _recive(self):
        try:
            while self.__isrun:
                data = json.loads(str(self.__socket.recv(BufferSize), encoding="utf-8"))
                if data["action"] == "rec_voice":  #语音传输
                    print(f"接收到{data['sender']}发送来的语音")
                    time.sleep(2)
                    print("<-- Received Voice -->")
                    msg = self.__socket.recv(int(self.fs) * int(self.duration) * 4)
                    total_data = b''
                    # print(t_data)
                    total_data += msg
                    # 如果没有数据了，读出来的data长度为0，len(data)==0
                    while msg != bytes("-1", encoding="utf-8"):
                        msg = self.__socket.recv(int(self.fs) * int(self.duration) * 4)
                        # print(t_data)
                        if (msg != bytes("-1", encoding="utf-8")):
                            total_data += msg
                    voice = np.frombuffer(total_data, dtype=np.float32)
                    print("<-- Playing Voice -->")
                    sd.play(voice,self.fs)
                    continue

                if data["action"] == "rec_file":
                    print(f"接收到{data['sender']}发送来的文件")
                    total_data = b''
                    num = 0
                    t_data = self.__socket.recv(262144*4)
                    #print(t_data)
                    total_data += t_data
                    num = len(t_data)
                    # 如果没有数据了，读出来的data长度为0，len(data)==0
                    while t_data != bytes("-1", encoding="utf-8"):
                        t_data = self.__socket.recv(262144*4)
                        # print(t_data)
                        num += len(t_data)
                        if (t_data != bytes("-1", encoding="utf-8")):
                            total_data += t_data
                    file_path = f"save_files/{num}.{data['data']['mode']}"
                    if data['data']['mode']=='png' or data['data']['mode']=='jpg' or data['data']['mode']=='jpeg':
                        nparr = np.fromstring(str(total_data,encoding="utf-8"), dtype='uint8')
                        img_decode = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                        cv2.imwrite(file_path,img_decode)
                        cv2.imshow("img_decode", img_decode)  # 显示图片
                        cv2.waitKey(1)
                    else:
                    #print('111')
                        with open(file_path, "wb") as f:
                            f.write(total_data)

                            f.close()
                    continue
                if data["action"] == "live":
                    print("目前在线人数为", data["data"]["count"])
                    for i in data["data"]["index"]:
                        print(i)
                    continue
                msg = "[{}]{}:{}".format(data["time"], data["sender"], data["data"]["msg"])
                print(msg)
            # 退出消息
            print("已退出消息接收")

        except Exception as e:
            print("接收错误", str(e))

    def startconnect(self, ip, port):
        '''
        get=input()
        if get == "Register":
            print("输入注册的用户名和密码")
            user_id = str(input("请输入用户名: "))
            pwd = str(input("请输入密码: "))
            self.__usermsg[user_id]=pwd
        '''
        '''
        elif get=="Connect":
            print("开始连接")
            user_id=str(input("请输入用户名: "))
            pwd=str(input("请输入密码: "))
        '''
        self.__isrun = True
        self.__socket.connect((ip, port))
        data_login=None
        print("请选择输入注册(Register)或登录(Login): ")
        get = input()
        if get == "Register":
            print("输入注册的用户名和密码")
            user_id = str(input("请输入用户名: "))
            pwd = str(input("请输入密码: "))
            self.__usermsg[user_id] = pwd
            self.register()
            data_login = json.loads(str(self.__socket.recv(BufferSize), encoding="utf-8"))
            time.sleep(1)
            #
        elif get== "Login":
            flag=True #True代表没有成功登录的状态
            while(flag==True):
                print("输入注册的用户名和密码")
                user_id = str(input("请输入用户名: "))
                pwd = str(input("请输入密码: "))
                self.__usermsg[user_id] = pwd
                self.login()
                data_login = json.loads(str(self.__socket.recv(BufferSize), encoding="utf-8"))
                time.sleep(1)
                #print(data_login)
                if data_login["data"]['msg']=="success":
                    print("登录成功！")
                    flag=False
                elif data_login["data"]['msg']=="failed":
                    print("登陆失败,请重试")
        else:
            pass
        # 连接成功
        # 获取序列号
        #data = json.loads(str(self.__socket.recv(BufferSize), encoding="utf-8"))
        if data_login:
            self.__index = data_login["data"]["index"]
            print("连接成功，您的序列号为:", self.__index)
        # 开启消息监听线程
            _thread.start_new_thread(self._recive, ())

if __name__=="__main__":
    client = SocketClient()
    server_ip="39.106.63.232"
    #server_ip="192.168.11.1"
    client.startconnect(server_ip, 1234) #端口要匹配

    while True:
        get = input()
        if get == "Close":
            client.close()
            break
        if "Send" in get:
            data = get.split("/")
            client.send(data[1], data[2])

        if "Check" in get:
            client.checklive()

        if "Sen_file" in get:
            data=get.split("/")
            client.send_file(data[1],data[2],mode=data[3])  #告诉文件格式

        if "Voice" in get:
            data=get.split("/")
            client.send_voice(data[1])

    print("程序已结束")

