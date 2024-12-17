p4 = bfrt.elastic_coco.pipe

inout_table = p4.Ingress.inout_port_index_table
inout_table.clear()
inout_table.add_with_in_index_cal_action(ingress_port=176)
inout_table.add_with_in_index_cal_action(ingress_port=168)
inout_table.add_with_out_index_cal_action(ingress_port=164)
inout_table.add_with_out_index_cal_action(ingress_port=172)

#flow table
src_addr_match = p4.Ingress.src_addr_match
src_addr_match.clear()
src_addr_match.add_with_src_addr_lpm_match(src_addr="111.133.155.0",src_addr_p_length=24,result=1)
src_addr_match.add_with_src_addr_lpm_match(src_addr="122.144.166.0",src_addr_p_length=24,result=2)
src_addr_match.add_with_src_addr_lpm_match(src_addr="133.155.177.0",src_addr_p_length=24,result=3)
src_addr_match.add_with_src_addr_lpm_match(src_addr="144.166.188.0",src_addr_p_length=24,result=4)

dst_addr_match = p4.Ingress.dst_addr_match
dst_addr_match.clear()
dst_addr_match.add_with_dst_addr_lpm_match(dst_addr="111.133.155.0",dst_addr_p_length=24,result=1)
dst_addr_match.add_with_dst_addr_lpm_match(dst_addr="122.144.166.0",dst_addr_p_length=24,result=2)
dst_addr_match.add_with_dst_addr_lpm_match(dst_addr="133.155.177.0",dst_addr_p_length=24,result=3)
dst_addr_match.add_with_dst_addr_lpm_match(dst_addr="144.166.188.0",dst_addr_p_length=24,result=4)

leave_port = p4.Ingress.leave_port
leave_port.clear()
#144ens2-144ens2: 7-3-2-4-7
leave_port.add_with_set_egress_port(src_addr_match_result=1,dst_addr_match_result=1,ingress_port=176,port=164)
leave_port.add_with_set_egress_port(src_addr_match_result=1,dst_addr_match_result=1,ingress_port=172,port=176)
#144ens2-144ens3: 7-3-1-4-7
leave_port.add_with_set_egress_port(src_addr_match_result=1,dst_addr_match_result=2,ingress_port=176,port=164)
leave_port.add_with_set_egress_port(src_addr_match_result=1,dst_addr_match_result=2,ingress_port=172,port=164)
#144ens2-143ens2: 7-3-2-4-8
leave_port.add_with_set_egress_port(src_addr_match_result=1,dst_addr_match_result=3,ingress_port=176,port=164)
#144ens2-143ens3: 7-4-1-3-8
leave_port.add_with_set_egress_port(src_addr_match_result=1,dst_addr_match_result=4,ingress_port=176,port=172)
#144ens3-144ens3: 7-4-2-3-7
leave_port.add_with_set_egress_port(src_addr_match_result=2,dst_addr_match_result=2,ingress_port=168,port=172)
leave_port.add_with_set_egress_port(src_addr_match_result=2,dst_addr_match_result=2,ingress_port=164,port=168)
#144ens3-144ens2: 7-4-1-3-7
leave_port.add_with_set_egress_port(src_addr_match_result=2,dst_addr_match_result=1,ingress_port=168,port=172)
leave_port.add_with_set_egress_port(src_addr_match_result=2,dst_addr_match_result=1,ingress_port=164,port=176)
#144ens3-143ens2: 7-3-1-4-8
leave_port.add_with_set_egress_port(src_addr_match_result=2,dst_addr_match_result=3,ingress_port=168,port=164)
#144ens3-143ens3: 7-4-2-3-8
leave_port.add_with_set_egress_port(src_addr_match_result=2,dst_addr_match_result=4,ingress_port=168,port=172)

#143ens2-144ens2: 8-3-2-4-7
leave_port.add_with_set_egress_port(src_addr_match_result=3,dst_addr_match_result=1,ingress_port=172,port=176)
#143ens2-144ens3: 8-4-1-3-7
leave_port.add_with_set_egress_port(src_addr_match_result=3,dst_addr_match_result=2,ingress_port=164,port=168)
#143ens3-144ens2: 8-3-1-4-7
leave_port.add_with_set_egress_port(src_addr_match_result=4,dst_addr_match_result=1,ingress_port=172,port=176)
#143ens3-144ens3: 8-4-2-3-7
leave_port.add_with_set_egress_port(src_addr_match_result=4,dst_addr_match_result=2,ingress_port=164,port=168)
