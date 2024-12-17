from random import randint, sample

def cal_gp(src,k):

    mu = k*k*5//4
    pod = (src-mu)//(k*k//4)
    lala = k*k//4 + k*pod + k//2 + (src-mu-pod*k*k//4)//(k//2)
    return lala

def get_err_fg(flow_group,num,path_dict):
    flag = True
    err_fg = []
    while flag:
        err_fg = sample(flow_group, num)
        flag = False
        for fg in err_fg:
            if len(path_dict[fg]) != 5:
                flag = True
    return err_fg

def create_error(flow_group,path_dict,typ,num,k):
    ans=dict()
    ans2=dict()
    mark=dict()
    error_fg = set()
    num_core = k*k//4
    err_fg = get_err_fg(flow_group,num,path_dict)
    cores = range(num_core)
    tmp_ = 0
    if typ==0 or typ==2 or typ==3:
        for fg in err_fg:
                # core_node = randint(0,num_core-1)
                # core_nodes = sample(cores,num_core//4)
                if len(path_dict)>0:
                    path = path_dict[fg]
                    core_nodes = [path[len(path)//2]]
                else:
                    core_nodes = sample(cores,num_core//4)

                ans[fg] = core_nodes
                # ans[gr_host] = [core_node]
                # mark[core_node] = 1
                error_fg.add(fg)
                # break

    elif typ==1:
        for fg in err_fg:
            # core_nodes = sample(cores,num_core//4)
            if len(path_dict)>0:
                path = path_dict[fg]
                core_nodes = [path[len(path)//2]]
            else:
                core_nodes = sample(cores,num_core//4)
                # core_node = randint(0,num_core-1)
                # if core_node in mark.keys():
                    # continue
            ans[fg]=[]
            error_fg.add(fg)
            for core_node in core_nodes:
                if core_node in ans2.keys():
                    ans[fg].extend([core_node,ans2[core_node]])
                else:
                    for pod in range(k):
                        aggr_node = num_core + (core_node // (k // 2)) + (k * pod)
                        if aggr_node in ans2.keys():
                            continue
                        # ans[gr_host] = [core_node,aggr_node]
                        ans[fg].extend([core_node,aggr_node])

                        # mark[aggr_node] = 1
                        ans2[core_node] = aggr_node
                        ans2[aggr_node] = core_node
                        # error_host.add(gr_host)
                        # error_host.add(aggr_node)

                        break

                # break
                
    return error_fg, ans, ans2