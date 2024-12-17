/*  base : 
    core switch measurement logic
    */
#include <core.p4>
#if __TARGET_TOFINO__ == 2
#include <t2na.p4>
#else
#include <tna.p4>
#endif

//*p4 ----- 16*//
//register num 
#define MAX_BUCKET_REGISTER_ENTRIES 4096
#define MAX_BUCKET_TAG_ENTRIES 1024
#define MAX_CELL_BUCKET_ENTRIES 4096
#define INDEX_HIGHEST 11 //index_length - 1
#define INDEX 12
#define INDEX_HASH_PART 10
#define CELL_INDEX_HIGHEST 11 //cell_index_length - 1
#define CELL 12
#define CELL_HASH_PART 10
//used for test
#define BASE_NUM 1
#define MAX_RECORD_NUM 2000
#define MAX_TIME_INTERVAL 262143 //2^18 max value of dequeue_timedelta
#define MIN_TIME_INTERVAL 0
//Threshold for splitting bucket into cell
#define THRESHOLD 0

const bit<16> TYPE_IPV4 = 0x0800;
const bit<16> TYPE_ARP = 0x0806;
const bit<8> TYPE_TCP = 0x06;//tcp = 6
const bit<8> TYPE_UDP = 0x11;//udp = 17

typedef bit<9>  egressSpec_t;
typedef bit<48> macAddr_t;	
typedef bit<32> ip4Addr_t;	
typedef bit<INDEX> index;
typedef bit<INDEX_HASH_PART> index_hash_part;
typedef bit<CELL> cell_index;
typedef bit<CELL_HASH_PART> cell_hash_part;
typedef bit<1> sketch_switcher;

//ethernet header
header ethernet_t {  
    macAddr_t dstAddr;
    macAddr_t srcAddr;
    bit<16>   etherType;	
}

//ipv4 header
header ipv4_t {   
    bit<4>    version; 
    bit<4>    ihl;      
    bit<8>    diffserv; 
    bit<16>   totalLen;
    bit<16>   identification; 
    bit<3>    flags;   
    bit<13>   fragOffset;  
    bit<8>    ttl;   
    bit<8>    protocol;  
    bit<16>   hdrChecksum; 
    ip4Addr_t srcAddr; 
    ip4Addr_t dstAddr;	
}

//arp header
header arp_h {
    bit<16> ar_hrd;
    bit<16> ar_pro;
    bit<8>  ar_hln;
    bit<8>  ar_pln;
    bit<16> ar_op;
    bit<48> src_mac;
    bit<32> src_ip;
    bit<48> dst_mac;
    bit<32> dst_ip;
}

//tcp header
header tcp_t{  
    bit<16> srcPort;  
    bit<16> dstPort;  
    bit<32> seqNo;    
    bit<32> ackNo;    
    bit<4>  dataOffset; 
    bit<4>  res;  
    bit<1>  cwr;  
    bit<1>  ece;  
    bit<1>  urg;  
    bit<1>  ack; 
    bit<1>  psh;  
    bit<1>  rst;  
    bit<1>  syn;  
    bit<1>  fin;  
    bit<16> window; 
    bit<16> checksum;  
    bit<16> urgentPtr; 
}

//udp header
header udp_t{
    bit<16> srcPort; 	
    bit<16> dstPort;	
    bit<16> length_;	
    bit<16> checksum;
}

//empty header
struct empty_header_t {}

struct headers {            
    ethernet_t  ethernet;
    ipv4_t      ipv4;
    arp_h       arp;
    tcp_t       tcp;
    udp_t       udp;
}
struct ingress_metadata{
    bit<8> srcAddr_match_result;
    bit<8> dstAddr_match_result;
}

struct egress_metadata {
    //bucket register index
    index bucket1_index;
    index bucket2_index;
    sketch_switcher reg_set;
    //bucket register index's offset part
    bit<2> offset1;
    bit<2> offset2;
    bit<1> bucket1_compare_dst;
    bit<1> bucket1_compare_src;
    bit<1> bucket2_compare_dst;
    bit<1> bucket2_compare_src;
    bit<1> divide_flag1;
    bit<1> divide_flag2;
    bit<2> cell_offset;
    cell_index cell_index_part1;
    cell_index cell_index_part2;
}

//empty MyIngressParser
parser MyIngressParser(
    packet_in packet,
    out headers hdr,
    out ingress_metadata meta,
    out ingress_intrinsic_metadata_t ig_intr_md
                ) {
    //parse 
    //extract information of packet
    state start {
        packet.extract(ig_intr_md);
        //port metadata related
        packet.advance(PORT_METADATA_SIZE);
        transition parse_ethernet;
    }

    state parse_ethernet {
        packet.extract(hdr.ethernet); 
        transition select (hdr.ethernet.etherType) { 
            TYPE_IPV4: parse_ipv4;  
            TYPE_ARP: parse_arp;  
            default: accept;   
        }
    }
    
   state parse_ipv4 {
        packet.extract(hdr.ipv4);   
        transition select (hdr.ipv4.protocol) { 
            TYPE_TCP: parse_tcp;   
            TYPE_UDP: parse_udp;
            default: accept; 
		}
    }

    state parse_arp {
        packet.extract(hdr.arp);   
        transition accept;
    }
    state parse_tcp {    
        packet.extract(hdr.tcp);  
        transition accept;
    }
    state parse_udp {
        packet.extract(hdr.udp);
        transition accept;
    }
}

//empty MyIngress
control MyIngress(
    inout headers hdr,
    inout ingress_metadata meta,
    in ingress_intrinsic_metadata_t ig_intr_md,
    in ingress_intrinsic_metadata_from_parser_t ig_intr_prsr_md,
    inout ingress_intrinsic_metadata_for_deparser_t ig_intr_dprsr_md,
    inout ingress_intrinsic_metadata_for_tm_t ig_intr_tm_md
    ) {
    //srcAddr lpm match
    action srcAddr_lpm_match(bit<8> result) {
        meta.srcAddr_match_result = result;
    }
    table srcAddr_match {
        key = {
            hdr.ipv4.srcAddr : lpm;
        }
        actions = {srcAddr_lpm_match;}
        size = 100;
    }
    //dstAddr lpm match
    action dstAddr_lpm_match(bit<8> result) {
        meta.dstAddr_match_result = result;
    }
    table dstAddr_match {
        key = {
            hdr.ipv4.dstAddr : lpm;
        }
        actions = {dstAddr_lpm_match;}
        size = 100;
    }
    //port match 
    action set_egress_port(bit<9> port) {
        ig_intr_tm_md.ucast_egress_port = port;
    }
    table leave_port {
        key = {
            meta.srcAddr_match_result : exact;
            meta.dstAddr_match_result : exact;
        }
        actions = {set_egress_port;}
        size = 100;
    }
    apply {
        //forward to appropriate egress device_port
        srcAddr_match.apply();
        dstAddr_match.apply();
        leave_port.apply();
        //don't bypass egress
        ig_intr_tm_md.bypass_egress = 1w0;
    }
}

//empty MyIngress deparser
control MyIngressDeparser(
        packet_out pkt,
        inout headers hdr,
        in ingress_metadata meta,
        in ingress_intrinsic_metadata_for_deparser_t ig_intr_dprsr_md) {

    apply {
        //didn't modify header,only emit totally
        pkt.emit(hdr);
    }
}

parser MyEgressParser(
        packet_in packet,
        out headers hdr,
        out egress_metadata meta,
        out egress_intrinsic_metadata_t eg_intr_md) {
    //mainly logic is in egress 
    //extract egress standard metadata information of packet
    state start {
        packet.extract(eg_intr_md);
        transition parse_ethernet;
    }
    state parse_ethernet {
        packet.extract(hdr.ethernet); 
        transition select (hdr.ethernet.etherType) { 
            TYPE_IPV4: parse_ipv4;  
            TYPE_ARP: parse_arp;  
            default: accept;   
        }
    }
    
   state parse_ipv4 {
        packet.extract(hdr.ipv4);   
        transition select (hdr.ipv4.protocol) { 
            TYPE_TCP: parse_tcp;   
            TYPE_UDP: parse_udp;
            default: accept; 
		}
    }

    state parse_arp {
        packet.extract(hdr.arp);   
        transition accept;
    }
    state parse_tcp {    
        packet.extract(hdr.tcp);  
        transition accept;
    }
    state parse_udp {
        packet.extract(hdr.udp);
        transition accept;
    }
}

control MyEgressDeparser(
        packet_out pkt,
        inout headers hdr,
        in egress_metadata eg_md,
        in egress_intrinsic_metadata_for_deparser_t ig_intr_dprs_md) {
    apply {
        pkt.emit(hdr);
    }
}

control MyEgress(
        inout headers hdr,
        inout egress_metadata meta,
        in egress_intrinsic_metadata_t eg_intr_md,
        in egress_intrinsic_metadata_from_parser_t eg_intr_md_from_prsr,
        inout egress_intrinsic_metadata_for_deparser_t eg_intr_dprs_md,
        inout egress_intrinsic_metadata_for_output_port_t eg_intr_oport_md) {
    /*logic: 
    packet in -> hash flow key and get bucket1 index -> judge whether bucket1 is empty or not 
        empty -> fill bucket1 tag register and update bucket1 value     
        not empty -> judge whether bucket1's recorded flow keys match current packet's flow key or not
            match -> update bucket1 value and judge whether bucket1 value exceed threshold
                exceed -> hash bucket1 index and flow key to get cell part1/part2 index + record hash mapping relation + update cell register
            not match -> hash bucket2 index -> judge judge whether bucket2 is empty or not and repeat the previous logic
    */
    action get_reg_set(){
        meta.reg_set = hdr.ipv4.flags[1:1];
    }
    table choose_sketch {
        actions = {get_reg_set;}
        const default_action = get_reg_set();
        size = 10;
    }
    /* *******
     dleft alogirthm table/action and regsiter 
    ****** */
    Hash<index_hash_part>(HashAlgorithm_t.CRC16) hash_bucket1;
    Hash<index_hash_part>(HashAlgorithm_t.CRC32) hash_bucket2;
    //bucket index hash function
    //bucket1 index table
    action get_bucket1_index_hash_part() {
        meta.bucket1_index[INDEX_HIGHEST:2] = hash_bucket1.get(
			{hdr.ipv4.srcAddr, hdr.ipv4.dstAddr, hdr.ipv4.protocol});
    }
    table bucket1_index_hash_part {
        actions  = {get_bucket1_index_hash_part;}
        const default_action = get_bucket1_index_hash_part();
        size = 1;
    }
    //bucket2 index table
    action get_bucket2_index_hash_part() {
        meta.bucket2_index[INDEX_HIGHEST:2] = hash_bucket2.get(
			{hdr.ipv4.srcAddr, hdr.ipv4.dstAddr, hdr.ipv4.protocol});
    }
    table bucket2_index_hash_part {
        actions  = {get_bucket2_index_hash_part;}
        const default_action = get_bucket2_index_hash_part();
        size = 1;
    }
    //bucket 1 part : 2 sketches in total , switch between two registers 
    Register<bit<32>,bit<32>>(MAX_BUCKET_REGISTER_ENTRIES,0) bucket1_sketch1;
	//bucket1: record
	RegisterAction<bit<32>,bit<32>,bit<1>>(bucket1_sketch1) bucket1_sketch1_read = {
        void apply(inout bit<32> input_value,out bit<1> output_value){
            input_value = input_value + 1;
            if(input_value >= THRESHOLD)
            {
                output_value = 1w1;
            }
            else
            {
                output_value = 1w0;
            }
        }
    };
    Register<bit<32>,bit<32>>(MAX_BUCKET_REGISTER_ENTRIES,0) bucket1_sketch2;
	//bucket1: record
	RegisterAction<bit<32>,bit<32>,bit<1>>(bucket1_sketch2) bucket1_sketch2_read = {
        void apply(inout bit<32> input_value,out bit<1> output_value){
            input_value = input_value + 1;
            if(input_value >= THRESHOLD)
            {
                output_value = 1w1;
            }
            else
            {
                output_value = 1w0;
            }
        }
    };
    Register<bit<32>,bit<32>>(MAX_BUCKET_TAG_ENTRIES,0) bucket1_srciptag_sketch1;
	//bucket1: record
	RegisterAction<bit<32>,bit<32>,bit<1>>(bucket1_srciptag_sketch1) bucket1_srciptag_sketch1_read = {
        void apply(inout bit<32> input_value,out bit<1> output_value){
            if(input_value == 32w0 || input_value == hdr.ipv4.srcAddr)
            {
                input_value = hdr.ipv4.srcAddr;
                output_value = 0;
            }
            else
            {
                output_value = 1;
            }
        }
    };
    Register<bit<32>,bit<32>>(MAX_BUCKET_TAG_ENTRIES,0) bucket1_srciptag_sketch2;
	//bucket1: record
	RegisterAction<bit<32>,bit<32>,bit<1>>(bucket1_srciptag_sketch2) bucket1_srciptag_sketch2_read = {
        void apply(inout bit<32> input_value,out bit<1> output_value){
            if(input_value == 32w0 || input_value == hdr.ipv4.srcAddr)
            {
                input_value = hdr.ipv4.srcAddr;
                output_value = 0;
            }
            else
            {
                output_value = 1;
            }
        }
    };
    Register<bit<32>,bit<32>>(MAX_BUCKET_TAG_ENTRIES,0) bucket1_dstiptag_sketch1;
	//bucket1: record
	RegisterAction<bit<32>,bit<32>,bit<1>>(bucket1_dstiptag_sketch1) bucket1_dstiptag_sketch1_read = {
        void apply(inout bit<32> input_value,out bit<1> output_value){
            if(input_value == 32w0 || input_value == hdr.ipv4.dstAddr)
            {
                input_value = hdr.ipv4.dstAddr;
                output_value = 0;
            }
            else
            {
                output_value = 1;
            }
        }
    };
    Register<bit<32>,bit<32>>(MAX_BUCKET_TAG_ENTRIES,0) bucket1_dstiptag_sketch2;
	//bucket1: record
	RegisterAction<bit<32>,bit<32>,bit<1>>(bucket1_dstiptag_sketch2) bucket1_dstiptag_sketch2_read = {
        void apply(inout bit<32> input_value,out bit<1> output_value){
            if(input_value == 32w0 || input_value == hdr.ipv4.dstAddr)
            {
                input_value = hdr.ipv4.dstAddr;
                output_value = 0;
            }
            else
            {
                output_value = 1;
            }
        }
    };
    //bucket 2 part
    Register<bit<32>,bit<32>>(MAX_BUCKET_REGISTER_ENTRIES,0) bucket2_sketch1;
	//bucket2: record
	RegisterAction<bit<32>,bit<32>,bit<1>>(bucket2_sketch1) bucket2_sketch1_read = {
        void apply(inout bit<32> input_value,out bit<1> output_value){
            input_value = input_value + 1;
            if(input_value >= THRESHOLD)
            {
                output_value = 1w1;
            }
            else
            {
                output_value = 1w0;
            }
        }
    };
    Register<bit<32>,bit<32>>(MAX_BUCKET_REGISTER_ENTRIES,0) bucket2_sketch2;
	//bucket2: record
	RegisterAction<bit<32>,bit<32>,bit<1>>(bucket2_sketch2) bucket2_sketch2_read = {
        void apply(inout bit<32> input_value,out bit<1> output_value){
            input_value = input_value + 1;
            if(input_value >= THRESHOLD)
            {
                output_value = 1w1;
            }
            else
            {
                output_value = 1w0;
            }
        }
    };
    Register<bit<32>,bit<32>>(MAX_BUCKET_TAG_ENTRIES,0) bucket2_srciptag_sketch1;
	//bucket2: record
	RegisterAction<bit<32>,bit<32>,bit<1>>(bucket2_srciptag_sketch1) bucket2_srciptag_sketch1_read = {
        void apply(inout bit<32> input_value,out bit<1> output_value){
            if(input_value == 32w0 || input_value == hdr.ipv4.srcAddr)
            {
                input_value = hdr.ipv4.srcAddr;
                output_value = 0;
            }
            else
            {
                output_value = 1;
            }
        }
    };
    Register<bit<32>,bit<32>>(MAX_BUCKET_TAG_ENTRIES,0) bucket2_srciptag_sketch2;
	//bucket2: record
	RegisterAction<bit<32>,bit<32>,bit<1>>(bucket2_srciptag_sketch2) bucket2_srciptag_sketch2_read = {
        void apply(inout bit<32> input_value,out bit<1> output_value){
            if(input_value == 32w0 || input_value == hdr.ipv4.srcAddr)
            {
                input_value = hdr.ipv4.srcAddr;
                output_value = 0;
            }
            else
            {
                output_value = 1;
            }
        }
    };
    Register<bit<32>,bit<32>>(MAX_BUCKET_TAG_ENTRIES,0) bucket2_dstiptag_sketch1;
	//bucket2: record
	RegisterAction<bit<32>,bit<32>,bit<1>>(bucket2_dstiptag_sketch1) bucket2_dstiptag_sketch1_read = {
        void apply(inout bit<32> input_value,out bit<1> output_value){
            if(input_value == 32w0 || input_value == hdr.ipv4.dstAddr)
            {
                input_value = hdr.ipv4.dstAddr;
                output_value = 0;
            }
            else
            {
                output_value = 1;
            }
        }
    };
    Register<bit<32>,bit<32>>(MAX_BUCKET_TAG_ENTRIES,0) bucket2_dstiptag_sketch2;
	//bucket2: record
	RegisterAction<bit<32>,bit<32>,bit<1>>(bucket2_dstiptag_sketch2) bucket2_dstiptag_sketch2_read = {
        void apply(inout bit<32> input_value,out bit<1> output_value){
            if(input_value == 32w0 || input_value == hdr.ipv4.dstAddr)
            {
                input_value = hdr.ipv4.dstAddr;
                output_value = 0;
            }
            else
            {
                output_value = 1;
            }
        }
    };
    //delay offset table
    action set_offset(bit<2> offset_1,bit<2> offset_2)
    {
        meta.offset1 = offset_1;
        meta.offset2 = offset_2;
    }
    table range_match_level1 {
        key = {
            eg_intr_md.enq_tstamp : range;
        }
        actions = {
            set_offset;
        }
        const default_action = set_offset(3,3);
        size = 100;
    }
    //complete index
    action get_bucket1_index_offset_part()
    {
        meta.bucket1_index[1:0] = meta.offset1;
    }
    table complete_bucket1_index{
        actions = {get_bucket1_index_offset_part;}
        const default_action = get_bucket1_index_offset_part();
        size = 1;
    }
    action get_bucket2_index_offset_part()
    {
        meta.bucket2_index[1:0] = meta.offset2;
    }
    table complete_bucket2_index{
        actions = {get_bucket2_index_offset_part;}
        const default_action = get_bucket2_index_offset_part();
        size = 1;
    }
    //tag register 
    //bucket1 
    action read_and_compare_bucket1_dstiptag_sketch1() {
        meta.bucket1_compare_dst = bucket1_dstiptag_sketch1_read.execute((bit<32>)meta.bucket1_index[INDEX_HIGHEST:2]);
    }
    action read_and_compare_bucket1_dstiptag_sketch2() {
        meta.bucket1_compare_dst = bucket1_dstiptag_sketch2_read.execute((bit<32>)meta.bucket1_index[INDEX_HIGHEST:2]);
    }
    table update_bucket1_dstiptag_sketch1 {
        key = {meta.reg_set : exact;}
        actions = {
            read_and_compare_bucket1_dstiptag_sketch1;}
        size = 2;
    }
    table update_bucket1_dstiptag_sketch2 {
        key = {meta.reg_set : exact;}
        actions = {
            read_and_compare_bucket1_dstiptag_sketch2;}
        size = 2;
    }
    action read_and_compare_bucket1_srciptag_sketch1() {
        meta.bucket1_compare_src = bucket1_srciptag_sketch1_read.execute((bit<32>)meta.bucket1_index[INDEX_HIGHEST:2]);
    }
    action read_and_compare_bucket1_srciptag_sketch2() {
        meta.bucket1_compare_src = bucket1_srciptag_sketch2_read.execute((bit<32>)meta.bucket1_index[INDEX_HIGHEST:2]);
    }
    table update_bucket1_srciptag_sketch1 {
        key = {meta.reg_set : exact;}
        actions = {
            read_and_compare_bucket1_srciptag_sketch1;}
        size = 2;
    }
    table update_bucket1_srciptag_sketch2 {
        key = {meta.reg_set : exact;}
        actions = {
            read_and_compare_bucket1_srciptag_sketch2;}
        size = 2;
    }
    //bucket2
    action read_and_compare_bucket2_dstiptag_sketch1() {
        meta.bucket2_compare_dst = bucket2_dstiptag_sketch1_read.execute((bit<32>)meta.bucket2_index[INDEX_HIGHEST:2]);
    }
    action read_and_compare_bucket2_dstiptag_sketch2() {
        meta.bucket2_compare_dst = bucket2_dstiptag_sketch2_read.execute((bit<32>)meta.bucket2_index[INDEX_HIGHEST:2]);
    }
    table update_bucket2_dstiptag_sketch1 {
        key = {meta.reg_set : exact;}
        actions = {
            read_and_compare_bucket2_dstiptag_sketch1;}
        size = 1;
    }
    table update_bucket2_dstiptag_sketch2 {
        key = {meta.reg_set : exact;}
        actions = {
            read_and_compare_bucket2_dstiptag_sketch2;}
        size = 1;
    }
    action read_and_compare_bucket2_srciptag_sketch1() {
        meta.bucket2_compare_src = bucket2_srciptag_sketch1_read.execute((bit<32>)meta.bucket2_index[INDEX_HIGHEST:2]);
    }
    action read_and_compare_bucket2_srciptag_sketch2() {
        meta.bucket2_compare_src = bucket2_srciptag_sketch2_read.execute((bit<32>)meta.bucket2_index[INDEX_HIGHEST:2]);
    }
    table update_bucket2_srciptag_sketch1 {
        key = {meta.reg_set : exact;}
        actions = {
            read_and_compare_bucket2_srciptag_sketch1;}
        size = 1;
    }
    table update_bucket2_srciptag_sketch2 {
        key = {meta.reg_set : exact;}
        actions = {
            read_and_compare_bucket2_srciptag_sketch2;}
        size = 1;
    }
    //bucket register update
    //bucket1 
    action write_bucket1_sketch1() {
       meta.divide_flag1 =  bucket1_sketch1_read.execute((bit<32>)meta.bucket1_index);
    }
    action write_bucket1_sketch2() {
       meta.divide_flag1 =  bucket1_sketch2_read.execute((bit<32>)meta.bucket1_index);
    }
    table update_bucket1_sketch1{
        key = {meta.reg_set : exact;}
        actions = {
            write_bucket1_sketch1;}
        size = 2;
    }
    table update_bucket1_sketch2{
        key = {meta.reg_set : exact;}
        actions = {
            write_bucket1_sketch2;}
        size = 2;
    }
    //bucket2
    action write_bucket2_sketch1() {
        meta.divide_flag2 = bucket2_sketch1_read.execute((bit<32>)meta.bucket2_index);
    }
    action write_bucket2_sketch2() {
        meta.divide_flag2 = bucket2_sketch2_read.execute((bit<32>)meta.bucket2_index);
    }
    table update_bucket2_sketch1{
        key = {meta.reg_set : exact;}
        actions = {
            write_bucket2_sketch1;}
        size = 2;
    }
    table update_bucket2_sketch2{
        key = {meta.reg_set : exact;}
        actions = {
            write_bucket2_sketch2;}
        size = 2;
    }
    /* *******
     cell division alogrithm table/action and register
    *******/
    /* after dleft , also need a cell division alogrithm
    dleft : deq_timedelta ->               [] [] [] []
                                           /\
    cell division : deq_timedelta ->     [] [] [] []
    */
    //cell hash function
    Hash<cell_hash_part>(HashAlgorithm_t.CRC16) b1_hash_cell1;
    Hash<cell_hash_part>(HashAlgorithm_t.CRC32) b1_hash_cell2;
    Hash<cell_hash_part>(HashAlgorithm_t.CRC16) b2_hash_cell1;
    Hash<cell_hash_part>(HashAlgorithm_t.CRC32) b2_hash_cell2;
    //Hash part : dleft in bucket1 , hash unit : bucket1_index
    action b1_hash_cell_index_part1() {
        meta.cell_index_part1[CELL_INDEX_HIGHEST:2] = b1_hash_cell1.get({
            hdr.ipv4.srcAddr,hdr.ipv4.dstAddr,meta.bucket1_index
        });
    }
    table b1_get_cell_hash_part1 {
        actions = {b1_hash_cell_index_part1;}
        const default_action = b1_hash_cell_index_part1();
        size = 10;
    }
    action b1_hash_cell_index_part2() {
        meta.cell_index_part2[CELL_INDEX_HIGHEST:2] = b1_hash_cell2.get({
            hdr.ipv4.srcAddr,hdr.ipv4.dstAddr,meta.bucket1_index
        });
    }
    table b1_get_cell_hash_part2 {
        actions = {b1_hash_cell_index_part2;}
        const default_action = b1_hash_cell_index_part2();
        size = 10;
    }
    //Hash part : dleft in bucket2 , hash unit : bucket2_index
    action b2_hash_cell_index_part1() {
        meta.cell_index_part1[CELL_INDEX_HIGHEST:2] = b2_hash_cell1.get({
            hdr.ipv4.srcAddr,hdr.ipv4.dstAddr,meta.bucket2_index
        });
    }
    table b2_get_cell_hash_part1 {
        actions = {b2_hash_cell_index_part1;}
        const default_action = b2_hash_cell_index_part1();
        size = 10;
    }
    action b2_hash_cell_index_part2() {
        meta.cell_index_part2[CELL_INDEX_HIGHEST:2] = b2_hash_cell2.get({
            hdr.ipv4.srcAddr,hdr.ipv4.dstAddr,meta.bucket2_index
        });
    }
    table b2_get_cell_hash_part2 {
        actions = {b2_hash_cell_index_part2;}
        const default_action = b2_hash_cell_index_part2();
        size = 10;
    }
    //complete cell index offset part
    //dleft in bucket1 
    action b1_offset_cell_index_part1() {
        meta.cell_index_part1[1:0] = meta.cell_offset;
    }
    table b1_complete_cell_part1 {
        actions = {b1_offset_cell_index_part1;}
        const default_action = b1_offset_cell_index_part1();
        size = 10;
    }
    action b1_offset_cell_index_part2() {
        meta.cell_index_part2[1:0] = meta.cell_offset;
    }
    table b1_complete_cell_part2 {
        actions = {b1_offset_cell_index_part2;}
        const default_action = b1_offset_cell_index_part2();
        size = 10;
    }
    //dleft in bucket2
    action b2_offset_cell_index_part1() {
        meta.cell_index_part1[1:0] = meta.cell_offset;
    }
    table b2_complete_cell_part1 {
        actions = {b2_offset_cell_index_part1;}
        const default_action = b2_offset_cell_index_part1();
        size = 10;
    }
    action b2_offset_cell_index_part2() {
        meta.cell_index_part2[1:0] = meta.cell_offset;
    }
    table b2_complete_cell_part2 {
        actions = {b2_offset_cell_index_part2;}
        const default_action = b2_offset_cell_index_part2();
        size = 10;
    }
    //cell register
    Register<bit<32>,bit<32>>(MAX_CELL_BUCKET_ENTRIES,0) cell_part1_sketch1;
	RegisterAction<bit<32>,bit<32>,bit<32>>(cell_part1_sketch1) cell_part1_sketch1_read = {
        void apply(inout bit<32> input_value,out bit<32> output_value){
            input_value = input_value + 1;
            output_value = 1;
        }
    };
    Register<bit<32>,bit<32>>(MAX_CELL_BUCKET_ENTRIES,0) cell_part1_sketch2;
	RegisterAction<bit<32>,bit<32>,bit<32>>(cell_part1_sketch2) cell_part1_sketch2_read = {
        void apply(inout bit<32> input_value,out bit<32> output_value){
            input_value = input_value + 1;
            output_value = 1;
        }
    };
    Register<bit<32>,bit<32>>(MAX_CELL_BUCKET_ENTRIES,0) cell_part2_sketch1;
	RegisterAction<bit<32>,bit<32>,bit<32>>(cell_part2_sketch1) cell_part2_sketch1_read = {
        void apply(inout bit<32> input_value,out bit<32> output_value){
            input_value = input_value + 1;
            output_value = 1;
        }
    };
    Register<bit<32>,bit<32>>(MAX_CELL_BUCKET_ENTRIES,0) cell_part2_sketch2;
	RegisterAction<bit<32>,bit<32>,bit<32>>(cell_part2_sketch2) cell_part2_sketch2_read = {
        void apply(inout bit<32> input_value,out bit<32> output_value){
            input_value = input_value + 1;
            output_value = 1;
        }
    };
    //import register : record func : bucket_index(with offset) -> cell_index(without offset)
    Register<bit<16>,bit<32>>(MAX_BUCKET_REGISTER_ENTRIES,0) bucket1_to_cell_part1_sketch1;
	RegisterAction<bit<16>,bit<32>,bit<16>>(bucket1_to_cell_part1_sketch1) bucket1_to_cell_part1_sketch1_read = {
        void apply(inout bit<16> input_value,out bit<16> output_value){
            input_value = (bit<16>)meta.cell_index_part1[CELL_INDEX_HIGHEST:2];
        }
    };
    Register<bit<16>,bit<32>>(MAX_BUCKET_REGISTER_ENTRIES,0) bucket1_to_cell_part1_sketch2;
	RegisterAction<bit<16>,bit<32>,bit<16>>(bucket1_to_cell_part1_sketch2) bucket1_to_cell_part1_sketch2_read = {
        void apply(inout bit<16> input_value,out bit<16> output_value){
            input_value = (bit<16>)meta.cell_index_part1[CELL_INDEX_HIGHEST:2];
        }
    };
    Register<bit<16>,bit<32>>(MAX_BUCKET_REGISTER_ENTRIES,0) bucket1_to_cell_part2_sketch1;
	RegisterAction<bit<16>,bit<32>,bit<16>>(bucket1_to_cell_part2_sketch1) bucket1_to_cell_part2_sketch1_read = {
        void apply(inout bit<16> input_value,out bit<16> output_value){
            input_value = (bit<16>)meta.cell_index_part2[CELL_INDEX_HIGHEST:2];
        }
    };
    Register<bit<16>,bit<32>>(MAX_BUCKET_REGISTER_ENTRIES,0) bucket1_to_cell_part2_sketch2;
	RegisterAction<bit<16>,bit<32>,bit<16>>(bucket1_to_cell_part2_sketch2) bucket1_to_cell_part2_sketch2_read = {
        void apply(inout bit<16> input_value,out bit<16> output_value){
            input_value = (bit<16>)meta.cell_index_part2[CELL_INDEX_HIGHEST:2];
        }
    };
    Register<bit<16>,bit<32>>(MAX_BUCKET_REGISTER_ENTRIES,0) bucket2_to_cell_part1_sketch1;
	RegisterAction<bit<16>,bit<32>,bit<16>>(bucket2_to_cell_part1_sketch1) bucket2_to_cell_part1_sketch1_read = {
        void apply(inout bit<16> input_value,out bit<16> output_value){
            input_value = (bit<16>)meta.cell_index_part1[CELL_INDEX_HIGHEST:2];
        }
    };
    Register<bit<16>,bit<32>>(MAX_BUCKET_REGISTER_ENTRIES,0) bucket2_to_cell_part1_sketch2;
	RegisterAction<bit<16>,bit<32>,bit<16>>(bucket2_to_cell_part1_sketch2) bucket2_to_cell_part1_sketch2_read = {
        void apply(inout bit<16> input_value,out bit<16> output_value){
            input_value = (bit<16>)meta.cell_index_part1[CELL_INDEX_HIGHEST:2];
        }
    };
    Register<bit<16>,bit<32>>(MAX_BUCKET_REGISTER_ENTRIES,0) bucket2_to_cell_part2_sketch1;
	RegisterAction<bit<16>,bit<32>,bit<16>>(bucket2_to_cell_part2_sketch1) bucket2_to_cell_part2_sketch1_read = {
        void apply(inout bit<16> input_value,out bit<16> output_value){
            input_value = (bit<16>)meta.cell_index_part2[CELL_INDEX_HIGHEST:2];
        }
    };
    Register<bit<16>,bit<32>>(MAX_BUCKET_REGISTER_ENTRIES,0) bucket2_to_cell_part2_sketch2;
	RegisterAction<bit<16>,bit<32>,bit<16>>(bucket2_to_cell_part2_sketch2) bucket2_to_cell_part2_sketch2_read = {
        void apply(inout bit<16> input_value,out bit<16> output_value){
            input_value = (bit<16>)meta.cell_index_part2[CELL_INDEX_HIGHEST:2];
        }
    };
    //cell division write register tables
    //Microsketch in bucket1 
    action b1_write_cell_part1_sketch1() {
        cell_part1_sketch1_read.execute((bit<32>)meta.cell_index_part1);
    }
    action b1_write_cell_part1_sketch2() {
        cell_part1_sketch2_read.execute((bit<32>)meta.cell_index_part1);
    }
    table b1_update_cell_part1_sketch1 {
        key = {meta.reg_set : exact;}
        actions  = {
            b1_write_cell_part1_sketch1;}
        size = 10;
    }
    table b1_update_cell_part1_sketch2 {
        key = {meta.reg_set : exact;}
        actions  = {
            b1_write_cell_part1_sketch2;}
        size = 10;
    }
    action b1_write_cell_part2_sketch1() {
        cell_part2_sketch1_read.execute((bit<32>)meta.cell_index_part2);
    }
    action b1_write_cell_part2_sketch2() {
        cell_part2_sketch2_read.execute((bit<32>)meta.cell_index_part2);
    }
    table b1_update_cell_part2_sketch1 {
        key = {meta.reg_set : exact;}
        actions  = {
            b1_write_cell_part2_sketch1;}
        size = 10;
    }
    table b1_update_cell_part2_sketch2 {
        key = {meta.reg_set : exact;}
        actions  = {
            b1_write_cell_part2_sketch2;}
        size = 10;
    }
    //Microsketch in bucket2
    action b2_write_cell_part1_sketch1() {
        cell_part1_sketch1_read.execute((bit<32>)meta.cell_index_part1);
    }
    action b2_write_cell_part1_sketch2() {
        cell_part1_sketch2_read.execute((bit<32>)meta.cell_index_part1);
    }
    table b2_update_cell_part1_sketch1 {
        key = {meta.reg_set : exact;}
        actions  = {
            b2_write_cell_part1_sketch1;}
        size = 10;
    }
    table b2_update_cell_part1_sketch2 {
        key = {meta.reg_set : exact;}
        actions  = {
            b2_write_cell_part1_sketch2;}
        size = 10;
    }
    action b2_write_cell_part2_sketch1() {
        cell_part2_sketch1_read.execute((bit<32>)meta.cell_index_part2);
    }
    action b2_write_cell_part2_sketch2() {
        cell_part2_sketch2_read.execute((bit<32>)meta.cell_index_part2);
    }
    table b2_update_cell_part2_sketch1 {
        key = {meta.reg_set : exact;}
        actions  = {
            b2_write_cell_part2_sketch1;}
        size = 10;
    }
    table b2_update_cell_part2_sketch2 {
        key = {meta.reg_set : exact;}
        actions  = {
            b2_write_cell_part2_sketch2;}
        size = 10;
    }
    //need record func 
    //bucket1_index -> cell_index
    action write_b1_to_cell_part1_sketch1() {
        bucket1_to_cell_part1_sketch1_read.execute((bit<32>)meta.bucket1_index);
    }
    action write_b1_to_cell_part1_sketch2() {
        bucket1_to_cell_part1_sketch2_read.execute((bit<32>)meta.bucket1_index);
    }
    table record_b1_to_cell_part1_index_sketch1 {
        key = {meta.reg_set : exact;}
        actions = {
            write_b1_to_cell_part1_sketch1;}
        size = 10;
    }
    table record_b1_to_cell_part1_index_sketch2 {
        key = {meta.reg_set : exact;}
        actions = {
            write_b1_to_cell_part1_sketch2;}
        size = 10;
    }
    action write_b1_to_cell_part2_sketch1() {
        bucket1_to_cell_part2_sketch1_read.execute((bit<32>)meta.bucket1_index);
    }
    action write_b1_to_cell_part2_sketch2() {
        bucket1_to_cell_part2_sketch2_read.execute((bit<32>)meta.bucket1_index);
    }
    table record_b1_to_cell_part2_index_sketch1 {
        key = {meta.reg_set : exact;}
        actions = {
            write_b1_to_cell_part2_sketch1;}
        size = 10;
    }
    table record_b1_to_cell_part2_index_sketch2 {
        key = {meta.reg_set : exact;}
        actions = {
            write_b1_to_cell_part2_sketch2;}
        size = 10;
    }
    //bucket2_index -> cell_index
    action write_b2_to_cell_part1_sketch1() {
        bucket2_to_cell_part1_sketch1_read.execute((bit<32>)meta.bucket2_index);
    }
    action write_b2_to_cell_part1_sketch2() {
        bucket2_to_cell_part1_sketch2_read.execute((bit<32>)meta.bucket2_index);
    }
    table record_b2_to_cell_part1_index_sketch1 {
        key = {meta.reg_set : exact;}
        actions = {
            write_b2_to_cell_part1_sketch1;}
        size = 10;
    }
    table record_b2_to_cell_part1_index_sketch2 {
        key = {meta.reg_set : exact;}
        actions = {
            write_b2_to_cell_part1_sketch2;}
        size = 10;
    }
    action write_b2_to_cell_part2_sketch1() {
        bucket2_to_cell_part2_sketch1_read.execute((bit<32>)meta.bucket2_index);
    }
    action write_b2_to_cell_part2_sketch2() {
        bucket2_to_cell_part2_sketch2_read.execute((bit<32>)meta.bucket2_index);
    }
    table record_b2_to_cell_part2_index_sketch1 {
        key = {meta.reg_set : exact;}
        actions = {
            write_b2_to_cell_part2_sketch1;}
        size = 10;
    }
    table record_b2_to_cell_part2_index_sketch2 {
        key = {meta.reg_set : exact;}
        actions = {
            write_b2_to_cell_part2_sketch2;}
        size = 10;
    }
    action set_offset2(bit<2> value1)
    {
        meta.cell_offset = value1;
    }
    table range_match_level2 {
        key = {
            eg_intr_md.enq_tstamp : range;
        }
        actions = {
            set_offset2;
        }
        const default_action = set_offset2(3);
        size = 100;
    }
    apply {
        //has been marked by edge switches
        if(hdr.ipv4.flags[0:0] == 1w1)
        {
            //choose current sketch to insert
            choose_sketch.apply();
            //get global offset
            range_match_level1.apply();
            range_match_level2.apply();
            /* 2 level dleft alogrithm part*/
            //get bucket1 write position 
            bucket1_index_hash_part.apply();
            complete_bucket1_index.apply();
            //get bucket2 write position 
            bucket2_index_hash_part.apply();
            complete_bucket2_index.apply();
            //get cell part1(divide from bucket1) write position 
            b1_get_cell_hash_part1.apply();
            b1_complete_cell_part1.apply();
            //get cell part2(divide from bucket1) write position 
            b1_get_cell_hash_part2.apply();
            b1_complete_cell_part2.apply();
            //get cell part1(divide from bucket2) write position 
            b2_get_cell_hash_part1.apply();
            b2_complete_cell_part1.apply();
            //get cell part2(divide from bucket2) write position 
            b2_get_cell_hash_part2.apply();
            b2_complete_cell_part2.apply();    
            //use hdr.ipv4.srcip and dstip update tag registers        
            update_bucket1_dstiptag_sketch1.apply();
            update_bucket1_dstiptag_sketch2.apply();
            update_bucket1_srciptag_sketch1.apply();
            update_bucket1_srciptag_sketch2.apply();
            //if bucket1 is empty 
            if(meta.bucket1_compare_dst == 1w0 && meta.bucket1_compare_src == 1w0)
            {
                update_bucket1_sketch1.apply();
                update_bucket1_sketch2.apply();
                /* 1 level cell division part */
                //devide_flag decide whether do cell division or not
                if(meta.divide_flag1 == 1w1)
                {
                    //record hash relation between bucket1 index and cell index 
                    record_b1_to_cell_part1_index_sketch1.apply();
                    record_b1_to_cell_part1_index_sketch2.apply();
                    record_b1_to_cell_part2_index_sketch1.apply();
                    record_b1_to_cell_part2_index_sketch2.apply();
                    //update cell register
                    b1_update_cell_part1_sketch1.apply();
                    b1_update_cell_part1_sketch2.apply();
                    b1_update_cell_part2_sketch1.apply();
                    b1_update_cell_part2_sketch2.apply();
                }
            }
            else
            {
                update_bucket2_dstiptag_sketch1.apply();
                update_bucket2_dstiptag_sketch2.apply();
                update_bucket2_srciptag_sketch1.apply();
                update_bucket2_srciptag_sketch2.apply();
                //if bucket2 is empty 
                if(meta.bucket2_compare_dst == 1w0 && meta.bucket2_compare_src == 1w0)
                {
                    update_bucket2_sketch1.apply();
                    update_bucket2_sketch2.apply();
                    /* 2 level cell division part */
                    //devide_flag decide whether do cell division or not
                    if(meta.divide_flag2 == 1w1)
                    {
                        //record hash relation between bucket2 index and cell index 
                        record_b2_to_cell_part1_index_sketch1.apply();
                        record_b2_to_cell_part1_index_sketch2.apply();
                        record_b2_to_cell_part2_index_sketch1.apply();
                        record_b2_to_cell_part2_index_sketch2.apply();
                        //update cell register
                        b2_update_cell_part1_sketch1.apply();
                        b2_update_cell_part1_sketch2.apply();
                        b2_update_cell_part2_sketch1.apply();
                        b2_update_cell_part2_sketch2.apply();
                    }
                }
            }
        }
    }
}

Pipeline(MyIngressParser(),
         MyIngress(),
         MyIngressDeparser(),
         MyEgressParser(),
         MyEgress(),
         MyEgressDeparser()) pipe;

Switch(pipe) main;