# -*- coding: utf-8 -*-
import json
import _thread
import random
import socket
import threading
import time
import csv
import pandas as pd
import logging

BufferSize = 409600 # 最大缓存4KB
BufferEncoding = "utf-8"  # 缓存编码

fs = 44200 # Sampling rate (Sampling Rate Must be same across Client And Service
# Setting Default Sampling Rate

duration = 5 # sec
FileHeader = '''
Socket Log
StartTime:{}
----------------------------------------------------------------
'''

FileTail = '''
----------------------------------------------------------------
EndTime:{}
Count:{}
'''

InfoTemplate = "|INFO|\t[{}]{}"


class Log:
    def __init__(self, path):
        self.__path = "{}\\{}.log".format(path, time.strftime("%Y%m%d%H%M%S", time.localtime()))
        self.__lock = threading.Lock()
        self.__counter = 0

    def _writer(self, message):
        self.__lock.acquire()
        self.__counter += 1
        stream = open(self.__path, "a+",encoding='gbk') #这里改一句就可以输出正确的log
        stream.write(message + "\n")
        stream.close()
        self.__lock.release()

    def open(self):
        self._writer(FileHeader.format(time.strftime("%Y/%m/%d/ %H:%M:%S", time.localtime())))

    def close(self):
        self._writer(FileTail.format(time.strftime("%Y/%m/%d/ %H:%M:%S", time.localtime()), self.__counter - 1))

    def logmsg(self, msg):
        data = InfoTemplate.format(time.strftime("%Y/%m/%d/ %H:%M:%S", time.localtime()), msg)
        self._writer(data)

    def logobj(self, obj):
        data = InfoTemplate.format(time.strftime("%Y/%m/%d/ %H:%M:%S", time.localtime()), json.loads(obj))
        self._writer(data)


class SocketServer:
    def __init__(self, logger: Log):
        self.__logger = logger
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__isrun = False
        self.__connects = []
        self.__max = 0
        self.__register_new = False #判断是不是新用户
        self.__login= False

    def loginfo(self, msg):
        print("|INFO|\t" + str(msg))
        self.__logger.logmsg(msg)

    def createmsg(self, sender, receiver, action, **data) -> str:
        msg = {
            "code": 200,
            "sender": sender,
            "receiver": receiver,
            "action": action,
            "time": time.strftime("%Y/%m/%d %H:%M:%S", time.localtime()),
            "data": data}
        return json.dumps(msg)

    def _logobj(self, data: dict):   #写入log文件
        action = data["action"]
        if action == "msg":
            msg = "收到{}发往{}的信息:{}".format(data["sender"], data["receiver"], data["data"]["msg"])
            self.loginfo(msg)
        if action == "file_sending":
            msg = "收到{}发往{}的文件".format(data["sender"], data["receiver"])
            self.loginfo(msg)

        if action == "voice":
            msg = "收到{}发往{}的语音".format(data["sender"], data["receiver"])
            self.loginfo(msg)

        if action == "close":
            msg = "用户{}关闭了连接".format(data["sender"])
            self.loginfo(msg)
        if action == "live":
            msg = "用户{}查询了当前在线人数:{}".format(data["sender"], len(self.__connects))
            self.loginfo(msg)
        if action == "register":
            if self.__register_new==True:
                msg = "新用户进行了一次注册"
            else:
                msg = "已注册用户!"
            self.loginfo(msg)
            self.__register_new=False

        if action == "login":
            if self.__login==True:
               msg = "一名用户登陆成功"
            else:
               msg = "一名用户登陆失败"
            self.loginfo(msg)
            self.__login=False

    def _forward(self, data: dict):
        try:
            goal = data["receiver"]
            # 判断是否为服务器消息
            if goal == "host":
                return

            # 判断是否为群发消息
            elif goal == "all":
                print("|INFO|\t开始转发群消息")
                self.__logger.logmsg("开始转发群消息")
                for i in self.__connects:
                    i[1].send(bytes(json.dumps(data), encoding=BufferEncoding))
                return

            # 监测目标是否上线
            else:
                for i in self.__connects:
                    if goal in i:
                        # 找到目标
                        receiver: socket.socket = i[1]
                        # 转发消息
                        receiver.send(bytes(json.dumps(data), encoding=BufferEncoding))
                        return
                # 未检测到
                self.loginfo("目标未上线")


        except Exception as e:

            self.loginfo(str(e))

    def _forward_voice(self,data:dict,voice):
        try:
            goal = data["receiver"]
            # 判断是否为服务器消息
            if goal == "host":
                return

            else:
                for i in self.__connects:
                    if goal in i:
                        # 找到目标
                        receiver: socket.socket = i[1]
                        # 转发消息
                        msg = self.createmsg(data['sender'], data['receiver'], 'rec_voice',status="success")
                        receiver.send(bytes(msg, encoding=BufferEncoding)) #注意此处直接发ms
                        print(f"向{data['receiver']}发送语音接收报头")
                        time.sleep(15)
                        receiver.sendall(voice)
                        time.sleep(30)
                        receiver.send(bytes("-1", encoding="utf-8"))
                        return
                # 未检测到
                self.loginfo("目标未上线")


        except Exception as e:
            self.loginfo(str(e))

    def _forward_file(self,data:dict, file_path):
        try:
            goal = data["receiver"]
            # 判断是否为服务器消息
            if goal == "host":
                return

            else:
                for i in self.__connects:
                    if goal in i:
                        # 找到目标
                        file=open(file_path,"rb")
                        receiver: socket.socket = i[1]
                        # 转发消息
                        msg = self.createmsg(data['sender'], data['receiver'], 'rec_file',mode=data['data']['mode'])
                        receiver.send(bytes(msg, encoding=BufferEncoding)) #注意此处直接发msg
                        print(f"向{data['receiver']}发送文件接收报头")
                        time.sleep(20)
                        receiver.sendall(file.read())
                        time.sleep(20)
                        receiver.send(bytes("-1", encoding="utf-8"))
                        file.close()
                        return
                # 未检测到
                self.loginfo("目标未上线")


        except Exception as e:
            self.loginfo(str(e))

    def _action(self, index, receiver: socket.socket, address, data: dict):

        action = data["action"]

        if action == "msg":
            self._forward(data)

            return 0

        if action == "voice":
            total_data=b''
            voice_data = receiver.recv(int(fs) * int(duration) * 4)
            total_data+=voice_data
            while voice_data!=bytes("-1",encoding="utf-8"):
                voice_data = receiver.recv(int(fs) * int(duration) * 4)
                if(voice_data!=bytes("-1",encoding="utf-8")):
                     total_data += voice_data
            
            self._forward_voice(data,total_data)
            return 0

        if action == "file_sending":
            total_data = b''
            num = 0
            print("111")
            t_data = receiver.recv(262144*4)
            total_data += t_data
            num = len(t_data)
            # 如果没有数据了，读出来的data长度为0，len(data)==0
            while t_data!=bytes("-1",encoding="utf-8"):
                t_data = receiver.recv(262144*4)
                num += len(t_data)
                if(t_data!=bytes("-1",encoding="utf-8")):
                    total_data += t_data
            file_path=f"tmp_files/{num}.{data['data']['mode']}"
            with open(file_path, "wb") as f:
                f.write(total_data)
            f.close()
            self._forward_file(data,file_path)
            return 0


        if action == "close":
            self.__connects.remove((index, receiver, address))
            receiver.close()
            return -1

        if action == "live":
            live = []
            for i in self.__connects:
                live.append(i[0])

            msg = self.createmsg("host", data["sender"], "live", count=len(live), index=live)
            receiver.send(bytes(msg, encoding=BufferEncoding))
            return 0

        if action == "register":
            tmp_user_msg=data["data"].items()
            #print(tmp_user_msg)
            tmp_user_name=None
            tmp_password=None
            for k,v in tmp_user_msg:
                tmp_user_name=k
                tmp_password=v
            #tmp_user_name=tmp_user_msg
            field_names=["user_name","password"]
            f = open('user_msg.csv', mode='a+', encoding='utf-8', newline='')  # user_msg为文件名称
            df=pd.read_csv('user_msg.csv')
            if tmp_user_name in df["user_name"].values:
                #TODO: 排除已经注册,密码不符合的情况
                f.close()
                return 0

            self.__register_new=True  #新用户
            csv_writer = csv.DictWriter(f, fieldnames=field_names)
            dic={"user_name":tmp_user_name,"password":tmp_password}
            csv_writer.writerow(dic)
            f.close()
            #f.write()

            return 0

        if action=="login":  #登录
            tmp_user_msg = data["data"].items()
            # print(tmp_user_msg)
            tmp_user_name = None
            tmp_password = None
            for k, v in tmp_user_msg:
                tmp_user_name = k
                tmp_password = v
            df = pd.read_csv('user_msg.csv')
            for item in df.values:
                if item[0]==tmp_user_name and item[1]==tmp_password:
                    msg = self.createmsg("host", index, "msg", index=index, msg="success")
                    #msg = json.dumps({"status": "success"})
                    receiver.send(bytes(msg, encoding=BufferEncoding))
                    #time.sleep(2)
                    self.__login=True
                    return 0

            msg = self.createmsg("host", index, "msg", index=index, msg="failed")
            receiver.send(bytes(msg, encoding=BufferEncoding))

            return 0

    def _getmessage(self, index, receiver: socket.socket, address):
        try:
            while self.__isrun:
                mcs=str(receiver.recv(BufferSize), encoding='utf8')
                data = json.loads(mcs)  # 4KB缓存

                ###LOG - Start 服务器Log记录
                #self._logobj(data)
                ###End

                ###Deal - Start 消息处理
                result = self._action(index, receiver, address, data)
                self._logobj(data)
                if result == -1:
                    return
                if result == 0:
                    continue
                ###End

        except Exception as e:

            self.loginfo(str(e))

        finally:
            self.loginfo(f"{index}的消息接收线程已退出")

    def _listen(self):

        self.loginfo("成功启动套接字监听")

        while self.__isrun:

            if len(self.__connects) == self.__max:
                break  # 达到最大连接数量断开监听

            connect, address = self.__socket.accept()  # 获取到连接

            # 生成标识符
            index = ""
            for i in range(5):
                index += str(random.randint(0, 9))

            self.loginfo("接受到:{}的连接,分配的ID:{}".format(address, index))

            self.__connects.append((index, connect, address))  # 挂起连接并加入库

            '''
            msg = self.createmsg("host", index, "msg", index=index, msg="连接成功")
            connect.send(bytes(msg, encoding="utf-8"))  # 发生返回信息
            '''

            _thread.start_new_thread(self._getmessage, (index, connect, address,))  # 打开信息监听进程
            #msg = self.createmsg("host", index, "msg", index=index, msg="连接成功")
            #connect.send(bytes(msg, encoding="utf-8"))  # 发生返回信息

            continue

        self.loginfo("监听线程已退出")

    def startlisten(self, port, ip="0.0.0.0", count=10):
        #print(ip)
        self.__socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.__socket.bind((ip, port))
        self.__socket.listen(count)
        self.__isrun = True
        self.__max = count
        self.loginfo("监听初始化完毕,正在启动")
        self.loginfo(f"开启端口:{port},支持最大连接数量:{count}")
        _thread.start_new_thread(self._listen, ())

    def send(self, address, msg):
        if not self.__isrun:
            return

        # 监测目标是否上线
        for i in self.__connects:
            if address in i:
                msg = self.createmsg("host", address, "msg", msg=msg)
                i[1].send(bytes(msg, encoding=BufferEncoding))
                self.loginfo("发生成功")
                return
        self.loginfo("目标不在线")

    def sendall(self, msg):
        if not self.__isrun:
            return

        for i in self.__connects:
            msg = self.createmsg("host", i[0], "msg", msg=msg)
            i[1].send(bytes(msg, encoding=BufferEncoding))
        self.loginfo("发送成功")
        return

    def close(self):
        self.__isrun = False
        # 释放log对象
        self.__logger.close()
        # 等待未完成的任务
        time.sleep(5)
        # 释放所有套接字
        self.__socket.close()
        for i in self.__connects:
            i[1].close()

if __name__=="__main__":
    '''
    f = open('user_msg.csv', mode='a', encoding='utf-8', newline='')  # user_msg为文件名称
    csv_writer = csv.DictWriter(f, fieldnames=['user_name','password'])
    csv_writer.writeheader()
    f.close()
    '''
    reader = open("config.json", "r")
    data = json.loads(reader.read())
    reader.close()
    log = Log(data["path"])
    log.open()
    server = SocketServer(log)
    server_ip="0.0.0.0"
    #server_ip=socket.gethostbyname(socket.gethostname()) #这里需要获取一个正确的ip
    #server_listening_ip=""
    print(f'服务器ip地址为: {server_ip}')
    server.startlisten(data["port"],ip=server_ip)
    try:
        while True:

            get = input()

            if "Close" in get:
                server.close()
                print("|INFO|\t已关闭所有进程")
                break

            if "Send" in get:
                data = get.split("/")
                server.send(data[1], data[2])

            else:
                print("|INFO|\t键盘输出:", get)

    except Exception as e:
        server.close()

    finally:
        print("|INFO|\t程序已退出")
