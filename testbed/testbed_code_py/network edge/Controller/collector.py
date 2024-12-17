import socket
import time
import json
import struct
import threading
from queue import Queue
from collections import defaultdict
import math

ip = "172.16.6.141"
port = 10000
pkt_loss_threshold = 100
pkt_loss_rate_threshold = 0.3
window_size = 10
delay = 1.5
max_INT_cnt = 100


def sendString(string, client_socket):
    len_s = len(string)
    f = struct.pack("i", len_s)
    client_socket.send(f)
    client_socket.sendall(string.encode("utf-8"))
    return

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
    print('recv time:', recv_end_time - recv_start_time)
    print('recv len:', len_s)
    return data

queue_list = []
res_queue = Queue()

def analyse_once():
    collect_start_time = None
    while True:
        flag = True
        for q in queue_list:
            if q.empty():
                flag = False
            elif collect_start_time is None:
                collect_start_time = time.time()
        if flag:
            break
        time.sleep(0.1)
        
    data_list = []
    for q in queue_list:
        data_list.append(q.get())
    
    collect_end_time = time.time()
    if len(data_list) > 0:
        print('collect time:', collect_end_time - collect_start_time)
    
    analyse_start_time = time.time()
    
    res_in = defaultdict(int)
    res_out = defaultdict(int)
    for data in data_list:
        data = json.loads(data)
        cur_in = data['in']
        cur_out = data['out']
        for key, val in cur_in.items():
            res_in[key] += val
        for key, val in cur_out.items():
            res_out[key] += val
    INT_ids = []
    for key in res_in:
        pkt_loss = res_in[key] - res_out[key]
        pkt_loss_rate = pkt_loss / res_in[key]
        if pkt_loss > pkt_loss_threshold or pkt_loss_rate > pkt_loss_rate_threshold:
            INT_ids.append(key)
    INT_ids = INT_ids[:max_INT_cnt]
    if len(data_list) > 0:
        print('INT ids len:', len(INT_ids))
    res = json.dumps(INT_ids)

    analyse_finish_time = time.time()
    analyse_time = analyse_finish_time - analyse_start_time
    if len(data_list) > 0:
        print('analyse time:', analyse_time)

    for _ in range(len(data_list)):
        res_queue.put(res)

def analyse():
    while True:
        analyse_once()

def work_once(conn, addr, id):
    data = receiveString(conn)
    print('receive data')

    while not queue_list[id].empty():
        queue_list[id].get_nowait()
    
    queue_list[id].put(data)
    res = res_queue.get()
    sendString(res, conn)

def work(conn, addr, id):
    while True:
        work_once(conn, addr, id)

if __name__ == "__main__":
    threading.Thread(target=analyse).start()
    s = socket.socket()
    s.bind((ip,port))
    s.listen(1)
    while True:
        conn, addr = s.accept()
        queue_list.append(Queue())
        th = threading.Thread(target=work, args=(conn, addr, len(queue_list) - 1))
        th.start()
