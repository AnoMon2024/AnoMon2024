import sys
C_path="../../workplace/C/netseer/"
sys.path.append(C_path)
import Netseer

class CheckNetseer:
    def __init__(self):
        self.netseer = Netseer.Netseer(5,60000)
        self.packet_drop_map = {}
        self.conflict_cnt = 0
    
    def insert(self,packet):
        src_ip = packet.flow_id>>72
        dst_ip = packet.flow_id>>40 & 0xffffffff
        src_port = (packet.flow_id>>24) & 0xffff
        dst_port = (packet.flow_id>>8) & 0xffff
        _proto = packet.flow_id & 0xff

        self.netseer.insert_pre(src_ip,dst_ip,src_port,dst_port,_proto)
        report_list = self.netseer.check_report()
        report_id = (report_list[0]<<72) + (report_list[1]<<40) + (report_list[2]<<24) + (report_list[3]<<8) + (report_list[4])
        report_num = report_list[5]
        if report_id==0 or report_num==0:
            return
        else:
            self.conflict_cnt += 1
        if self.packet_drop_map.get(str(report_id)) != None:
            self.packet_drop_map[str(report_id)] += report_num
        else:
            self.packet_drop_map[str(report_id)] = report_num
        return

    def query_all(self):
        all_drop = self.netseer.query_all()
        if len(all_drop) == 0:
            return self.packet_drop_map

        for i in range(len(all_drop)):
            report_list = all_drop[i]
            report_id = (report_list[0]<<72) + (report_list[1]<<40) + (report_list[2]<<24) + (report_list[3]<<8) + (report_list[4])
            report_num = report_list[5]
            if self.packet_drop_map.get(str(report_id)) != None:
                self.packet_drop_map[str(report_id)] += report_num
            else:
                self.packet_drop_map[str(report_id)] = report_num

        return self.packet_drop_map

