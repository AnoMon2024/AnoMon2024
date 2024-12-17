p4 = bfrt.CellSketch.pipe

#flow table : need to be re-writen according to your topo structure
srcAddr_match = p4.MyIngress.srcAddr_match
srcAddr_match.add_with_srcAddr_lpm_match(srcAddr="111.133.155.0",srcAddr_p_length=24,result=1)
srcAddr_match.add_with_srcAddr_lpm_match(srcAddr="122.144.166.0",srcAddr_p_length=24,result=2)
srcAddr_match.add_with_srcAddr_lpm_match(srcAddr="133.155.177.0",srcAddr_p_length=24,result=3)
srcAddr_match.add_with_srcAddr_lpm_match(srcAddr="144.166.188.0",srcAddr_p_length=24,result=4)

dstAddr_match = p4.MyIngress.dstAddr_match
dstAddr_match.add_with_dstAddr_lpm_match(dstAddr="111.133.155.0",dstAddr_p_length=24,result=1)
dstAddr_match.add_with_dstAddr_lpm_match(dstAddr="122.144.166.0",dstAddr_p_length=24,result=2)
dstAddr_match.add_with_dstAddr_lpm_match(dstAddr="133.155.177.0",dstAddr_p_length=24,result=3)
dstAddr_match.add_with_dstAddr_lpm_match(dstAddr="144.166.188.0",dstAddr_p_length=24,result=4)

leave_port = p4.MyIngress.leave_port
#144ens2-144ens2: 7-3-2-4-7
leave_port.add_with_set_egress_port(srcAddr_match_result=1,dstAddr_match_result=1,port=420)
#144ens2-144ens3: 7-3-1-4-7
leave_port.add_with_set_egress_port(srcAddr_match_result=1,dstAddr_match_result=2,port=432)
#144ens2-143ens2: 7-3-2-4-8
leave_port.add_with_set_egress_port(srcAddr_match_result=1,dstAddr_match_result=3,port=420)
#144ens2-143ens3: 7-4-1-3-8
leave_port.add_with_set_egress_port(srcAddr_match_result=1,dstAddr_match_result=4,port=388)
#144ens3-144ens3: 7-4-2-3-7
leave_port.add_with_set_egress_port(srcAddr_match_result=2,dstAddr_match_result=2,port=400)
#144ens3-144ens2: 7-4-1-3-7
leave_port.add_with_set_egress_port(srcAddr_match_result=2,dstAddr_match_result=1,port=400)
#144ens3-143ens2: 7-3-1-4-8
leave_port.add_with_set_egress_port(srcAddr_match_result=2,dstAddr_match_result=3,port=432)
#144ens3-143ens3: 7-4-2-3-8
leave_port.add_with_set_egress_port(srcAddr_match_result=2,dstAddr_match_result=4,port=388)

#143ens2-143ens2: 8-3-2-4-8
leave_port.add_with_set_egress_port(srcAddr_match_result=3,dstAddr_match_result=3,port=420)
#143ens2-143ens3: 8-3-1-4-8
leave_port.add_with_set_egress_port(srcAddr_match_result=3,dstAddr_match_result=4,port=432)
#143ens2-144ens2: 8-3-2-4-7
leave_port.add_with_set_egress_port(srcAddr_match_result=3,dstAddr_match_result=1,port=420)
#143ens2-144ens3: 8-4-1-3-7
leave_port.add_with_set_egress_port(srcAddr_match_result=3,dstAddr_match_result=2,port=400)
#143ens3-143ens3: 8-4-2-3-8
leave_port.add_with_set_egress_port(srcAddr_match_result=4,dstAddr_match_result=4,port=388)
#143ens3-143ens2: 8-4-1-3-8
leave_port.add_with_set_egress_port(srcAddr_match_result=4,dstAddr_match_result=3,port=388)
#143ens3-144ens2: 8-3-1-4-7
leave_port.add_with_set_egress_port(srcAddr_match_result=4,dstAddr_match_result=1,port=432)
#143ens3-144ens3: 8-4-2-3-7
leave_port.add_with_set_egress_port(srcAddr_match_result=4,dstAddr_match_result=2,port=400)



#range match part : deal with offset related work
range_match_level1 = p4.MyEgress.range_match_level1

range_match_level1.add_with_set_offset(enq_tstamp_start=0,enq_tstamp_end=65536,offset_1=0,offset_2=0)
range_match_level1.add_with_set_offset(enq_tstamp_start=65537,enq_tstamp_end=131072,offset_1=1,offset_2=1)
range_match_level1.add_with_set_offset(enq_tstamp_start=131073,enq_tstamp_end=196608,offset_1=2,offset_2=2)
range_match_level1.add_with_set_offset(enq_tstamp_start=196609,enq_tstamp_end=262143,offset_1=3,offset_2=3)

range_match_level2 = p4.MyEgress.range_match_level2

range_match_level2.add_with_set_offset2(enq_tstamp_start=0,enq_tstamp_end=16384,value1=0)
range_match_level2.add_with_set_offset2(enq_tstamp_start=16385,enq_tstamp_end=32768,value1=1)
range_match_level2.add_with_set_offset2(enq_tstamp_start=32769,enq_tstamp_end=49512,value1=2)
range_match_level2.add_with_set_offset2(enq_tstamp_start=49513,enq_tstamp_end=65536,value1=3)
range_match_level2.add_with_set_offset2(enq_tstamp_start=65537,enq_tstamp_end=81920,value1=0)
range_match_level2.add_with_set_offset2(enq_tstamp_start=81921,enq_tstamp_end=98304,value1=1)
range_match_level2.add_with_set_offset2(enq_tstamp_start=98305,enq_tstamp_end=114688,value1=2)
range_match_level2.add_with_set_offset2(enq_tstamp_start=114689,enq_tstamp_end=131072,value1=3)
range_match_level2.add_with_set_offset2(enq_tstamp_start=131073,enq_tstamp_end=147456,value1=0)
range_match_level2.add_with_set_offset2(enq_tstamp_start=147457,enq_tstamp_end=163840,value1=1)
range_match_level2.add_with_set_offset2(enq_tstamp_start=163841,enq_tstamp_end=180224,value1=2)
range_match_level2.add_with_set_offset2(enq_tstamp_start=180225,enq_tstamp_end=196608,value1=3)
range_match_level2.add_with_set_offset2(enq_tstamp_start=196609,enq_tstamp_end=212992,value1=0)
range_match_level2.add_with_set_offset2(enq_tstamp_start=212993,enq_tstamp_end=229376,value1=1)
range_match_level2.add_with_set_offset2(enq_tstamp_start=229377,enq_tstamp_end=245760,value1=2)
range_match_level2.add_with_set_offset2(enq_tstamp_start=245761,enq_tstamp_end=262143,value1=3)

#shift choose sketch
#sketch1 related
update_bucket1_sketch1 = p4.MyEgress.update_bucket1_sketch1
update_bucket1_sketch1.add_with_write_bucket1_sketch1(reg_set=0)

update_bucket2_sketch1 = p4.MyEgress.update_bucket2_sketch1
update_bucket2_sketch1.add_with_write_bucket2_sketch1(reg_set=0)

update_bucket1_srciptag_sketch1 = p4.MyEgress.update_bucket1_srciptag_sketch1
update_bucket1_srciptag_sketch1.add_with_read_and_compare_bucket1_srciptag_sketch1(reg_set=0)

update_bucket1_dstiptag_sketch1 = p4.MyEgress.update_bucket1_dstiptag_sketch1
update_bucket1_dstiptag_sketch1.add_with_read_and_compare_bucket1_dstiptag_sketch1(reg_set=0)

update_bucket2_srciptag_sketch1 = p4.MyEgress.update_bucket2_srciptag_sketch1
update_bucket2_srciptag_sketch1.add_with_read_and_compare_bucket2_srciptag_sketch1(reg_set=0)

update_bucket2_dstiptag_sketch1 = p4.MyEgress.update_bucket2_dstiptag_sketch1
update_bucket2_dstiptag_sketch1.add_with_read_and_compare_bucket2_dstiptag_sketch1(reg_set=0)

b1_update_cell_part1_sketch1 = p4.MyEgress.b1_update_cell_part1_sketch1
b1_update_cell_part1_sketch1.add_with_b1_write_cell_part1_sketch1(reg_set=0)

b1_update_cell_part2_sketch1 = p4.MyEgress.b1_update_cell_part2_sketch1
b1_update_cell_part2_sketch1.add_with_b1_write_cell_part2_sketch1(reg_set=0)

b2_update_cell_part1_sketch1 = p4.MyEgress.b2_update_cell_part1_sketch1
b2_update_cell_part1_sketch1.add_with_b2_write_cell_part1_sketch1(reg_set=0)

b2_update_cell_part2_sketch1 = p4.MyEgress.b2_update_cell_part2_sketch1
b2_update_cell_part2_sketch1.add_with_b2_write_cell_part2_sketch1(reg_set=0)

record_b1_to_cell_part1_index_sketch1 = p4.MyEgress.record_b1_to_cell_part1_index_sketch1
record_b1_to_cell_part1_index_sketch1.add_with_write_b1_to_cell_part1_sketch1(reg_set=0)

record_b1_to_cell_part2_index_sketch1 = p4.MyEgress.record_b1_to_cell_part2_index_sketch1
record_b1_to_cell_part2_index_sketch1.add_with_write_b1_to_cell_part2_sketch1(reg_set=0)

record_b2_to_cell_part1_index_sketch1 = p4.MyEgress.record_b2_to_cell_part1_index_sketch1
record_b2_to_cell_part1_index_sketch1.add_with_write_b2_to_cell_part1_sketch1(reg_set=0)

record_b2_to_cell_part2_index_sketch1 = p4.MyEgress.record_b2_to_cell_part2_index_sketch1
record_b2_to_cell_part2_index_sketch1.add_with_write_b2_to_cell_part2_sketch1(reg_set=0)

#sketch2 related
update_bucket1_sketch2 = p4.MyEgress.update_bucket1_sketch2
update_bucket1_sketch2.add_with_write_bucket1_sketch2(reg_set=1)

update_bucket2_sketch2 = p4.MyEgress.update_bucket2_sketch2
update_bucket2_sketch2.add_with_write_bucket2_sketch2(reg_set=1)

update_bucket1_srciptag_sketch2 = p4.MyEgress.update_bucket1_srciptag_sketch2
update_bucket1_srciptag_sketch2.add_with_read_and_compare_bucket1_srciptag_sketch2(reg_set=1)

update_bucket1_dstiptag_sketch2 = p4.MyEgress.update_bucket1_dstiptag_sketch2
update_bucket1_dstiptag_sketch2.add_with_read_and_compare_bucket1_dstiptag_sketch2(reg_set=1)

update_bucket2_srciptag_sketch2 = p4.MyEgress.update_bucket2_srciptag_sketch2
update_bucket2_srciptag_sketch2.add_with_read_and_compare_bucket2_srciptag_sketch2(reg_set=1)

update_bucket2_dstiptag_sketch2 = p4.MyEgress.update_bucket2_dstiptag_sketch2
update_bucket2_dstiptag_sketch2.add_with_read_and_compare_bucket2_dstiptag_sketch2(reg_set=1)

b1_update_cell_part1_sketch2 = p4.MyEgress.b1_update_cell_part1_sketch2
b1_update_cell_part1_sketch2.add_with_b1_write_cell_part1_sketch2(reg_set=1)

b1_update_cell_part2_sketch2 = p4.MyEgress.b1_update_cell_part2_sketch2
b1_update_cell_part2_sketch2.add_with_b1_write_cell_part2_sketch2(reg_set=1)

b2_update_cell_part1_sketch2 = p4.MyEgress.b2_update_cell_part1_sketch2
b2_update_cell_part1_sketch2.add_with_b2_write_cell_part1_sketch2(reg_set=1)

b2_update_cell_part2_sketch2 = p4.MyEgress.b2_update_cell_part2_sketch2
b2_update_cell_part2_sketch2.add_with_b2_write_cell_part2_sketch2(reg_set=1)

record_b1_to_cell_part1_index_sketch2 = p4.MyEgress.record_b1_to_cell_part1_index_sketch2
record_b1_to_cell_part1_index_sketch2.add_with_write_b1_to_cell_part1_sketch2(reg_set=1)

record_b1_to_cell_part2_index_sketch2 = p4.MyEgress.record_b1_to_cell_part2_index_sketch2
record_b1_to_cell_part2_index_sketch2.add_with_write_b1_to_cell_part2_sketch2(reg_set=1)

record_b2_to_cell_part1_index_sketch2 = p4.MyEgress.record_b2_to_cell_part1_index_sketch2
record_b2_to_cell_part1_index_sketch2.add_with_write_b2_to_cell_part1_sketch2(reg_set=1)

record_b2_to_cell_part2_index_sketch2 = p4.MyEgress.record_b2_to_cell_part2_index_sketch2
record_b2_to_cell_part2_index_sketch2.add_with_write_b2_to_cell_part2_sketch2(reg_set=1)