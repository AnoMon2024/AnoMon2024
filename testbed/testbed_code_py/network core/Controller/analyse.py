import numpy as np
import json
import sys
import getopt
from collections import defaultdict
import time

quantile_list = [0.01,0.05,0.1,0.5,0.9,0.95,0.99]
#The edge switch inside the network
edge_switch = [2,3]
#topo structure
switch_topo = [[2,3],[2,3],[0,1],[0,1]]

loss_threshold = 0.95
switch_num = 4
cell_num = 4
divide_threshold = 0
start_threshold = 0
end_threshold = 262144
pkt_counter = defaultdict(int)
interval = end_threshold - start_threshold

#calculate quantiles part
quantile_start_time = time.time()
for i in range(switch_num):
    filename = "sketch" + str(i) + ".json"
    f = open(filename,"r",encoding="utf-8")
    sketch = json.load(f)
    #each flows' data
    for item in sketch:
        srcip = item["srcip"]
        dstip = item["dstip"]
        quantile_data = defaultdict(int)
        #pkt counter
        for j in range(cell_num):
            counter_result = item["counter" + str(j)]
            pkt_counter[(i,srcip + dstip)] += counter_result
        #print(pkt_counter[(i,srcip+dstip)])
        pkt_total = pkt_counter[(i,srcip + dstip)]
        for j in range(len(quantile_list)):
            result = 0.0
            quantile = quantile_list[j]
            percentage_num = quantile * pkt_total
            #print("percentage_num:" + str(percentage_num))
            counter = 0
            for k in range(cell_num):
                #at current counter range
                if(counter + item["counter" + str(k)] >= percentage_num):
                    #need divide
                    if(item["counter" + str(k)] > divide_threshold):
                        divided_total = 0
                        #Micro sketch divied cells' totalnum
                        for l in range(cell_num):
                            divided_total += item["c" + str(k) + "-cell" + str(l)]
                        divided_percentage = []
                        child_cell_percentage = 0.0
                        #Micro sketch divied cells' percentage
                        for l in range(cell_num):
                            divided_percentage.append(float(item["c" + str(k) + "-cell" + str(l)])/divided_total)
                            #at current child-cell
                            if(counter + (child_cell_percentage + divided_percentage[l]) * item["counter" + str(k)] >= percentage_num):
                                result += interval/cell_num * k #part1 : counter value
                                result += interval/(cell_num * cell_num) * l #part2 : child cell value
                                result += (float(percentage_num - counter)/item["counter" + str(k)] - child_cell_percentage) * interval/(cell_num * cell_num)
                                break
                            child_cell_percentage += divided_percentage[l]
                    #do not need divide
                    else:
                        result += interval/cell_num * k
                        result += (percentage_num - counter)/item["counter" + str(k)] * (interval/cell_num)
                    break
                counter += item["counter" + str(k)]
            print("quantile : " + str(quantile_list[j]) + " result : " + str(result))
quantile_end_time = time.time()
print("quantile:" + str(quantile_end_time - quantile_start_time))

loss_start_time = time.time()
#packet loss check
def check_route(tag,switch,already_route):
    current_switch_flow_total = pkt_counter[(switch,tag)]
    for i in switch_topo[switch]:
        if(i not in already_route):
            next_jump_switch_flow_total = pkt_counter[(i,tag)]
            #packet loss happened
            if(float(next_jump_switch_flow_total)/current_switch_flow_total < loss_threshold and next_jump_switch_flow_total != 0):
                print("flow " + tag + "packet loss,happened between switch" + str(switch) + "and switch" + str(i))
                break
            elif(next_jump_switch_flow_total > current_switch_flow_total):
                continue
            else:
                tmp = already_route
                tmp.append(i)
                check_route(tag,i,tmp)
                already_route.remove(i)

key_list = pkt_counter.keys()
for item in key_list:
    switch = item[0]
    tag = item[1]
    if(switch in edge_switch):
        check_route(tag,switch,[switch])

loss_end_time = time.time()
print("loss check time:" + str(loss_end_time - loss_start_time))
