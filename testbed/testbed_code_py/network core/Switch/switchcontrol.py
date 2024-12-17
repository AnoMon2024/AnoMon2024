import json
import time
import os
import sys
import glob
import signal
import argparse
import socket
import struct
from tracemalloc import start
import math
from collections import defaultdict

bucket_tag_num = 1024
bucket_num = bucket_tag_num * 4
cell_num = bucket_tag_num * 4
divide_threshold = 0
window_size = 5
delay = 1.0

s = socket.socket()
#target server ip and port
server_ip = "172.16.6.141"
server_port = 5003
s.connect((server_ip,server_port))

total_time = 0
p4 = bfrt.CellSketch.pipe
#bucket1 registers : bucket1 srctag dsttag --> 2 sketches
bucket1_sketch1 = p4.MyEgress.bucket1_sketch1
bucket1_sketch2 = p4.MyEgress.bucket1_sketch2
bucket1_srciptag_sketch1 = p4.MyEgress.bucket1_srciptag_sketch1
bucket1_srciptag_sketch2 = p4.MyEgress.bucket1_srciptag_sketch2
bucket1_dstiptag_sketch1 = p4.MyEgress.bucket1_dstiptag_sketch1
bucket1_dstiptag_sketch2 = p4.MyEgress.bucket1_dstiptag_sketch2
#bucket2 registers : bucket2 srctag dsttag --> 2 sketches
bucket2_sketch1 = p4.MyEgress.bucket2_sketch1
bucket2_sketch2 = p4.MyEgress.bucket2_sketch2
bucket2_srciptag_sketch1 = p4.MyEgress.bucket2_srciptag_sketch1
bucket2_srciptag_sketch2 = p4.MyEgress.bucket2_srciptag_sketch2
bucket2_dstiptag_sketch1 = p4.MyEgress.bucket2_dstiptag_sketch1
bucket2_dstiptag_sketch2 = p4.MyEgress.bucket2_dstiptag_sketch2
#cell registers : part1 part2
cell_part1_sketch1 = p4.MyEgress.cell_part1_sketch1
cell_part1_sketch2 = p4.MyEgress.cell_part1_sketch2
cell_part2_sketch1 = p4.MyEgress.cell_part2_sketch1
cell_part2_sketch2 = p4.MyEgress.cell_part2_sketch2
bucket1_to_cell_part1_sketch1 = p4.MyEgress.bucket1_to_cell_part1_sketch1
bucket1_to_cell_part1_sketch2 = p4.MyEgress.bucket1_to_cell_part1_sketch2
bucket1_to_cell_part2_sketch1 = p4.MyEgress.bucket1_to_cell_part2_sketch1
bucket1_to_cell_part2_sketch2 = p4.MyEgress.bucket1_to_cell_part2_sketch2
bucket2_to_cell_part1_sketch1 = p4.MyEgress.bucket2_to_cell_part1_sketch1
bucket2_to_cell_part1_sketch2 = p4.MyEgress.bucket2_to_cell_part1_sketch2
bucket2_to_cell_part2_sketch1 = p4.MyEgress.bucket2_to_cell_part2_sketch1
bucket2_to_cell_part2_sketch2 = p4.MyEgress.bucket2_to_cell_part2_sketch2

#Clock synchronization
change_time = math.ceil(time.time() / window_size) * window_size
#loop start
while True:
    while time.time() < change_time:
        time.sleep(0.1)
    #switch sketch shift flag , when choose flag is 1 , means read sketch1 and record in sketch2
    choose_flag = (time.time() // window_size) % 2
    data = []
    #wait all packets with the same mark pass 
    while time.time() < change_time + delay:
        time.sleep(0.1)
    #start time : The time Dump operation starts
    start_time = time.time()
    #update next loop's start time for clock synchronization
    change_time = math.ceil(time.time() / window_size) * window_size
    if choose_flag == 1:
        #dump data from switch data plane
        bucket1_result = bucket1_sketch1.dump(json=True, from_hw=True)
        bucket2_result = bucket2_sketch1.dump(json=True, from_hw=True)
        bucket1_srciptag_result = bucket1_srciptag_sketch1.dump(json=True, from_hw=True)
        bucket1_dstiptag_result = bucket1_dstiptag_sketch1.dump(json=True, from_hw=True)
        bucket2_srciptag_result = bucket2_srciptag_sketch1.dump(json=True, from_hw=True)
        bucket2_dstiptag_result = bucket2_dstiptag_sketch1.dump(json=True, from_hw=True)
        cell_bucket1_part1_result = cell_part1_sketch1.dump(json=True, from_hw=True)
        cell_bucket1_part2_result = cell_part2_sketch1.dump(json=True, from_hw=True)
        bucket1_data = json.loads(bucket1_result)
        bucket2_data = json.loads(bucket2_result)
        bucket1_srciptag_data = json.loads(bucket1_srciptag_result)
        bucket1_dstiptag_data = json.loads(bucket1_dstiptag_result)
        bucket2_srciptag_data = json.loads(bucket2_srciptag_result)
        bucket2_dstiptag_data = json.loads(bucket2_dstiptag_result)
        cell_bucket1_part1_data = json.loads(cell_bucket1_part1_result)
        cell_bucket1_part2_data = json.loads(cell_bucket1_part2_result)
        bucket1_to_cell_part1_result = bucket1_to_cell_part1_sketch1.dump(json=True, from_hw=True)
        bucket1_to_cell_part2_result = bucket1_to_cell_part2_sketch1.dump(json=True, from_hw=True)
        bucket2_to_cell_part1_result = bucket2_to_cell_part1_sketch1.dump(json=True, from_hw=True)
        bucket2_to_cell_part2_result = bucket2_to_cell_part2_sketch1.dump(json=True, from_hw=True)
        bucket1_to_cell_part1_data = json.loads(bucket1_to_cell_part1_result)
        bucket1_to_cell_part2_data = json.loads(bucket1_to_cell_part2_result)
        bucket2_to_cell_part1_data = json.loads(bucket2_to_cell_part1_result)
        bucket2_to_cell_part2_data = json.loads(bucket2_to_cell_part2_result)
        #dump time : The time Dump operation ends
        dump_time = time.time()
        #print("dump time : " + str(dump_time - start_time))
        #extract statistics from sketch
        for i in range (bucket_tag_num):
            bucket1_sip = bucket1_srciptag_data[i]["data"]["MyEgress.bucket1_srciptag_sketch1.f1"][3]
            bucket2_sip = bucket2_srciptag_data[i]["data"]["MyEgress.bucket2_srciptag_sketch1.f1"][3]
            bucket1_dip = bucket1_dstiptag_data[i]["data"]["MyEgress.bucket1_dstiptag_sketch1.f1"][3]
            bucket2_dip = bucket2_dstiptag_data[i]["data"]["MyEgress.bucket2_dstiptag_sketch1.f1"][3]
            if(bucket1_sip != 0 and bucket1_dip !=0):
                tmp = {}
                tmp["srcip"] = bucket1_sip
                tmp["dstip"] = bucket1_dip
                for j in range(4):
                    bucket1_tmp = bucket1_data[i*4 + j]["data"]["MyEgress.bucket1_sketch1.f1"][3]
                    tmp["counter" + str(j)] = bucket1_tmp
                    if(bucket1_tmp > divide_threshold):
                        cell_hash_part1 = bucket1_to_cell_part1_data[i*4 + j]["data"]["MyEgress.bucket1_to_cell_part1_sketch1.f1"][3]
                        cell_hash_part2 = bucket1_to_cell_part2_data[i*4 + j]["data"]["MyEgress.bucket1_to_cell_part2_sketch1.f1"][3]
                        for k in range(4):
                            cell_tmp_1 = cell_bucket1_part1_data[cell_hash_part1*4 + k]["data"]["MyEgress.cell_part1_sketch1.f1"][3]
                            cell_tmp_2 = cell_bucket1_part2_data[cell_hash_part2*4 + k]["data"]["MyEgress.cell_part2_sketch1.f1"][3]
                            cell_tmp = min(cell_tmp_1,cell_tmp_2)
                            tmp["c" + str(j) + "-cell" + str(k)] = cell_tmp
                data.append(tmp)
            if(bucket2_sip != 0 and bucket2_dip !=0):
                tmp = {}
                tmp["srcip"] = bucket2_sip
                tmp["dstip"] = bucket2_dip
                for j in range(4):
                    bucket2_tmp = bucket2_data[i*4 + j]["data"]["MyEgress.bucket2_sketch1.f1"][3]
                    tmp["counter" + str(j)] = bucket2_tmp
                    if(bucket2_tmp > divide_threshold):
                        cell_hash_part1 = bucket2_to_cell_part1_data[i*4 + j]["data"]["MyEgress.bucket2_to_cell_part1_sketch1.f1"][3]
                        cell_hash_part2 = bucket2_to_cell_part2_data[i*4 + j]["data"]["MyEgress.bucket2_to_cell_part2_sketch1.f1"][3]
                        for k in range(4):
                            cell_tmp_1 = cell_bucket1_part1_data[cell_hash_part1*4 + k]["data"]["MyEgress.cell_part1_sketch1.f1"][3]
                            cell_tmp_2 = cell_bucket1_part2_data[cell_hash_part2*4 + k]["data"]["MyEgress.cell_part2_sketch1.f1"][3]
                            cell_tmp = min(cell_tmp_1,cell_tmp_2)
                            tmp["c" + str(j) + "-cell" + str(k)] = cell_tmp
                data.append(tmp)
        bucket1_sketch1.clear()
        bucket2_sketch1.clear()
        bucket1_srciptag_sketch1.clear()
        bucket1_dstiptag_sketch1.clear()
        bucket2_srciptag_sketch1.clear()
        bucket2_dstiptag_sketch1.clear()
        cell_part1_sketch1.clear()
        cell_part2_sketch1.clear()
        bucket1_to_cell_part1_sketch1.clear()
        bucket1_to_cell_part2_sketch1.clear()
        bucket2_to_cell_part1_sketch1.clear()
        bucket2_to_cell_part2_sketch1.clear()
    elif choose_flag == 0:
        bucket1_result = bucket1_sketch2.dump(json=True, from_hw=True)
        bucket2_result = bucket2_sketch2.dump(json=True, from_hw=True)
        bucket1_srciptag_result = bucket1_srciptag_sketch2.dump(json=True, from_hw=True)
        bucket1_dstiptag_result = bucket1_dstiptag_sketch2.dump(json=True, from_hw=True)
        bucket2_srciptag_result = bucket2_srciptag_sketch2.dump(json=True, from_hw=True)
        bucket2_dstiptag_result = bucket2_dstiptag_sketch2.dump(json=True, from_hw=True)
        cell_bucket1_part1_result = cell_part1_sketch2.dump(json=True, from_hw=True)
        cell_bucket1_part2_result = cell_part2_sketch2.dump(json=True, from_hw=True)
        bucket1_data = json.loads(bucket1_result)
        bucket2_data = json.loads(bucket2_result)
        bucket1_srciptag_data = json.loads(bucket1_srciptag_result)
        bucket1_dstiptag_data = json.loads(bucket1_dstiptag_result)
        bucket2_srciptag_data = json.loads(bucket2_srciptag_result)
        bucket2_dstiptag_data = json.loads(bucket2_dstiptag_result)
        cell_bucket1_part1_data = json.loads(cell_bucket1_part1_result)
        cell_bucket1_part2_data = json.loads(cell_bucket1_part2_result)
        bucket1_to_cell_part1_result = bucket1_to_cell_part1_sketch2.dump(json=True, from_hw=True)
        bucket1_to_cell_part2_result = bucket1_to_cell_part2_sketch2.dump(json=True, from_hw=True)
        bucket2_to_cell_part1_result = bucket2_to_cell_part1_sketch2.dump(json=True, from_hw=True)
        bucket2_to_cell_part2_result = bucket2_to_cell_part2_sketch2.dump(json=True, from_hw=True)
        bucket1_to_cell_part1_data = json.loads(bucket1_to_cell_part1_result)
        bucket1_to_cell_part2_data = json.loads(bucket1_to_cell_part2_result)
        bucket2_to_cell_part1_data = json.loads(bucket2_to_cell_part1_result)
        bucket2_to_cell_part2_data = json.loads(bucket2_to_cell_part2_result)
        dump_time = time.time()
        print("dump time : " + str(dump_time - start_time))
        for i in range (bucket_tag_num):
            bucket1_sip = bucket1_srciptag_data[i]["data"]["MyEgress.bucket1_srciptag_sketch2.f1"][3]
            bucket2_sip = bucket2_srciptag_data[i]["data"]["MyEgress.bucket2_srciptag_sketch2.f1"][3]
            bucket1_dip = bucket1_dstiptag_data[i]["data"]["MyEgress.bucket1_dstiptag_sketch2.f1"][3]
            bucket2_dip = bucket2_dstiptag_data[i]["data"]["MyEgress.bucket2_dstiptag_sketch2.f1"][3]
            if(bucket1_sip != 0 and bucket1_dip !=0):
                tmp = {}
                tmp["srcip"] = bucket1_sip
                tmp["dstip"] = bucket1_dip
                for j in range(4):
                    bucket1_tmp = bucket1_data[i*4 + j]["data"]["MyEgress.bucket1_sketch2.f1"][3]
                    tmp["counter" + str(j)] = bucket1_tmp
                    if(bucket1_tmp > divide_threshold):
                        cell_hash_part1 = bucket1_to_cell_part1_data[i*4 + j]["data"]["MyEgress.bucket1_to_cell_part1_sketch2.f1"][3]
                        cell_hash_part2 = bucket1_to_cell_part2_data[i*4 + j]["data"]["MyEgress.bucket1_to_cell_part2_sketch2.f1"][3]
                        for k in range(4):
                            cell_tmp_1 = cell_bucket1_part1_data[cell_hash_part1*4 + k]["data"]["MyEgress.cell_part1_sketch2.f1"][3]
                            cell_tmp_2 = cell_bucket1_part2_data[cell_hash_part2*4 + k]["data"]["MyEgress.cell_part2_sketch2.f1"][3]
                            cell_tmp = min(cell_tmp_1,cell_tmp_2)
                            tmp["c" + str(j) + "-cell" + str(k)] = cell_tmp
                data.append(tmp)
            if(bucket2_sip != 0 and bucket2_dip !=0):
                tmp = {}
                tmp["srcip"] = bucket2_sip
                tmp["dstip"] = bucket2_dip
                for j in range(4):
                    bucket2_tmp = bucket2_data[i*4 + j]["data"]["MyEgress.bucket2_sketch2.f1"][3]
                    tmp["counter" + str(j)] = bucket2_tmp
                    if(bucket2_tmp > divide_threshold):
                        cell_hash_part1 = bucket2_to_cell_part1_data[i*4 + j]["data"]["MyEgress.bucket2_to_cell_part1_sketch2.f1"][3]
                        cell_hash_part2 = bucket2_to_cell_part2_data[i*4 + j]["data"]["MyEgress.bucket2_to_cell_part2_sketch2.f1"][3]
                        for k in range(4):
                            cell_tmp_1 = cell_bucket1_part1_data[cell_hash_part1*4 + k]["data"]["MyEgress.cell_part1_sketch2.f1"][3]
                            cell_tmp_2 = cell_bucket1_part2_data[cell_hash_part2*4 + k]["data"]["MyEgress.cell_part2_sketch2.f1"][3]
                            cell_tmp = min(cell_tmp_1,cell_tmp_2)
                            tmp["c" + str(j) + "-cell" + str(k)] = cell_tmp
                data.append(tmp)
        bucket1_sketch2.clear()
        bucket2_sketch2.clear()
        bucket1_srciptag_sketch2.clear()
        bucket1_dstiptag_sketch2.clear()
        bucket2_srciptag_sketch2.clear()
        bucket2_dstiptag_sketch2.clear()
        cell_part1_sketch2.clear()
        cell_part2_sketch2.clear()
        bucket1_to_cell_part1_sketch2.clear()
        bucket1_to_cell_part2_sketch2.clear()
        bucket2_to_cell_part1_sketch2.clear()
        bucket2_to_cell_part2_sketch2.clear()
    print("data load over\n")
    #handele time : the time when data handle work is over
    handle_time = time.time()
    #print("handle time : " + str(handle_time - start_time))
    data_to_send = json.dumps(data)
    len_send_data = len(data_to_send)
    f = struct.pack("i", len_send_data)
    s.send(f)
    #send reshaped data to center servers
    s.sendall(data_to_send.encode("utf-8"))
    #end time : The time all the data has been sent
    end_time = time.time()
    #print("send_time:"+str(end_time-handle_time))
    #print("send_time + handle_time:" + str(end_time - dump_time))
    time.sleep(5 - end_time + start_time)

