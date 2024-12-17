from random import randint, sample
import networkx as nx
from ns.flow.flow import Flow
import random
import datetime

def read_topo(fname):
    ftype = ".graphml"
    if fname.endswith(ftype):
        return nx.read_graphml(fname)
    else:
        print(f"{fname} is not GraphML")

def cal_gp(src,k):

    mu = k*k*5//4
    pod = (src-mu)//(k*k//4)
    lala = k*k//4 + k*pod + k//2 + (src-mu-pod*k*k//4)//(k//2)
    return lala

def cal_src(gp,k):
    gp_id = (((gp-k*k/4)//k)*(k/2)) + (((gp-k*k/4)%k)-(k/2))
    start = gp_id*k/2
    end = gp_id*k/2 + k/2 - 1
    return k*k*5//4 + randint(start,end)

class PathGenerator:
    def __init__(self,G,hosts,k,flow_group_num):
        self.topo=G
        self.hosts=hosts
        self.pathDict = dict()
        self.gp_path_map = dict()
        self.subnet_fg_map = dict()
        self.fg_idx = 0
        self.k = k
        self.group_num = flow_group_num
        # tmp=0
        # for src in hosts:
        #     for dst in hosts:
        #         tmp+=1
        #         print("tmp",tmp)
        #         gp1 = cal_gp(src,int(k))
        #         gp2 = cal_gp(dst,int(k))
        #         if gp1==gp2:
        #             continue
        #         self.pathDict[(src,dst)]=list(nx.all_shortest_paths(G, src, dst))
                # self.pathDict[(src,dst)]=list(nx.all_simple_paths(G, src, dst, cutoff=nx.diameter(G)))
    def generate_fg_with_path(self,path):
        if path in self.pathDict.keys():
            return self.pathDict[path]
        else:
            self.pathDict[path] = self.fg_idx
            self.gp_path_map[self.fg_idx] = path
            self.fg_idx += 1
            return self.pathDict[path]
        
    def generate_fg_with_subnet(self,fid):
        if fid>>72 in self.subnet_fg_map.keys():
            return self.subnet_fg_map[fid>>72]
        else:
            self.subnet_fg_map[fid>>72] = self.fg_idx
            self.fg_idx += 1
            return self.subnet_fg_map[fid>>72]
        
    def generate_flows(self, nflows,k=8,fg_typ="subnet"):
        print("hosts---",self.hosts)
        all_flows = dict()
        flow_group_id = dict()
        flow_group_map = dict()
        fg_sd_map = dict()

        for flow_id in range(nflows):
            # print("flow",flow_id)
            #random.seed(datetime.datetime.now().second)
            while True:

                src, dst = sample(self.hosts, 2)
                if (src-5*k*k//4)//(k*k//4) == (dst-5*k*k//4)//(k*k//4):
                    continue

                gp1 = cal_gp(src,int(k))
                gp2 = cal_gp(dst,int(k))

                if self.group_num != 0 and len(fg_sd_map.keys())==self.group_num:
                    gp_pair = sample(fg_sd_map.keys(),1)[0]
                    gp1,gp2 = gp_pair[0],gp_pair[1]
                    src = cal_src(gp1,int(k))
                    dst = cal_src(gp2,int(k))
                    #print("--gp1,cal src,gp2,cal dst:",gp1,cal_gp(src,int(k)),gp2,cal_gp(dst,int(k)))

                p1 = randint(0,65535)
                p2 = randint(0,65535)
                ptc = randint(0,255)
                fid = (gp1<<92)+(src<<80)+(0<<72)+(gp2<<60)+(dst<<48)+(0<<40)+(p1<<24)+(p2<<8)+ptc
                # fid = (gp1<<88)+(src<<80)+(src<<72)+(gp2<<56)+(dst<<48)+(dst<<40)+(p1<<24)+(p2<<8)+ptc
                all_flows[flow_id] = Flow(fid, src, dst)

                sd_pair = tuple([gp1,gp2])
                
                if sd_pair in fg_sd_map.keys():
                    all_flows[flow_id].path = tuple([src] + list(fg_sd_map[sd_pair][0]) +[dst])
                else:
                    all_flows[flow_id].path = tuple(sample(list(nx.all_shortest_paths(self.topo, src, dst)),1)[0])
                    fg_sd_map[sd_pair] = [all_flows[flow_id].path[1:-1]]
                    
                if fg_typ == "path":
                    all_flows[flow_id].fg_id = self.generate_fg_with_path(all_flows[flow_id].path[1:-1])
                if fg_typ == "subnet":
                    all_flows[flow_id].fg_id = self.generate_fg_with_subnet(fid)
                    
                flow_group_id[all_flows[flow_id].fid] = all_flows[flow_id].fg_id
                
                if all_flows[flow_id].fg_id in flow_group_map.keys():
                    flow_group_map[all_flows[flow_id].fg_id].append(all_flows[flow_id].fid)
                else:
                    flow_group_map[all_flows[flow_id].fg_id] = [all_flows[flow_id].fid]          
                break  
        
        return all_flows, flow_group_id, flow_group_map, self.gp_path_map
            
#    def generate_flows(self, nflows,k=8,fg_typ="subnet"):
#         print("hosts---",self.hosts)
#         all_flows = dict()
#         flow_group_id = dict()
#         flow_group_map = dict()
#         fg_sd_map = dict()
#         gp_list = []
#         # print("dfa")
#         for flow_id in range(nflows):
#             # print("flow",flow_id)
#             #random.seed(datetime.datetime.now().second)
#             while True:
#                 # print("murmur1")
#                 src, dst = sample(self.hosts, 2)
#                 if (src-5*k*k//4)//(k*k//4) == (dst-5*k*k//4)//(k*k//4):
#                     continue
#                 # print("murmur2")
#                 gp1 = cal_gp(src,int(k))
#                 gp2 = cal_gp(dst,int(k))

#                 if gp1==gp2:
#                     # print("again")
#                     continue
#                 # print("murmur3")
#                 p1 = randint(0,65535)
#                 p2 = randint(0,65535)
#                 ptc = randint(0,255)
#                 fid = (gp1<<92)+(src<<80)+(0<<72)+(gp2<<60)+(dst<<48)+(0<<40)+(p1<<24)+(p2<<8)+ptc
#                 # fid = (gp1<<88)+(src<<80)+(src<<72)+(gp2<<56)+(dst<<48)+(dst<<40)+(p1<<24)+(p2<<8)+ptc
#                 all_flows[flow_id] = Flow(fid, src, dst)

#                 sd_pair = tuple([gp1,gp2])
#                 gp_list.append(sd_pair)
                
#                 if self.group_num != 0 and self.fg_idx >= self.group_num and sd_pair in fg_sd_map.keys():
#                     all_flows[flow_id].path = tuple([src] + list(sample(fg_sd_map[sd_pair],1)[0]) +[dst])
#                 else:
#                     all_flows[flow_id].path = tuple(sample(list(nx.all_shortest_paths(self.topo, src, dst)),1)[0])
#                     if sd_pair in fg_sd_map.keys():
#                         fg_sd_map[sd_pair].append(all_flows[flow_id].path[1:-1])
#                     else:
#                         fg_sd_map[sd_pair] = [all_flows[flow_id].path[1:-1]]
                    
#                 if fg_typ == "path":
#                     all_flows[flow_id].fg_id = self.generate_fg_with_path(all_flows[flow_id].path[1:-1])
#                 if fg_typ == "subnet":
#                     all_flows[flow_id].fg_id = self.generate_fg_with_subnet(fid)
                    
#                 flow_group_id[all_flows[flow_id].fid] = all_flows[flow_id].fg_id
                
#                 if all_flows[flow_id].fg_id in flow_group_map.keys():
#                     flow_group_map[all_flows[flow_id].fg_id].append(all_flows[flow_id].fid)
#                 else:
#                     flow_group_map[all_flows[flow_id].fg_id] = [all_flows[flow_id].fid]
#                 # print(all_flows[flow_id].path)
#                 # all_flows[flow_id].path = sample(
#                 #     self.pathDict[(src,dst)],
#                 #     1)[0]
#                 # print("murmur5")                
#                 break  
#         #print("-------host-------\n",self.hosts)
#         #print("-------path-------\n",self.pathDict)
        
#         return all_flows, flow_group_id, flow_group_map, self.gp_path_map

def generate_fib(G, all_flows):
    for n in G.nodes():
        node = G.nodes[n]

        node['port_to_nexthop'] = dict()
        node['nexthop_to_port'] = dict()

        for port, nh in enumerate(nx.neighbors(G, n)):
            node['nexthop_to_port'][nh] = port
            node['port_to_nexthop'][port] = nh

        node['flow_to_port'] = dict()
        node['flow_to_nexthop'] = dict()

    for f in all_flows:
        flow = all_flows[f]
        path = list(zip(flow.path, flow.path[1:]))
        for seg in path:
            a, z = seg
            G.nodes[a]['flow_to_port'][
                flow.fid] = G.nodes[a]['nexthop_to_port'][z]
            G.nodes[a]['flow_to_nexthop'][flow.fid] = z

    return G
