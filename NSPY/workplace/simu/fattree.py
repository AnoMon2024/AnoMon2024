from functools import partial
from random import expovariate, sample
from numpy import random as nprdm
import random
from ns.packet.dist_generator import DistPacketGenerator
from ns.packet.sink import PacketSink
from ns.switch.switch import SimplePacketSwitch
from ns.switch.switch import FairPacketSwitch
# from ns.switch.switch import CheckSwitch
from ns.topos.fattree import build as build_fattree
from ns.topos.utils import generate_fib
from ns.topos.utils import PathGenerator
# from ns.topos.utils import generate_fib, generate_flows
import simpy
import numpy as np
import argparse
import datetime

import sys
sys.path.append('../')
import utils.TCP_distribution as tcpdist
import utils.create_error as cer

parser = argparse.ArgumentParser(description="draw results of a single flow")
parser.add_argument('--culprit_typ', default=3, type=int, help='type of problems')
parser.add_argument('--mem', default=800, type=float, help='memory')
parser.add_argument('--algo', default="dleft", type=str, help='algorithm')
parser.add_argument('--error_ratio', default=0.25, type=float, help='ratio of error in a section')
#####################################################
parser.add_argument('--test', default=0, type=int, help='type of test')
parser.add_argument('--mem_num', default=0, type=int, help='rank of memory')
parser.add_argument('--window', default=1, type=float, help='size of window compared to a section')
parser.add_argument('--err_flow_ratio', default=0.1, type=float, help='ratio of culprit hosts')
parser.add_argument('--flow_group_typ', default="subnet", type=str)
parser.add_argument('--flow_group_num',default=0,type=int)
parser.add_argument('--heavy_change',default=0,type=int)
parser.add_argument('--test_ns',default=0,type=int)
global args
args = parser.parse_args()
tst = ["core","time","edge"]

C_path="../C/"+args.algo+"/"
sys.path.append(C_path)

import Sketches
culprit_fg = set()
edge_num=0
edge_recall=0
edge_prec=0
print("args",args)
#####################################################

check_num=0
check_recall=0
check_prec=0

global correct_list,ab_flow_list,flow_drop_list
# reported_list = []
correct_list = []
ab_flow_list = []
flow_drop_list = []
memcost = args.mem
print("#",args.culprit_typ)
random.seed(datetime.datetime.now().second)
np.random.seed(datetime.datetime.now().second)
ff = open(C_path+"log.txt","w")

use_ns = args.test_ns
n_flows = 100000
k = 4
pir = 1000000000000000
buffer_size = 10000000000000000000000000
mean_pkt_size = 10.0
ab_fgroup = []
env = simpy.Environment()
sec_time=10
all_time=100
tp_time=0
sz = all_time//sec_time
poi_distri = nprdm.poisson(lam=sec_time,size=sz)
nor_distri = nprdm.normal(loc=sec_time*args.error_ratio,scale=sec_time*args.error_ratio/2,size=sz)
print("poi:",poi_distri,file=ff)
print("nor:",nor_distri,file=ff)
print("poi:",poi_distri)
print("nor:",nor_distri)
culprit_time=dict()
for s in range(sz):
    last_time = max(1,nor_distri[s])
    culprit_time[tp_time] = tp_time + last_time
    tp_time+=poi_distri[s]

print("-------culprit_time-------\n",culprit_time)

sketches = Sketches.Sketches()

culprit_num=int(k*k*k//4*args.err_flow_ratio)
culprit_typ= args.culprit_typ
fg_typ = args.flow_group_typ
culprit_name = ["black","loop","jitter","wait"]

f = open(C_path+"log_"+args.algo+"_"+culprit_name[culprit_typ]+".txt","w")
for key in culprit_time.keys():
    print("start:",key,"end:",culprit_time[key],file=f)
f.close()

ft = build_fattree(k)
class Time_report:
    def __init__(self,
                 env):
        self.env = env
        self.action = env.process(self.run())

    def run(self):
        while True:
            yield self.env.timeout(1)
            print("time",self.env.now,end="; ",flush=True)

time_rp = Time_report(env)
class CheckSwitch:
    def __init__(self,
                 env,
                 ft,
                 ab_fgroup,
                 sketches,
                 all_flows,
                 flow_group_map,
                 duration=10) -> None:
        self.env = env
        self.ft = ft
        self.duration = duration
        self.ab_fgroup = ab_fgroup
        self.sketches = sketches
        self.all_flows = all_flows
        self.flow_group_map = flow_group_map
        self.action = env.process(self.run())
        self.interval = 1
        self.interval_last = -1
        self.sk_clear_flag = False
        self.all_bd = 0
        self.bd_cnt = 0

    def convert(self,x):
        res = x.srcIP_dstIP()
        res = (res<<16)+x.srcPort()
        res = (res<<16)+x.dstPort()
        res = (res<<8)+x.proto()
        return res

    def converts(self,xs):
        ress = []
        for x in xs:
            res = self.convert(x)
            ress.append(res)
        return ress

    def intrsec(self,a1,b1,a2,b2):
        if a1>=a2 and a1<b2 and b1>b2:
            return 1
        elif b1>a2 and b1<=b2 and a1<a2:
            return 1
        elif a1>=a2 and b1<=b2:
            return 1
        elif a1<a2 and b1>b2:
            return 1
        return 0
    
    def get_ab_fg(self):
        fg_ratio_map = dict()
        
        for fg_id in self.flow_group_map.keys():
            ratio = 0.0
            for flow_id in self.flow_group_map[fg_id]:
                src_ip = flow_id>>72
                dst_ip = flow_id>>40 & 0xffffffff
                src_port = (flow_id>>24) & 0xffff
                dst_port = (flow_id>>8) & 0xffff
                _proto = flow_id & 0xff
                ratio += self.sketches.check_ratio_with_fid(src_ip,dst_ip,src_port,dst_port,_proto,culprit_typ)
            fg_ratio_map[fg_id] = ratio
        
        sorted_ratio = sorted(fg_ratio_map.items(), key = lambda x:x[1], reverse=True)
        # print("-------sorted_ratio-------\n",sorted_ratio)
        res = [x[0] for x in sorted_ratio]
        return res[0:culprit_num]

    def get_packet_drop_flow(self,limit):
        reported_list = []
        
        for flow_id in range(0,n_flows):
            flow = self.all_flows[flow_id]
            
            src_ip = flow.fid>>72
            dst_ip = flow.fid>>40 & 0xffffffff
            src_port = (flow.fid>>24) & 0xffff
            dst_port = (flow.fid>>8) & 0xffff
            _proto = flow.fid & 0xff

            packet_in = self.ft.nodes[flow.path[1]]['device'].sketch2.query_pre(src_ip,dst_ip,src_port,dst_port,_proto)
            packet_out = self.ft.nodes[flow.path[-2]]['device'].sketch3.query_pre(src_ip,dst_ip,src_port,dst_port,_proto)
            if flow.fid in ab_flow_list:
                print(flow.fid,",",packet_in,",",packet_out)
            if packet_in - packet_out >= limit:
                reported_list.append(flow.fid)

        return reported_list

    def check_netseer(self):
        p_drop_map = {}
        for n in self.ft.nodes():
            d_map = self.ft.nodes[n]['device'].netseer.query_all()

            for key in d_map.keys():
                if p_drop_map.get(key) == None:
                    p_drop_map[key] = d_map[key]
                else:
                    p_drop_map[key] += d_map[key]
        return p_drop_map

    def check_bd(self):
        basic_mem = 60000 #byte
        sketch_mem = (cnt_edge+cnt_core)*basic_mem
        netseer_mem = (cnt_core+cnt_edge)*basic_mem
        netseer_id_mem = 13
        netseer_counter_mem = 4
        netseer_extra_packet = 0
        netseer_pkt_header_mem = 42
        sketch_pkt_header_mem = 54
        max_load = 1500
        for n in self.ft.nodes():
            netseer_extra_packet += self.ft.nodes[n]['device'].netseer.conflict_cnt
            self.ft.nodes[n]['device'].netseer.conflict_cnt = 0
        netseer_extra_mem = netseer_extra_packet * (netseer_pkt_header_mem + netseer_id_mem + netseer_counter_mem)
        netseer_mem += ((netseer_mem // max_load) + 1)*netseer_pkt_header_mem
        sketch_mem += ((sketch_mem // max_load) + 1)*sketch_pkt_header_mem
        sketch_report_bd = self.sketches.get_extra_bd()
        print("sketch bandwidth: ",(sketch_mem*8/1000000)/5," Mbps")
        print("sketch report bd: ",(sketch_report_bd*8/1000000)/5, "Mbps")
        print("netseer bandwidth: ",((netseer_extra_mem+netseer_mem)*8/1000000)/5," Mbps")
        self.all_bd += (((netseer_extra_mem+netseer_mem)*8/1000000)/5)
        self.bd_cnt += 1
        print("avg_bd:",self.all_bd/self.bd_cnt)

    def run(self):
        while True:
            yield self.env.timeout(1)
            f = open(C_path+"log_"+args.algo+"_"+culprit_name[culprit_typ]+".txt","a")
            
            ab_flow_list = []
            for ab_fg in culprit_flows:
                ab_flow_list.append(flow_group_map[ab_fg])
            #ab_flow_list.extend(self.sketches.get_ab_fs())
            #print("-------ab_flow_list-------",ab_flow_list)

            reset_interval = True
            now_time = int(self.env.now)
            print("now_time:",now_time,"in last:",self.interval_last)
            # if self.env.now > self.duration+1:
            
            for key in culprit_time.keys():
                if not self.intrsec(self.env.now-self.duration,self.env.now,key+1,culprit_time[key]):
                    self.sk_clear_flag = False
                    continue
                reset_interval = False
                if self.interval_last == -1:
                    self.interval_last = now_time
                    self.sk_clear_flag = True
                else:
                    if now_time - self.interval_last >= self.interval:
                        self.interval_last = now_time
                        self.sk_clear_flag = True
                    else:
                        self.sk_clear_flag = False
                        break
                    
                global check_num,check_prec,check_recall
                
                if args.heavy_change != 0:
                    reported_list = self.get_packet_drop_flow(args.heavy_change)
                    if len(reported_list):
                        inter_num=0
                        for ite in ab_flow_list:
                            if ite in reported_list:
                                inter_num+=1
                        print("inter_num:",inter_num)
                        prec = inter_num/len(reported_list)
                        recall = inter_num/len(ab_flow_list)
                    else:
                        prec = 0
                        recall = 0

                    
                    check_num+=1
                    check_prec+=prec
                    check_recall+=recall
                    print("recall",recall,"precision",prec)
                    
                    break
                # for dle in range(0,cnt_core):
                #     print(dle,self.sketches.coresketch[dle].PPrint(),file=f)
                # for dle in range(0,cnt_edge):
                #     print(dle,self.sketches.edgesketch[dle].PPrint(),file=f)
                reported_list = []
                for j in range(101,102,2):
                # for j in range(1,10,2):
                    t=0
                    if culprit_typ==0:
                        if args.algo == "dleft":
                            t=0.99999995
                        else:
                            t=0.5
                    elif culprit_typ == 1:
                        t=1.000004
                    else:
                        t = 1.000005
                    ##############################################
                    # if args.test==0:
                    #     print('test 0: ',args.culprit_typ,file=f)
                    #     s="../res/"+args.algo+"_"+culprit_name[args.culprit_typ]+".csv"
                    #     f_res = open(s,"a")
                    # elif args.test==1:
                    #     print('test 1: ',args.culprit_typ,file=f)
                    #     s="../res_time/last"+str(args.error_ratio)+"_"+culprit_name[args.culprit_typ]+".csv"
                    #     f_res = open(s,"a")
                    # elif args.test==2:
                    #     print('test 2: ',args.culprit_typ,file=f)
                    #     s="../res_edge/eflo"+str(args.err_flow_ratio)+"_"+culprit_name[args.culprit_typ]+".csv"
                    #     f_res = open(s,"a")
                    ##############################################
                    if args.test!=2:
                        print("traversing",end=": ",flush=True)
                        for flow_id in range(0,n_flows):
                            flow = self.all_flows[flow_id]

                            src_ip = flow.fid>>72
                            dst_ip = flow.fid>>40 & 0xffffffff
                            src_port = (flow.fid>>24) & 0xffff
                            dst_port = (flow.fid>>8) & 0xffff
                            _proto = flow.fid & 0xff
                            if (args.algo == "dleft" and flow.fg_id not in self.ab_fgroup) or flow.is_big != 1:
                                continue
                        
                            length = len(flow.path)
                            # print("flow",flow.fid,"path",flow.path,file=f)
                            print("flow",flow.fid,"interval",flow.pkt_gen.arrival_interval,"path",flow.path,file=f)
                            if culprit_typ==3:
                                for i in range(2,length-1):
                                    last_wait = self.ft.nodes[flow.path[i-1]]['device'].sketch1.query_wait_pre(src_ip,dst_ip,src_port,dst_port,_proto)
                                    prst_wait = self.ft.nodes[flow.path[i]]['device'].sketch1.query_wait_pre(src_ip,dst_ip,src_port,dst_port,_proto)
                                    last_freq = self.ft.nodes[flow.path[i-1]]['device'].sketch1.query_pre(src_ip,dst_ip,src_port,dst_port,_proto)
                                    prst_freq = self.ft.nodes[flow.path[i]]['device'].sketch1.query_pre(src_ip,dst_ip,src_port,dst_port,_proto)
                                    print(flow.path[i-1],last_wait,last_freq,end=' * ',file=f)
                                    print(flow.path[i],prst_wait,prst_freq,file=f)
                                    if last_wait == 0:
                                        break
                                    if prst_wait/last_wait > t:
                                        print("flow",flow_id,"ab-switch",flow.path[i],file=f)
                                        reported_list.append([flow.fid,flow.path[i]])
                                        break
                            elif culprit_typ==2:
                                for i in range(2,length-1):
                                    last_interval = self.ft.nodes[flow.path[i-1]]['device'].sketch1.query_interval_pre(src_ip,dst_ip,src_port,dst_port,_proto)
                                    prst_interval = self.ft.nodes[flow.path[i]]['device'].sketch1.query_interval_pre(src_ip,dst_ip,src_port,dst_port,_proto)
                                    last_freq = self.ft.nodes[flow.path[i-1]]['device'].sketch1.query_pre(src_ip,dst_ip,src_port,dst_port,_proto)
                                    prst_freq = self.ft.nodes[flow.path[i]]['device'].sketch1.query_pre(src_ip,dst_ip,src_port,dst_port,_proto)
                                    print(flow.path[i-1],last_interval,last_freq,end=' * ',file=f)
                                    print(flow.path[i],prst_interval,prst_freq,file=f)
                                    # if [flow.fid,flow.path[i-1]] in correct_list:
                                    #         print("prst:",prst_interval,", last:",last_interval)
                                    if last_interval == 0:
                                        break
                                    if prst_interval/last_interval > t:
                                        print("flow",flow_id,"ab-switch",flow.path[i-1],file=f)
                                        reported_list.append([flow.fid,flow.path[i-1]])
                                        break
                            elif culprit_typ==1:
                                for i in range(2,length-1):
                                    last_freq = self.ft.nodes[flow.path[i-1]]['device'].sketch1.query_pre(src_ip,dst_ip,src_port,dst_port,_proto)
                                    prst_freq = self.ft.nodes[flow.path[i]]['device'].sketch1.query_pre(src_ip,dst_ip,src_port,dst_port,_proto)
                                    print(flow.path[i-1],last_freq,end=' ',file=f)
                                    print(flow.path[i],prst_freq,file=f)
                                    if [flow.fid,flow.path[i]] in correct_list:
                                        print("prst:",prst_freq,", last:",last_freq)
                                    if last_freq == 0:
                                        break
                                    if prst_freq/last_freq > t:
                                        print("flow",flow_id,"ab-switch",flow.path[i],file=f)
                                        reported_list.append([flow.fid,flow.path[i]])
                                        break
                            elif culprit_typ==0:
                                for i in range(2,length-1):
                                    last_freq = self.ft.nodes[flow.path[i-1]]['device'].sketch1.query_pre(src_ip,dst_ip,src_port,dst_port,_proto)
                                    prst_freq = self.ft.nodes[flow.path[i]]['device'].sketch1.query_pre(src_ip,dst_ip,src_port,dst_port,_proto)
                                    print(flow.path[i-1],last_freq,end=' ',file=f)
                                    print(flow.path[i],prst_freq,file=f)
                                    # if [flow.fid,flow.path[i-1]] in correct_list:
                                    #     print("prst:",prst_freq,", last:",last_freq)
                                    if last_freq == 0:
                                        break
                                    if prst_freq/last_freq < t:
                                        #print("flow",flow_id,"ab-switch",flow.path[i],file=f)
                                        reported_list.append([flow.fid,flow.path[i]])
                                        break
                        
                        if use_ns==1:
                            if now_time % 5 == 0:
                                self.check_bd()
                            netseer_result = self.check_netseer()
                            reported_list = netseer_result.keys()
                            #print("reported list\n",reported_list)
                            inter_num=0
                            for ite in flow_drop_list:
                                if str(ite) in reported_list:
                                    inter_num+=1
                            prec = inter_num/len(reported_list)
                            recall = inter_num/len(flow_drop_list)
                        elif len(reported_list):
                            inter_num=0
                            for ite in correct_list:
                                if ite in reported_list:
                                    inter_num+=1
                            prec = inter_num/len(reported_list)
                            recall = inter_num/len(correct_list)
                            # res_str = str(memcost)+","+str(prec)+","+str(recall)+","
                            # print(res_str,file=f_res)
                        else:
                            prec = 0
                            recall = 0
                            # res_str = str(memcost)+","+str(prec)+","+str(recall)+","
                            # print(res_str,file=f_res)
                        #global check_num,check_prec,check_recall
                        check_num+=1
                        check_prec+=prec
                        check_recall+=recall
                        # print("reported",len(reported_list),reported_list,file=f)
                        # print("correct",len(correct_list),correct_list,file=f)
                        sketch_report_bd = self.sketches.get_extra_bd()
                        print("sketch report bd: ",(sketch_report_bd*8/1000000)/5, "Mbps")
                        print("recall",recall,"precision",prec)
                        #f_res.close()
                
                break    

            if reset_interval == True:
                self.interval_last = -1

            if args.algo == "dleft":
                #self.ab_fgroup = self.sketches.ab_fg(culprit_num,culprit_typ)
                self.ab_fgroup = self.get_ab_fg()
                print("lala",len(self.ab_fgroup),self.ab_fgroup)
###################################################
                if args.test==2:
                    for key in culprit_time.keys():
                        if not self.intrsec(self.env.now-self.duration,self.env.now,key,culprit_time[key]):
                            continue
                        inter_num=0
                        rep_num=0
                        for ite in self.ab_fgroup:
                            # if ite==0:
                            #     continue
                            rep_num+=1
                            if ite in culprit_fg:
                                inter_num+=1
                        prec=0
                        if rep_num:
                            prec = inter_num/rep_num
                        recall=inter_num/len(culprit_fg)
                        global edge_num,edge_prec,edge_recall
                        edge_num+=1
                        edge_prec+=prec
                        edge_recall+=recall
                        print("reported",len(self.ab_fgroup),self.ab_fgroup,file=f)
                        print("correct",len(culprit_fg),culprit_fg,file=f)
                        print("recall--",recall,"precision--",prec)
                        break
            else:
                self.ab_fgroup = culprit_fg
                ###################################################
            for n in self.ft.nodes():
                node = self.ft.nodes[n]
                node['device'].demux.loop_num=dict()
            
                if args.algo == "dleft":
                    for port in node['device'].egress_ports:
                        port.ab_fgroup = self.ab_fgroup
                        port.out.ab_fgroup = self.ab_fgroup
                    node['device'].demux.ab_fgroup = self.ab_fgroup
            if self.sk_clear_flag:
                self.sketches.Clear()
            f.close()

hosts = set()
for n in ft.nodes():
    if ft.nodes[n]['type'] == 'host':
        hosts.add(n)


PathGene = PathGenerator(ft,hosts,k,args.flow_group_num)
all_flows, flow_groupid, flow_group_map, path_dict = PathGene.generate_flows(n_flows,k,fg_typ)
print("-------fg_map-------",flow_group_map.keys())
size_dist = partial(expovariate, 1.0 / mean_pkt_size)
tmp_list = []

culprit_flows, culprit_switches, loop_pair = cer.create_error(flow_group_map.keys(),path_dict,culprit_typ,culprit_num,k)
print(culprit_switches,file=ff)
print(culprit_flows,file=ff)
print("------cul flow ----\n",culprit_flows)
# for i in culprit_flows:
#     print("---- len ",i,"----",len(flow_group_map[i]))
print("------cul switch ----\n",culprit_switches)
def constnt():
    return 0.1

ab_flow_cnt_map = dict()
for ab_fgid in culprit_flows:
    ab_flow_cnt_map[ab_fgid] = 0
    
for flow_id, flow in all_flows.items():
    arr_dist = constnt

    arrival_interval, is_big = tcpdist.TCP_Distribution(time = sec_time,lamda = 0.0001)
    #print("arrint--",arrival_interval)
    #flow.fid+= (is_big<<72)
    is_big=1 #for testing netseer bandwidth
    flow.is_big = is_big
    if (flow_groupid[flow.fid] in culprit_flows) and (flow.is_big == 1) and (args.heavy_change == 0 or (args.heavy_change!=0 and 1/arrival_interval > args.heavy_change)):
        ab_flow_list.append(flow.fid)
        if culprit_typ == 0:
            flow_drop_list.append(flow.fid)
        ab_flow_cnt_map[flow_groupid[flow.fid]] += 1
        print("culprit_switches",culprit_switches[flow_groupid[flow.fid]],"path",flow.path,file=ff)
        for switch in flow.path:
            if switch in culprit_switches[flow_groupid[flow.fid]]:
                correct_list.append([flow.fid, switch])
                culprit_fg.add(flow_groupid[flow.fid])
                break

    pg = DistPacketGenerator(env,
                             f"Flow_{flow.fid}",
                             arrival_dist = arr_dist,
                             arrival_interval=0.5,
                             size_dist=size_dist,
                             flow_id=flow.fid,
                             fg_id = flow.fg_id,
                             is_big = flow.is_big)
    ps = PacketSink(env)

    all_flows[flow_id].pkt_gen = pg
    all_flows[flow_id].pkt_sink = ps

print("-------culprit_cnt-------\n",ab_flow_cnt_map)
# print("-------flow_drop-------\n",flow_drop_list)
# print("-------correct_list-------\n",len(correct_list))
print("-------culprit_fg-------\n",culprit_fg)

ft = generate_fib(ft, all_flows)
n_classes_per_port = 4
weights = {c: 4 for c in range(n_classes_per_port)}
weights[n_classes_per_port]=0.1

cnt = {node_id: 0 for node_id in ft.nodes()}

def flow_to_classes(f_id, n_id=0):
    return (f_id + n_id ) % n_classes_per_port


cnt_edge=0
cnt_core=0
for node_id in ft.nodes():
    node = ft.nodes[node_id]

    flow_classes = partial(flow_to_classes,
                           n_id=node_id)
    if node['layer']=='edge':
        sketch1 = sketches.edgesketch[cnt_edge]
        sketch2=0
        sketch3=0
        if args.algo=="dleft":
            sketch2 = sketches.insketch[cnt_edge]
            sketch3 = sketches.outsketch[cnt_edge]
        cnt_edge+=1

        if args.algo=="dleft":
            node['device'] = FairPacketSwitch(env,k,pir,buffer_size,weights,'WFQ',flow_classes,
        # node['device'] = FairPacketSwitch(env,k,pir,buffer_size,weights,'DRR',flow_classes,
                                        element_id=node_id,
                                        layer=node['layer'],
                                        ab_fgroup=ab_fgroup,
                                        culprit_switches=culprit_switches,
                                        culprit_flows=culprit_flows,
                                        sketches=sketches,
                                        sketch1=sketch1,
                                        sketch2=sketch2,
                                        sketch3=sketch3,
                                        loop_pair=loop_pair,
                                        culprit_typ=culprit_typ,
                                        n_flows=n_flows,
                                        algo=args.algo,
                                        culprit_time=culprit_time,
                                        use_netseer=use_ns)
        elif args.algo=="sumax" or args.algo=="marple":
            node['device'] = FairPacketSwitch(env,k,pir,buffer_size,weights,'WFQ',flow_classes,
        # node['device'] = FairPacketSwitch(env,k,pir,buffer_size,weights,'DRR',flow_classes,
                                        element_id=node_id,
                                        layer=node['layer'],
                                        ab_fgroup=ab_fgroup,
                                        culprit_switches=culprit_switches,
                                        culprit_flows=culprit_flows,
                                        sketches=sketches,
                                        sketch1=sketch1,
                                        # sketch2=sketch2,
                                        # sketch3=sketch3,
                                        loop_pair=loop_pair,
                                        culprit_typ=culprit_typ,
                                        n_flows=n_flows,
                                        algo=args.algo,
                                        culprit_time=culprit_time,
                                        use_netseer=use_ns)
    elif node['layer']=='aggregation' or node['layer']=='core':
        sketch1 = sketches.coresketch[cnt_core]
        cnt_core+=1
        pd_dict = dict()
        if args.heavy_change != 0:
            for i in ab_flow_list:
                pd_dict[i] = args.heavy_change*all_time

        node['device'] = FairPacketSwitch(env,k,pir,buffer_size,weights,'WFQ',flow_classes,
        # node['device'] = FairPacketSwitch(env,k,pir,buffer_size,weights,'DRR',flow_classes,
                                        element_id=node_id,
                                        layer=node['layer'],
                                        ab_fgroup=ab_fgroup,
                                        culprit_switches=culprit_switches,
                                        culprit_flows=culprit_flows,
                                        sketches=sketches,
                                        sketch1=sketch1,
                                        loop_pair=loop_pair,
                                        culprit_typ=culprit_typ,
                                        n_flows=n_flows,
                                        algo=args.algo,
                                        culprit_time=culprit_time,
                                        packet_drop_num=pd_dict,
                                        use_netseer=use_ns)
    elif node['layer']=='leaf':
        node['device'] = FairPacketSwitch(env,k,pir,buffer_size,weights,'WFQ',flow_classes,
        # node['device'] = FairPacketSwitch(env,k,pir,buffer_size,weights,'DRR',flow_classes,
                                        element_id=node_id,
                                        layer=node['layer'],
                                        ab_fgroup=ab_fgroup,
                                        culprit_switches=culprit_switches,
                                        culprit_flows=culprit_flows,
                                        sketches=sketches,
                                        loop_pair=loop_pair,
                                        culprit_typ=culprit_typ,
                                        n_flows=n_flows,
                                        algo=args.algo,
                                        culprit_time=culprit_time,
                                        use_netseer=use_ns)

    node['device'].demux.fib = node['flow_to_port']
    node['device'].demux.nexthop_to_port = node['nexthop_to_port']

for n in ft.nodes():
    node = ft.nodes[n]
    for port_number, next_hop in node['port_to_nexthop'].items():
        node['device'].ports[port_number].out = ft.nodes[next_hop]['device']
        node['device'].ports[port_number+k].out = ft.nodes[next_hop]['device']


for flow_id, flow in all_flows.items():
    flow.pkt_gen.out = ft.nodes[flow.src]['device']
    ft.nodes[flow.dst]['device'].demux.ends[flow.fid] = flow.pkt_sink

    length = len(flow.path)
    for i in range(1,length-1):
        cnt[flow.path[i]]+=1

for n in ft.nodes():
    print(n,cnt[n],end="; ",file=ff)

check=CheckSwitch(env,ft,ab_fgroup,sketches,all_flows,flow_group_map,sec_time*args.window)
print("start running")
env.run(until=all_time+0.01)

#####################################################################
# if args.test==0:
#     s="../res/"+args.algo+"_"+culprit_name[args.culprit_typ]+".csv"
#     f_res = open(s,"a+")
# elif args.test==1:
#     s="../res_time/"+str(args.error_ratio)+"_"+culprit_name[args.culprit_typ]+".csv"
#     f_res = open(s,"a+")
# elif args.test==2:
#     s="../res_edge/"+str(args.err_flow_ratio)+"_"+culprit_name[args.culprit_typ]+".csv"
#     f_res = open(s,"a+")
# if args.test==0:
#     res_str = fg_typ + "," + str(n_flows) + "," +str(memcost)+","+str(check_prec/check_num)+","+str(check_recall/check_num)+","
# elif args.test==1:
#     res_str = fg_typ + "," + str(n_flows) + "," +str(args.window)+","+str(check_prec/check_num)+","+str(check_recall/check_num)+","
# else:
#     res_str = fg_typ + "," + str(n_flows) + "," +str(memcost)+","+str(edge_prec/edge_num)+","+str(edge_recall/edge_num)+","
#     print(edge_prec/edge_num,edge_recall/edge_num)
# print(res_str,file=f_res)
# print(res_str)
# f_res.close()
######################################################################
ff.close()