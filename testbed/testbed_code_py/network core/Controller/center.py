'''center code
main work: receive data sent from switch's control plane'''
import socket
import time
import json
import struct
import threading

import sys

ip = "172.16.6.141"
#in our topo , we used 4 tofino switches inside the newtwork
port_set = [5001,5002,5003,5004]
switch_num = 4

register_num = 1024

#receive string from socket
def receiveString(client_socket):
    d = client_socket.recv(struct.calcsize("i"))
    recv_start_time = time.time()
    len_s = struct.unpack("i", d)
    print("data_length:"+str(len_s))
    num = len_s[0]//1024
    data = ""
    current_length = 0
    data_list = []
    while current_length < len_s[0]:
        data_list.append(client_socket.recv(1024).decode("utf-8"))
        current_length += len(data_list[-1])
    data = ''.join(data_list)
    recv_end_time = time.time()
    #print("recv_time:" + str(recv_end_time - recv_start_time))
    #print("no error after loop")
    sys.stdout.write("recieve data over")
    return data

def trans_to_ipadress(input):
    value1 = input & 0x000000ff
    value2 = (input & 0x0000ff00) >> 8
    value3 = (input & 0x00ff0000) >> 16
    value4 = (input & 0xff000000) >> 24
    return str(value4) + "." + str(value3) + "." + str(value2) + "." + str(value1)

def listen_and_record(ip,port,switch_seq):
    s = socket.socket()
    s.bind((ip,port))
    s.listen(1)
    conn, addr = s.accept()
    while True:
        Micro_list = []
        data = receiveString(conn)
        #data : receive from switch control plane
        data = json.loads(data)
        #extract data out
        # print(data)
        with open("sketch"+str(switch_seq)+".json",'w') as f:
            f.seek(0)
            f.truncate()
            json.dump(data,f)
            print("load over...")
    #conn.close()

if __name__ == "__main__":
    for i in range(switch_num):
        thread_server = threading.Thread(target=listen_and_record,args=(ip,port_set[i],i))
        thread_server.start()