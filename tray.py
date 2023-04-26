f = open("sample.txt","wb")
size = 262144*4 # bytes in 1 GiB
f.write(bytes('0',encoding='utf-8')* size)
f.close()