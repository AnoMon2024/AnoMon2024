import json
import re
import sys
import binascii
import socket
import threading
import time
import struct
import math


table_size = 64
print_flag = 1
server_ip = "172.16.6.141"
server_port = 10000
pipe_id = 1
window_size = 10
delay = 1.5

elastic_regs_0 = [bfrt.elastic_coco.pipe.Ingress.freq_vote_01, bfrt.elastic_coco.pipe.Ingress.freq_vote_02, bfrt.elastic_coco.pipe.Egress.freq_vote_04]
elastic_id_strs_0 = ["Ingress.freq_vote_01.lo","Ingress.freq_vote_02.lo","Egress.freq_vote_04.lo"]
elastic_counter_strs_0 = ["Ingress.freq_vote_01.hi","Ingress.freq_vote_02.hi","Egress.freq_vote_04.hi"]
elastic_regs_1 = [bfrt.elastic_coco.pipe.Ingress.freq_vote_11, bfrt.elastic_coco.pipe.Ingress.freq_vote_12, bfrt.elastic_coco.pipe.Egress.freq_vote_14]
elastic_id_strs_1 = ["Ingress.freq_vote_11.lo","Ingress.freq_vote_12.lo","Egress.freq_vote_14.lo"]
elastic_counter_strs_1 = ["Ingress.freq_vote_11.hi","Ingress.freq_vote_12.hi","Egress.freq_vote_14.hi"]

### main begin
s = socket.socket()
s.connect((server_ip, server_port))

while True:
    change_time = math.ceil(time.time() / window_size) * window_size
    while time.time() < change_time:
        time.sleep(0.1)
    
    if print_flag == 1:
        start_time = time.time()
    
    test_int = bfrt.elastic_coco.pipe.Ingress.int_reg
    
    ### get choose flag
    flag_table = bfrt.elastic_coco.pipe.Ingress.sketch_choose_flag
    flag_text = flag_table.dump(json=True, from_hw=True)
    flag_data = json.loads(flag_text)
    choose_flag = (time.time() // window_size) % 2
    get_time = time.time()
    if print_flag == 1:
        pass

    ### change choose flag
    if choose_flag == 1:
        flag_table.mod(0,1)
    else:
        flag_table.mod(0,0)
    if print_flag == 1:
        mod_time = time.time()

    while time.time() < change_time + delay:
        time.sleep(0.1)
    if print_flag == 1:
        delay_end_time = time.time()
    
    collect_start_time = time.time()
    
    ### collect data 
    res_in = {}
    res_out = {}

    ### elastic data 
    for i in range(3):
        if choose_flag == 0:
            text = elastic_regs_0[i].dump(json=True, from_hw=True)
            elastic_regs_0[i].clear()
            table = json.loads(text)
            id_str = elastic_id_strs_0[i]
            counter_str = elastic_counter_strs_0[i]
        else :
            text = elastic_regs_1[i].dump(json=True, from_hw=True)
            elastic_regs_1[i].clear()
            table = json.loads(text)
            id_str = elastic_id_strs_1[i]
            counter_str = elastic_counter_strs_1[i]
        for j in range(table_size):
            id = table[j]['data'][id_str][pipe_id]
            counter = table[j]['data'][counter_str][pipe_id]
            if id != 0 and counter != 0:
                if id not in res_in:
                    res_in[id] = counter
                else:
                    res_in[id] += counter

        for j in range(table_size, table_size+table_size):
            id = table[j]['data'][id_str][pipe_id]
            counter = table[j]['data'][counter_str][pipe_id]
            if id != 0 and counter != 0:
                if id not in res_out:
                    res_out[id] = counter
                else:
                    res_out[id] += counter

    if print_flag == 1:
        elastic_time = time.time()

    ### coco data
    if choose_flag == 0:
        counter_table = bfrt.elastic_coco.pipe.Egress.coco_counter_01
        id_table = bfrt.elastic_coco.pipe.Egress.coco_id_01
        counter_string = "Egress.coco_counter_01.f1"
        id_string = "Egress.coco_id_01.f1"
    else:
        counter_table = bfrt.elastic_coco.pipe.Egress.coco_counter_11
        id_table = bfrt.elastic_coco.pipe.Egress.coco_id_11
        counter_string = "Egress.coco_counter_11.f1"
        id_string = "Egress.coco_id_11.f1"

    res = {}
    counter_text = counter_table.dump(json=True, from_hw=True)
    counter_table.clear()
    counters = json.loads(counter_text)
    id_text = id_table.dump(json=True, from_hw=True)
    id_table.clear()
    ids = json.loads(id_text)

    for i in range(table_size):
        id = ids[i]['data'][id_string][0]
        counter = counters[i]['data'][counter_string][0]
        if id != 0 or counter != 0:
            if id not in res:
                res_in[id] = counter
            else:
                res_in[id] += counter

    for i in range(table_size,table_size+table_size):
        id = ids[i]['data'][id_string][0]
        counter = counters[i]['data'][counter_string][0]
        if id != 0 or counter != 0:
            if id not in res:
                res_out[id] = counter
            else:
                res_out[id] += counter
    if print_flag == 1:
        coco_time = time.time()

    ### data / 32
    for id in res_in:
        res_in[id] /= 32
    for id in res_out:
        res_out[id] /= 32

    ###send data
    data = {"in":res_in,"out":res_out}
    if print_flag == 1:
        dump_end_time = time.time()
        print("dump time: %f" % (dump_end_time - collect_start_time))
    data = json.dumps(data)

    len_send_data = len(data)
    f = struct.pack("i", len_send_data)
    s.send(f)
    s.sendall(data.encode("utf-8"))

    collect_end_time = time.time()
    if print_flag == 1:
        tcp_end_time = time.time()
        print("collect time: %f" % (collect_end_time - dump_end_time))

    ### receive data
    d = s.recv(struct.calcsize("i"))
    len_s = struct.unpack("i", d)
    num = len_s[0]//1024
    recv_data = ""
    current_length = 0
    while current_length < len_s[0]:
        recv_data += s.recv(1024).decode("utf-8")
        current_length = len(recv_data)

    if print_flag == 1:
        tcp_end_time = time.time()

    ### set INT
    ids = json.loads(recv_data)
    print(len(ids), 'flows are marked INT')
    mark_start_time = time.time()
    int_table = bfrt.elastic_coco.pipe.Ingress.mark_INT_table
    int_table.clear()
    for id in ids:
        int_table.add_with_mark_INT(int(id))
    if print_flag == 1:
        end_time = time.time()
        print('mark int time:', (end_time - mark_start_time))

s.close()