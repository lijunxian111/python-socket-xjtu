# python-socket-xjtu
the experiment 8 of computer networks XJTU

run server2.py using a remote server
run client2.py using your own computer.
记得服务器安全组配置一下端口！！！

terminal commands:（输入到命令行或者pycharm，vs的终端）
Register
Login
Check: 看有多少用户活跃，返回序列号
Send: 格式为Send/序列号/消息，意思为对序列号为xx的用户发消息，注意序列号可以为all，大家都能收到消息
Sen_file:格式为Sen_file/序列号/文件名/格式（txt,jpg,...) 序列号不可以为all
Voice:格式为Voice/序列号，序列号不可以为all，传一段语音
Close:关闭socket

有可能的报错：端口被占用，拒绝连接等，记得服务器监听“0.0.0.0”，客户端去bond服务器的公网IP

GUI是基于pyqt5的，开了个头
