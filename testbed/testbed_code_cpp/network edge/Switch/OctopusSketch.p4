#include<core.p4>
#if __TARGET_TOFINO__ == 2
#include<t2na.p4>
#else
#include<tna.p4>
#endif

#define BUCKET_SIZE 2048
#define BUCKET_SIZE_OFFSET 1024
#define BUCKET_INDEX_MASK 1023
#define BUCKET_INDEX_LEN 16
#define LAMBDA 32
#define LAMBDA_SHIFT 5
#define RECIRCULATE_PORT 14
#define CPU_PORT 192
#define OTHER_PORT 152
typedef bit<32> b32_bucket_len_t;
typedef bit<64> b64_bucket_len_t;
typedef bit<16> b16_t;
typedef bit<10> b10_t;
typedef bit<8> b8_t;
typedef bit<16> bucket_index_len_t;

struct b64_bucket_t {
	bit<32> lo;
	bit<32> hi;
}


/************* HEADERS *************/
header ethernet_h {
    bit<48> dst_addr;
    bit<48> src_addr;
    bit<16> ether_type;
}

header ipv4_h {
    bit<4> version;
    bit<4> ihl;
    bit<8> diffserv;
    bit<16> total_len;
    bit<16> identification;
    bit<16> flags;
    bit<8> ttl;
    bit<8> protocol;
    bit<16> hdr_checksum;
    bit<32> src_addr;
    bit<32> dst_addr;
}

header meta_h {
    bit<8> choose_flag;

    //coco
    bit<16> index_coco;

    //elastic
    bit<16> index_1;
    bit<16> index_2;
    bit<16> index_3;
    bit<16> index_4;
    bit<32> totVotes;
    bit<32> counter_val;
    bit<32> flow_id;    //current flow
    bit<32> flow_freq;
    bit<32> register_id;
    bit<1> heavy_flag;
    bit<1> light_flag;
    bit<6> zero;
}

header udp_h {
	bit<16> src_port;
	bit<16> dst_port;
	bit<16> total_len;
	bit<16> checksum;
}

header myflow_h {
    bit<32> id;
}

header ctlinfo_h {
    bit<8> class_flag;  //0: normal packet      1: packet to read register
    bit<8> read_flag;   //0/1/2/3: elastic 1 id/counter  4/5/6/7: elastic 2 id/counter   8/9/10/11: elastic 4 id/counter    12/13/14/15: coco 1 id/counter
    bit<16> bgn_index;  //set by controller packet
    bit<16> end_index;  //set by controller packet
    bit<16> zero_zone;
}

header data_h {
    bit<32> data;
}

struct ingress_header_t {
    ethernet_h ethernet;
    ipv4_h ipv4;
    udp_h udp;
    ctlinfo_h info;
    myflow_h myflow;
    meta_h meta;
    data_h data;
}

struct ingress_metadata_t{
    bit<8> src_addr_match_result;
    bit<8> dst_addr_match_result;
}

struct egress_header_t {
    ethernet_h ethernet;
    ipv4_h ipv4;
    udp_h udp;
    ctlinfo_h info;     //notice: need zero-zone
    myflow_h myflow;
    meta_h meta;
    data_h data;
}

struct egress_metadata_t {
	bit<32> count;
	bit<32> cond;
  	bit<16> rng;
}

enum bit<16> ether_type_t {
    IPV4    = 0x0800,
    ARP     = 0x0806
}

enum bit<8> ip_proto_t {
    ICMP    = 1,
    IGMP    = 2,
    TCP     = 6,
    UDP     = 17
}

/************* INGRESS *************/
parser IngressParser(packet_in pkt,
	out ingress_header_t hdr,
	out ingress_metadata_t meta,
	out ingress_intrinsic_metadata_t ig_intr_md)
{
	state start{
		pkt.extract(ig_intr_md);
		pkt.advance(PORT_METADATA_SIZE);
		transition parse_ethernet;
	}

	state parse_ethernet{
		pkt.extract(hdr.ethernet);
        transition select((bit<16>)hdr.ethernet.ether_type) {
            (bit<16>)ether_type_t.IPV4      : parse_ipv4;
            (bit<16>)ether_type_t.ARP       : accept;
		0xffff: parse_info;
            default : accept;
        }
	}

	state parse_ipv4{
		pkt.extract(hdr.ipv4);
        transition select(hdr.ipv4.protocol) {
            (bit<8>)ip_proto_t.ICMP             : accept;
            (bit<8>)ip_proto_t.IGMP             : accept;
            (bit<8>)ip_proto_t.TCP              : accept;
            (bit<8>)ip_proto_t.UDP              : parse_udp;
            default : accept;
        }
	}

	state parse_udp{
        pkt.extract(hdr.udp);
	hdr.myflow.setValid();
        hdr.meta.setValid();

        transition accept;
	}
	
	state parse_info {
		pkt.extract(hdr.info);
        	hdr.data.setValid();
		transition accept;
	}

}

control Ingress(inout ingress_header_t hdr,
		inout ingress_metadata_t meta,
		in ingress_intrinsic_metadata_t ig_intr_md,
		in ingress_intrinsic_metadata_from_parser_t ig_prsr_md,
		inout ingress_intrinsic_metadata_for_deparser_t ig_dprsr_md,
		inout ingress_intrinsic_metadata_for_tm_t ig_tm_md)
{
	Hash<bucket_index_len_t>(HashAlgorithm_t.CRC32) hash_1;
	Hash<bucket_index_len_t>(HashAlgorithm_t.CRC32) hash_2;
	Hash<bucket_index_len_t>(HashAlgorithm_t.CRC32) hash_3;

    //commmon used
    action drop_flow_action() {
        hdr.meta.heavy_flag = 0;
        hdr.meta.light_flag = 0;
    }

    action update_flow_action() {
        hdr.meta.flow_id = hdr.meta.register_id;
        hdr.meta.flow_freq = hdr.meta.counter_val;
    }

    action NoAction() {

    }

    //preprocessing
	Hash<b16_t>(HashAlgorithm_t.IDENTITY) id_hash;
    action preprocessing() {
        hdr.myflow.id[15:0] = id_hash.get({hdr.ipv4.protocol, hdr.udp.src_port, hdr.udp.dst_port});
        hdr.myflow.id[23:16] = hdr.ipv4.dst_addr[7:0];
        hdr.myflow.id[31:24] = hdr.ipv4.src_addr[7:0];
    }

    //@stage(0) 
    table preprocessing_table{
        actions = {
            preprocessing;
        }
        size = 100;
        const default_action = preprocessing;
    }

    action preprocessing_1() {
        hdr.meta.index_1 = hash_1.get({hdr.ipv4.src_addr, hdr.ipv4.dst_addr, hdr.ipv4.protocol, hdr.udp.src_port, hdr.udp.dst_port});
    }

    //@stage(0) 
    table preprocessing_table_1{
        actions = {
            preprocessing_1;
        }
        size = 100;
        const default_action = preprocessing_1;
    }

    action preprocessing_2() {
        hdr.meta.index_2 = hash_2.get({hdr.meta.flow_id});
    }

    //@stage(0) 
    table preprocessing_table_02{
        actions = {
            preprocessing_2;
        }
        size = 100;
        const default_action = preprocessing_2;
    }
    
    //@stage(0) 
    table preprocessing_table_12{
        actions = {
            preprocessing_2;
        }
        size = 100;
        const default_action = preprocessing_2;
    }

    action preprocessing_3() {
        hdr.meta.index_3 = hash_3.get({hdr.meta.flow_id});
    }

    //@stage(0) 
    table preprocessing_table_03{
        actions = {
            preprocessing_3;
        }
        size = 100;
        const default_action = preprocessing_3;
    }
    
    //@stage(0) 
    table preprocessing_table_13{
        actions = {
            preprocessing_3;
        }
        size = 100;
        const default_action = preprocessing_3;
    }

    Register<b8_t, bit<1>>(1) sketch_choose_flag;
    RegisterAction<b8_t, bit<1>, b8_t>(sketch_choose_flag) sketch_choose_salu = {
        void apply(inout b8_t reg_data, out b8_t out_data) {
            out_data = reg_data;
        }
    };

    action sketch_choose_action() {
        hdr.meta.choose_flag = sketch_choose_salu.execute(0);
    }

    //@stage(0)
    table sketch_choose_table {
        actions = {
            sketch_choose_action;
        }
        size = 100;
        const default_action = sketch_choose_action;
    }

    action mark_INT() {
        hdr.ipv4.flags = hdr.ipv4.flags | 0x2000;
    }

    //@stage(1)
    table mark_INT_table {
        key = {
            hdr.myflow.id: exact;
        }
        actions = {
            mark_INT;
        }
        size = 5000;
    }

    action mark_choice_true() {
        hdr.ipv4.flags = hdr.ipv4.flags | 0x4000;
    }

    table mark_choice_true_table {
        actions = {
            mark_choice_true;
        }
        size = 100;
        const default_action = mark_choice_true;
    }

    action mark_choice_false() {
        hdr.ipv4.flags = hdr.ipv4.flags & 0xbfff;
    }

    table mark_choice_false_table {
        actions = {
            mark_choice_false;
        }
        size = 100;
        const default_action = mark_choice_false;
    }

    action in_index_cal_action() {
        hdr.meta.index_1 = hdr.meta.index_1&BUCKET_INDEX_MASK;
        hdr.meta.index_2 = hdr.meta.index_2&BUCKET_INDEX_MASK;
        hdr.meta.index_3 = hdr.meta.index_3&BUCKET_INDEX_MASK;
        hdr.meta.index_4 = hdr.meta.index_4&BUCKET_INDEX_MASK;
    }

    action out_index_cal_action() {
        hdr.meta.index_1 = hdr.meta.index_1&BUCKET_INDEX_MASK+BUCKET_SIZE_OFFSET;
        hdr.meta.index_2 = hdr.meta.index_2&BUCKET_INDEX_MASK+BUCKET_SIZE_OFFSET;
        hdr.meta.index_3 = hdr.meta.index_3&BUCKET_INDEX_MASK+BUCKET_SIZE_OFFSET;
        hdr.meta.index_4 = hdr.meta.index_4&BUCKET_INDEX_MASK+BUCKET_SIZE_OFFSET;
    }

    //@stage(1)
    table inout_port_index_table{
        key = {
            ig_intr_md.ingress_port: exact;
        }
        actions = {
            in_index_cal_action;
            out_index_cal_action;
        }
        size = 64;
        // const default_action = in_index_cal_action;
    }

    /******************CREATE ABNORMAL FLOW **************/
    Register<bit<8>, bit<8>>(256) flow_amount;
    RegisterAction<bit<8>, bit<8>, bit<8>>(flow_amount) judge_drop_salu = {
        void apply(inout bit<8> reg_data, out bit<8> out_data) {
            if(reg_data == 9) {
                reg_data = 0;
                out_data = 3;
            }
            else {
                reg_data = reg_data + 1;
                out_data = 1;
            }
        }
    };

    action judge_drop_action(bit<8> index) {
        hdr.meta.choose_flag = judge_drop_salu.execute(index);
    }

    //@stage(1)
    table create_abnormal_table{
        key = {
            ig_intr_md.ingress_port:exact;
            hdr.ipv4.src_addr: exact;
            hdr.ipv4.dst_addr: exact;
        }
        actions = {
            judge_drop_action;
            NoAction;
        }
        size = 256;
        const default_action = NoAction;
    }

    //elastic 01
    Register<b32_bucket_len_t, bucket_index_len_t>(BUCKET_SIZE) total_vote_01;
    RegisterAction<b32_bucket_len_t, bucket_index_len_t, b32_bucket_len_t>(total_vote_01) total_vote_salu_01 = {
        void apply(inout b32_bucket_len_t reg_data, out b32_bucket_len_t out_data) {
            reg_data = reg_data + 1;
            out_data = reg_data;
        }
    };

    action total_vote_action_01() {
        hdr.meta.totVotes = total_vote_salu_01.execute(hdr.meta.index_1);
        hdr.meta.register_id = 0;
        hdr.meta.heavy_flag = 1;
        hdr.meta.light_flag = 1;
    }

    //@stage(2)
    table total_vote_table_01 {
        actions = {
            total_vote_action_01;
        }
        size = 100;
        const default_action = total_vote_action_01;
    }

    Register<b64_bucket_t, bucket_index_len_t>(BUCKET_SIZE) freq_vote_01;
    RegisterAction<b64_bucket_t, bucket_index_len_t, b32_bucket_len_t>(freq_vote_01) freq_vote_salu_01 = {
        void apply(inout b64_bucket_t reg_data, out b32_bucket_len_t out_data) {
            if(hdr.meta.totVotes >= reg_data.hi || hdr.myflow.id == reg_data.lo) {
                out_data = reg_data.lo;
                reg_data.lo = hdr.myflow.id;
                reg_data.hi = reg_data.hi + LAMBDA;
            }
            else {
                out_data = 0;
            }
        }
    };

    action freq_vote_action_01() {
        hdr.meta.register_id = freq_vote_salu_01.execute(hdr.meta.index_1);
    }

    //@stage(3)
    table freq_vote_table_01 {
        actions = {
            freq_vote_action_01;
        }
        size = 100;
        const default_action = freq_vote_action_01;
    }

    //2023-9-13 add
    RegisterAction<b64_bucket_t, bucket_index_len_t, b32_bucket_len_t>(freq_vote_01) read_counter_freq_vote_salu_01 = {
        void apply(inout b64_bucket_t reg_data, out b32_bucket_len_t out_data) {
            out_data = reg_data.hi;
        }
    };

    RegisterAction<b64_bucket_t, bucket_index_len_t, b32_bucket_len_t>(freq_vote_01) read_id_freq_vote_salu_01 = {
        void apply(inout b64_bucket_t reg_data, out b32_bucket_len_t out_data) {
            out_data = reg_data.lo;
        }
    };

    action read_counter_freq_vote_action_01() {
        hdr.data.data = read_counter_freq_vote_salu_01.execute(hdr.info.bgn_index);
	hdr.info.bgn_index = hdr.info.bgn_index+1;

    }

    action read_id_freq_vote_action_01() {
        hdr.data.data = read_id_freq_vote_salu_01.execute(hdr.info.bgn_index);
	hdr.info.bgn_index = hdr.info.bgn_index+1;
    }

    table read_freq_vote_table_01 {
        key = {
            hdr.info.read_flag: exact;
        }
        actions = {
            read_counter_freq_vote_action_01;
            read_id_freq_vote_action_01;
            NoAction;
        }
        size = 2;
        const default_action = NoAction;
        const entries = {
            3: read_counter_freq_vote_action_01();
            2: read_id_freq_vote_action_01();
        }
    }


    //@stage(4)
    table drop_flow_table_01 {
        actions = {
            drop_flow_action;
        }
        size = 100;
        const default_action = drop_flow_action;
    }

    Register<b32_bucket_len_t, bucket_index_len_t>(BUCKET_SIZE) freq_vote_copy_01;
    RegisterAction<b32_bucket_len_t, bucket_index_len_t, b32_bucket_len_t>(freq_vote_copy_01) freq_vote_copy_salu_01 = {
        void apply(inout b32_bucket_len_t reg_data, out b32_bucket_len_t out_data) {
            reg_data = reg_data + LAMBDA;
            out_data = reg_data;
        }
    };

    action freq_vote_copy_action_01() {
        hdr.meta.counter_val = freq_vote_copy_salu_01.execute(hdr.meta.index_1);
    }

    table freq_vote_copy_table_01 {
        actions = {
            freq_vote_copy_action_01;
        }
        size = 100;
        const default_action = freq_vote_copy_action_01;
    }

    //@stage(4)
    table update_flow_table_01 {
        actions = {
            update_flow_action;
        }
        size = 100;
        const default_action = update_flow_action;
    }


    //elastic 02
    Register<b32_bucket_len_t, bucket_index_len_t>(BUCKET_SIZE) total_vote_02;
    RegisterAction<b32_bucket_len_t, bucket_index_len_t, b32_bucket_len_t>(total_vote_02) total_vote_salu_02 = {
        void apply(inout b32_bucket_len_t reg_data, out b32_bucket_len_t out_data) {
            reg_data = reg_data + 1;
            out_data = reg_data;
        }
    };

    action total_vote_action_02() {
        hdr.meta.totVotes = total_vote_salu_02.execute(hdr.meta.index_2);
        hdr.meta.register_id = 0;
    }

    //@stage(5)
    table total_vote_table_02 {
        actions = {
            total_vote_action_02;
        }
        size = 100;
        const default_action = total_vote_action_02;
    }

    Register<b64_bucket_t, bucket_index_len_t>(BUCKET_SIZE) freq_vote_02;
    RegisterAction<b64_bucket_t, bucket_index_len_t, b32_bucket_len_t>(freq_vote_02) freq_vote_salu_02 = {
        void apply(inout b64_bucket_t reg_data, out b32_bucket_len_t out_data) {
                if(hdr.meta.totVotes >= reg_data.hi || hdr.myflow.id == reg_data.lo) {
                    out_data = reg_data.lo;
                    reg_data.lo = hdr.myflow.id;
                    reg_data.hi = reg_data.hi + LAMBDA;
                }
                else {
                    out_data = 0;
                }
        }
    };

    action freq_vote_action_02() {
        hdr.meta.register_id = freq_vote_salu_02.execute(hdr.meta.index_2);
    }

    //@stage(6)
    table freq_vote_table_02 {
        actions = {
            freq_vote_action_02;
        }
        size = 100;
        const default_action = freq_vote_action_02;
    }

    //2023-9-13 add
    RegisterAction<b64_bucket_t, bucket_index_len_t, b32_bucket_len_t>(freq_vote_02) read_counter_freq_vote_salu_02 = {
        void apply(inout b64_bucket_t reg_data, out b32_bucket_len_t out_data) {
            out_data = reg_data.hi;
        }
    };

    RegisterAction<b64_bucket_t, bucket_index_len_t, b32_bucket_len_t>(freq_vote_02) read_id_freq_vote_salu_02 = {
        void apply(inout b64_bucket_t reg_data, out b32_bucket_len_t out_data) {
            out_data = reg_data.lo;
        }
    };

    action read_counter_freq_vote_action_02() {
        hdr.data.data = read_counter_freq_vote_salu_02.execute(hdr.info.bgn_index);
	hdr.info.bgn_index = hdr.info.bgn_index+1;
    }

    action read_id_freq_vote_action_02() {
        hdr.data.data = read_id_freq_vote_salu_02.execute(hdr.info.bgn_index);
	hdr.info.bgn_index = hdr.info.bgn_index+1;
    }

    table read_freq_vote_table_02 {
        key = {
            hdr.info.read_flag: exact;
        }
        actions = {
            read_counter_freq_vote_action_02;
            read_id_freq_vote_action_02;
            NoAction;
        }
        size = 2;
        const default_action = NoAction;
        const entries = {
            7: read_counter_freq_vote_action_02();
            6: read_id_freq_vote_action_02();
        }

    }


    //@stage(7)
    table drop_flow_table_02 {
        actions = {
            drop_flow_action;
        }
        size = 100;
        const default_action = drop_flow_action;
    }

    Register<b32_bucket_len_t, bucket_index_len_t>(BUCKET_SIZE) freq_vote_copy_02;
    RegisterAction<b32_bucket_len_t, bucket_index_len_t, b32_bucket_len_t>(freq_vote_copy_02) freq_vote_copy_salu_02 = {
        void apply(inout b32_bucket_len_t reg_data, out b32_bucket_len_t out_data) {
            reg_data = reg_data + LAMBDA;
            out_data = reg_data;
        }
    };

    action freq_vote_copy_action_02() {
        hdr.meta.counter_val = freq_vote_copy_salu_02.execute(hdr.meta.index_2);
    }

    table freq_vote_copy_table_02 {
        actions = {
            freq_vote_copy_action_02;
        }
        size = 100;
        const default_action = freq_vote_copy_action_02;
    }

    //@stage(7)
    table update_flow_table_02 {
        actions = {
            update_flow_action;
        }
        size = 100;
        const default_action = update_flow_action;
    }

    //elastic 03
    Register<b32_bucket_len_t, bucket_index_len_t>(BUCKET_SIZE) total_vote_03;
    RegisterAction<b32_bucket_len_t, bucket_index_len_t, b32_bucket_len_t>(total_vote_03) total_vote_salu_03 = {
        void apply(inout b32_bucket_len_t reg_data, out b32_bucket_len_t out_data) {
            reg_data = reg_data + 1;
            out_data = reg_data;
        }
    };

    action total_vote_action_03() {
        hdr.meta.totVotes = total_vote_salu_03.execute(hdr.meta.index_3);
        hdr.meta.register_id = 0;
    }

    //@stage(8)
    table total_vote_table_03 {
        actions = {
            total_vote_action_03;
        }
        size = 100;
        const default_action = total_vote_action_03;
    }

    Register<b64_bucket_t, bucket_index_len_t>(BUCKET_SIZE) freq_vote_03;
    RegisterAction<b64_bucket_t, bucket_index_len_t, b32_bucket_len_t>(freq_vote_03) freq_vote_salu_03 = {
        void apply(inout b64_bucket_t reg_data, out b32_bucket_len_t out_data) {
                if(hdr.meta.totVotes >= reg_data.hi || hdr.myflow.id == reg_data.lo) {
                    out_data = reg_data.lo;
                    reg_data.lo = hdr.myflow.id;
                    reg_data.hi = reg_data.hi + LAMBDA;
                }
                else {
                    out_data = 0;
                }
        }
    };

    action freq_vote_action_03() {
        hdr.meta.register_id = freq_vote_salu_03.execute(hdr.meta.index_3);
    }

    //@stage(9)
    table freq_vote_table_03 {
        actions = {
            freq_vote_action_03;
        }
        size = 100;
        const default_action = freq_vote_action_03;
    }

    //@stage(10)
    table drop_flow_table_03 {
        actions = {
            drop_flow_action;
        }
        size = 100;
        const default_action = drop_flow_action;
    }

    Register<b32_bucket_len_t, bucket_index_len_t>(BUCKET_SIZE) freq_vote_copy_03;
    RegisterAction<b32_bucket_len_t, bucket_index_len_t, b32_bucket_len_t>(freq_vote_copy_03) freq_vote_copy_salu_03 = {
        void apply(inout b32_bucket_len_t reg_data, out b32_bucket_len_t out_data) {
            reg_data = reg_data + LAMBDA;
            out_data = reg_data;
        }
    };

    action freq_vote_copy_action_03() {
        hdr.meta.counter_val = freq_vote_copy_salu_03.execute(hdr.meta.index_3);
    }

    table freq_vote_copy_table_03 {
        actions = {
            freq_vote_copy_action_03;
        }
        size = 100;
        const default_action = freq_vote_copy_action_03;
    }

    //@stage(10)
    table update_flow_table_03 {
        actions = {
            update_flow_action;
        }
        size = 100;
        const default_action = update_flow_action;
    }


    //elastic 11
    Register<b32_bucket_len_t, bucket_index_len_t>(BUCKET_SIZE) total_vote_11;
    RegisterAction<b32_bucket_len_t, bucket_index_len_t, b32_bucket_len_t>(total_vote_11) total_vote_salu_11 = {
        void apply(inout b32_bucket_len_t reg_data, out b32_bucket_len_t out_data) {
            reg_data = reg_data + 1;
            out_data = reg_data;
        }
    };

    action total_vote_action_11() {
        hdr.meta.totVotes = total_vote_salu_11.execute(hdr.meta.index_1);
        hdr.meta.register_id = 0;
        hdr.meta.heavy_flag = 1;
        hdr.meta.light_flag = 1;
    }

    //@stage(2)
    table total_vote_table_11 {
        actions = {
            total_vote_action_11;
        }
        size = 100;
        const default_action = total_vote_action_11;
    }

    Register<b64_bucket_t, bucket_index_len_t>(BUCKET_SIZE) freq_vote_11;
    RegisterAction<b64_bucket_t, bucket_index_len_t, b32_bucket_len_t>(freq_vote_11) freq_vote_salu_11 = {
        void apply(inout b64_bucket_t reg_data, out b32_bucket_len_t out_data) {
                if(hdr.meta.totVotes >= reg_data.hi || hdr.myflow.id == reg_data.lo) {
                    out_data = reg_data.lo;
                    reg_data.lo = hdr.myflow.id;
                    reg_data.hi = reg_data.hi + LAMBDA;
                }
                else {
                    out_data = 0;
                }
        }
    };


    action freq_vote_action_11() {
        hdr.meta.register_id = freq_vote_salu_11.execute(hdr.meta.index_1);
    }

    //@stage(3)
    table freq_vote_table_11 {
        actions = {
            freq_vote_action_11;
        }
        size = 100;
        const default_action = freq_vote_action_11;
    }

    RegisterAction<b64_bucket_t, bucket_index_len_t, b32_bucket_len_t>(freq_vote_11) read_counter_freq_vote_salu_11 = {
        void apply(inout b64_bucket_t reg_data, out b32_bucket_len_t out_data) {
            out_data = reg_data.hi;
        }
    };

    RegisterAction<b64_bucket_t, bucket_index_len_t, b32_bucket_len_t>(freq_vote_11) read_id_freq_vote_salu_11 = {
        void apply(inout b64_bucket_t reg_data, out b32_bucket_len_t out_data) {
            out_data = reg_data.lo;
        }
    };

    action read_counter_freq_vote_action_11() {
        hdr.data.data = read_counter_freq_vote_salu_11.execute(hdr.info.bgn_index);
	hdr.info.bgn_index = hdr.info.bgn_index+1;
    }

    action read_id_freq_vote_action_11() {
        hdr.data.data = read_id_freq_vote_salu_11.execute(hdr.info.bgn_index);
	hdr.info.bgn_index = hdr.info.bgn_index+1;
    }

    table read_freq_vote_table_11 {
        key = {
            hdr.info.read_flag: exact;
        }
        actions = {
            read_counter_freq_vote_action_11;
            read_id_freq_vote_action_11;
            NoAction;
        }
        size = 100;
        const default_action = NoAction;
        const entries = {
            1: read_counter_freq_vote_action_11();
            0: read_id_freq_vote_action_11();
        }
    }

    //@stage(4)
    table drop_flow_table_11 {
        actions = {
            drop_flow_action;
        }
        size = 2;
        const default_action = drop_flow_action;
    }

    Register<b32_bucket_len_t, bucket_index_len_t>(BUCKET_SIZE) freq_vote_copy_11;
    RegisterAction<b32_bucket_len_t, bucket_index_len_t, b32_bucket_len_t>(freq_vote_copy_11) freq_vote_copy_salu_11 = {
        void apply(inout b32_bucket_len_t reg_data, out b32_bucket_len_t out_data) {
            reg_data = reg_data + LAMBDA;
            out_data = reg_data;
        }
    };

    action freq_vote_copy_action_11() {
        hdr.meta.counter_val = freq_vote_copy_salu_11.execute(hdr.meta.index_1);
    }

    table freq_vote_copy_table_11 {
        actions = {
            freq_vote_copy_action_11;
        }
        size = 100;
        const default_action = freq_vote_copy_action_11;
    }

    //@stage(4)
    table update_flow_table_11 {
        actions = {
            update_flow_action;
        }
        size = 100;
        const default_action = update_flow_action;
    }

    //elastic 12
    Register<b32_bucket_len_t, bucket_index_len_t>(BUCKET_SIZE) total_vote_12;
    RegisterAction<b32_bucket_len_t, bucket_index_len_t, b32_bucket_len_t>(total_vote_12) total_vote_salu_12 = {
        void apply(inout b32_bucket_len_t reg_data, out b32_bucket_len_t out_data) {
            reg_data = reg_data + 1;
            out_data = reg_data;
        }
    };

    action total_vote_action_12() {
        hdr.meta.totVotes = total_vote_salu_12.execute(hdr.meta.index_2);
        hdr.meta.register_id = 0;
    }

    //@stage(5)
    table total_vote_table_12 {
        actions = {
            total_vote_action_12;
        }
        size = 100;
        const default_action = total_vote_action_12;
    }

    Register<b64_bucket_t, bucket_index_len_t>(BUCKET_SIZE) freq_vote_12;
    RegisterAction<b64_bucket_t, bucket_index_len_t, b32_bucket_len_t>(freq_vote_12) freq_vote_salu_12 = {
        void apply(inout b64_bucket_t reg_data, out b32_bucket_len_t out_data) {
                if(hdr.meta.totVotes >= reg_data.hi || hdr.myflow.id == reg_data.lo) {
                    out_data = reg_data.lo;
                    reg_data.lo = hdr.myflow.id;
                    reg_data.hi = reg_data.hi + LAMBDA;
                }
                else {
                    out_data = 0;
                }
        }
    };

    action freq_vote_action_12() {
        hdr.meta.register_id = freq_vote_salu_12.execute(hdr.meta.index_2);
    }

    //@stage(6)
    table freq_vote_table_12 {
        actions = {
            freq_vote_action_12;
        }
        size = 100;
        const default_action = freq_vote_action_12;
    }

    //2023-9-13 add
    RegisterAction<b64_bucket_t, bucket_index_len_t, b32_bucket_len_t>(freq_vote_12) read_counter_freq_vote_salu_12 = {
        void apply(inout b64_bucket_t reg_data, out b32_bucket_len_t out_data) {
            out_data = reg_data.hi;
        }
    };

    RegisterAction<b64_bucket_t, bucket_index_len_t, b32_bucket_len_t>(freq_vote_12) read_id_freq_vote_salu_12 = {
        void apply(inout b64_bucket_t reg_data, out b32_bucket_len_t out_data) {
            out_data = reg_data.lo;
        }
    };

    action read_counter_freq_vote_action_12() {
        hdr.data.data = read_counter_freq_vote_salu_12.execute(hdr.info.bgn_index);
	hdr.info.bgn_index = hdr.info.bgn_index+1;
    }

    action read_id_freq_vote_action_12() {
        hdr.data.data = read_id_freq_vote_salu_12.execute(hdr.info.bgn_index);
	hdr.info.bgn_index = hdr.info.bgn_index+1;
    }

    table read_freq_vote_table_12 {
        key = {
            hdr.info.read_flag: exact;
        }
        actions = {
            read_counter_freq_vote_action_12;
            read_id_freq_vote_action_12;
            NoAction;
        }
        size = 2;
        const default_action = NoAction;
        const entries = {
            5: read_counter_freq_vote_action_12();
            4: read_id_freq_vote_action_12();
        }
    }



    //@stage(7)
    table drop_flow_table_12 {
        actions = {
            drop_flow_action;
        }
        size = 100;
        const default_action = drop_flow_action;
    }

    Register<b32_bucket_len_t, bucket_index_len_t>(BUCKET_SIZE) freq_vote_copy_12;
    RegisterAction<b32_bucket_len_t, bucket_index_len_t, b32_bucket_len_t>(freq_vote_copy_12) freq_vote_copy_salu_12 = {
        void apply(inout b32_bucket_len_t reg_data, out b32_bucket_len_t out_data) {
            reg_data = reg_data + LAMBDA;
            out_data = reg_data;
        }
    };

    action freq_vote_copy_action_12() {
        hdr.meta.counter_val = freq_vote_copy_salu_12.execute(hdr.meta.index_2);
    }

    table freq_vote_copy_table_12 {
        actions = {
            freq_vote_copy_action_12;
        }
        size = 100;
        const default_action = freq_vote_copy_action_12;
    }

    //@stage(7)
    table update_flow_table_12 {
        actions = {
            update_flow_action;
        }
        size = 100;
        const default_action = update_flow_action;
    }

    //elastic 13
    Register<b32_bucket_len_t, bucket_index_len_t>(BUCKET_SIZE) total_vote_13;
    RegisterAction<b32_bucket_len_t, bucket_index_len_t, b32_bucket_len_t>(total_vote_13) total_vote_salu_13 = {
        void apply(inout b32_bucket_len_t reg_data, out b32_bucket_len_t out_data) {
            reg_data = reg_data + 1;
            out_data = reg_data;
        }
    };

    action total_vote_action_13() {
        hdr.meta.totVotes = total_vote_salu_13.execute(hdr.meta.index_3);
        hdr.meta.register_id = 0;
    }

    //@stage(8)
    table total_vote_table_13 {
        actions = {
            total_vote_action_13;
        }
        size = 100;
        const default_action = total_vote_action_13;
    }

    Register<b64_bucket_t, bucket_index_len_t>(BUCKET_SIZE) freq_vote_13;
    RegisterAction<b64_bucket_t, bucket_index_len_t, b32_bucket_len_t>(freq_vote_13) freq_vote_salu_13 = {
        void apply(inout b64_bucket_t reg_data, out b32_bucket_len_t out_data) {
                if(hdr.meta.totVotes >= reg_data.hi || hdr.myflow.id == reg_data.lo) {
                    out_data = reg_data.lo;
                    reg_data.lo = hdr.myflow.id;
                    reg_data.hi = reg_data.hi + LAMBDA;
                }
                else {
                    out_data = 0;
                }
        }
    };

    action freq_vote_action_13() {
        hdr.meta.register_id = freq_vote_salu_13.execute(hdr.meta.index_3);
    }

    //@stage(9)
    table freq_vote_table_13 {
        actions = {
            freq_vote_action_13;
        }
        size = 100;
        const default_action = freq_vote_action_13;
    }

    //@stage(10)
    table drop_flow_table_13 {
        actions = {
            drop_flow_action;
        }
        size = 100;
        const default_action = drop_flow_action;
    }

    Register<b32_bucket_len_t, bucket_index_len_t>(BUCKET_SIZE) freq_vote_copy_13;
    RegisterAction<b32_bucket_len_t, bucket_index_len_t, b32_bucket_len_t>(freq_vote_copy_13) freq_vote_copy_salu_13 = {
        void apply(inout b32_bucket_len_t reg_data, out b32_bucket_len_t out_data) {
            reg_data = reg_data + LAMBDA;
            out_data = reg_data;
        }
    };

    action freq_vote_copy_action_13() {
        hdr.meta.counter_val = freq_vote_copy_salu_13.execute(hdr.meta.index_3);
    }

    table freq_vote_copy_table_13 {
        actions = {
            freq_vote_copy_action_13;
        }
        size = 100;
        const default_action = freq_vote_copy_action_13;
    }

    //@stage(10)
    table update_flow_table_13 {
        actions = {
            update_flow_action;
        }
        size = 100;
        const default_action = update_flow_action;
    }


    //srcAddr lpm match
    action src_addr_lpm_match(bit<8> result) {
        meta.src_addr_match_result = result;
    }
    table src_addr_match {
        key = {
            hdr.ipv4.src_addr : lpm;
        }
        actions = {src_addr_lpm_match;}
        size = 100;
    }
    //dstAddr lpm match
    action dst_addr_lpm_match(bit<8> result) {
        meta.dst_addr_match_result = result;
    }
    table dst_addr_match {
        key = {
            hdr.ipv4.dst_addr : lpm;
        }
        actions = {dst_addr_lpm_match;}
        size = 100;
    }
    //port match 
    action set_egress_port(bit<9> port) {
        ig_tm_md.ucast_egress_port = port;
    }
    table leave_port {
        key = {
            meta.src_addr_match_result : exact;
            meta.dst_addr_match_result : exact;
            ig_intr_md.ingress_port : exact;
        }
        actions = {set_egress_port;}
        size = 30;
    }

    Register<bit<32>, bit<32>>(size=1, initial_value=0) int_reg;
    RegisterAction<bit<32>, bit<32>, void>(int_reg) int_reg_salu={
        void apply(inout bit<32> register_data) {
            if (hdr.ipv4.flags[13:13] == 1)
                register_data = register_data + 1;
        }
    };

    Register<bit<32>, bit<32>>(size=1, initial_value=0) id_reg;
    RegisterAction<bit<32>, bit<32>, void>(id_reg) id_reg_salu={
        void apply(inout bit<32> register_data) {
            register_data = (bit<32>)hdr.meta.index_1;
        }
    };

    Register<bit<32>, bit<32>>(size=1, initial_value=0) id1_reg;
    RegisterAction<bit<32>, bit<32>, void>(id1_reg) id1_reg_salu={
        void apply(inout bit<32> register_data) {
            register_data = (bit<32>)hdr.meta.index_1;
        }
    };

    apply {
        if(hdr.udp.isValid()) {
            src_addr_match.apply();
            dst_addr_match.apply();
            leave_port.apply();
            preprocessing_table.apply();
            preprocessing_table_1.apply();
            id1_reg_salu.execute(0);
            sketch_choose_table.apply();
            if (hdr.meta.choose_flag == 1)
                mark_choice_true_table.apply();
            else
                mark_choice_false_table.apply();
            inout_port_index_table.apply();
            mark_INT_table.apply();
            int_reg_salu.execute(0);
            id_reg_salu.execute(0);
            // create_abnormal_table.apply();
            // id_cal_table.apply();
            if(hdr.meta.choose_flag == 1) {
                //elastic
                total_vote_table_11.apply();
                freq_vote_table_11.apply();
                if(hdr.meta.register_id != 0) {
                    if(hdr.meta.register_id == hdr.myflow.id) {
                        drop_flow_table_11.apply();
                    }
                    freq_vote_copy_table_11.apply();
                    update_flow_table_11.apply();
                }

                if(hdr.meta.heavy_flag == 1) {
                    preprocessing_table_12.apply();
                    total_vote_table_12.apply();
                    freq_vote_table_12.apply();
                    if(hdr.meta.register_id != 0) {
                        if(hdr.meta.register_id == hdr.myflow.id) {
                            drop_flow_table_12.apply();
                        }
                        freq_vote_copy_table_12.apply();
                        update_flow_table_12.apply();
                    }
                }
                /*
                if(hdr.meta.heavy_flag == 1) {
                    preprocessing_table_13.apply();
                    total_vote_table_13.apply();
                    freq_vote_table_13.apply();
                    if(hdr.meta.register_id != 0) {
                        if(hdr.meta.register_id == hdr.myflow.id) {
                            drop_flow_table_13.apply();
                        }
                        freq_vote_copy_table_13.apply();
                        update_flow_table_13.apply();
                    }
                }
                */
            }
            else if(hdr.meta.choose_flag == 0){
                //elastic
                total_vote_table_01.apply();
                freq_vote_table_01.apply();
                if(hdr.meta.register_id != 0) {
                    if(hdr.meta.register_id == hdr.myflow.id) {
                        drop_flow_table_01.apply();
                    }
                    freq_vote_copy_table_01.apply();
                    update_flow_table_01.apply();
                }

                if(hdr.meta.heavy_flag == 1) {
                    preprocessing_table_02.apply();
                    total_vote_table_02.apply();
                    freq_vote_table_02.apply();
                    if(hdr.meta.register_id != 0) {
                        if(hdr.meta.register_id == hdr.myflow.id) {
                            drop_flow_table_02.apply();
                        }
                        freq_vote_copy_table_02.apply();
                        update_flow_table_02.apply();
                    }
                }
                /*
                if(hdr.meta.heavy_flag == 1) {
                    preprocessing_table_03.apply();
                    total_vote_table_03.apply();
                    freq_vote_table_03.apply();
                    if(hdr.meta.register_id != 0) {
                        if(hdr.meta.register_id == hdr.myflow.id) {
                            drop_flow_table_03.apply();
                        }
                        freq_vote_copy_table_03.apply();
                        update_flow_table_03.apply();
                    }
                }
                */
            }
            // meta_copy_table.apply();
            //ig_tm_md.ucast_egress_port = CPU_PORT;
                ig_tm_md.ucast_egress_port = OTHER_PORT;
	
        }
        else if(hdr.info.isValid()){
            if(hdr.info.end_index != hdr.info.bgn_index) {
                read_freq_vote_table_11.apply();
                read_freq_vote_table_01.apply();
                read_freq_vote_table_12.apply();
                read_freq_vote_table_02.apply();
                ig_tm_md.ucast_egress_port = RECIRCULATE_PORT;
		}
		else {
			
                ig_tm_md.ucast_egress_port = CPU_PORT;
		}
       } 
    }

}

control IngressDeparser(packet_out pkt,
	inout ingress_header_t hdr,
	in ingress_metadata_t meta,
	in ingress_intrinsic_metadata_for_deparser_t ig_dprtr_md)
{
	apply{
		pkt.emit(hdr);
	}
}


/************* INGRESS *************/
parser EgressParser(packet_in pkt,
	out egress_header_t hdr,
	out egress_metadata_t meta,
	out egress_intrinsic_metadata_t eg_intr_md)
{
	state start{
		pkt.extract(eg_intr_md);
		transition parse_ethernet;
	}

	state parse_ethernet{
		pkt.extract(hdr.ethernet);
        transition select((bit<16>)hdr.ethernet.ether_type) {
            (bit<16>)ether_type_t.IPV4      : parse_ipv4;
            (bit<16>)ether_type_t.ARP       : accept;
            default : accept;
        }
	}

	state parse_ipv4{
		pkt.extract(hdr.ipv4);
        transition select(hdr.ipv4.protocol) {
            (bit<8>)ip_proto_t.ICMP             : accept;
            (bit<8>)ip_proto_t.IGMP             : accept;
            (bit<8>)ip_proto_t.TCP              : accept;
            (bit<8>)ip_proto_t.UDP              : parse_myflow;
            default : accept;
        }
	}

	state parse_myflow{
        pkt.extract(hdr.udp);
        pkt.extract(hdr.info);
		pkt.extract(hdr.myflow);
        pkt.extract(hdr.meta);
		transition accept;
	}
}

control Egress(inout egress_header_t hdr,
	inout egress_metadata_t meta,
	in egress_intrinsic_metadata_t eg_intr_md,
	in egress_intrinsic_metadata_from_parser_t eg_prsr_md,
	inout egress_intrinsic_metadata_for_deparser_t eg_dprsr_md,
	inout egress_intrinsic_metadata_for_output_port_t eg_oport_md)
{
	Hash<bucket_index_len_t>(HashAlgorithm_t.CRC32) hash_4;
    CRCPolynomial<bit<32>>(coeff=0x04C11DB7,reversed=true, msb=false, extended=false, init=0xFFFFFFFF, xor=0xFFFFFFFF) crc32_1;
	Hash<bucket_index_len_t>(HashAlgorithm_t.CUSTOM, crc32_1) coco_hash_1;

    //commmon used
    action drop_flow_action() {
        hdr.meta.heavy_flag = 0;
        hdr.meta.light_flag = 0;
    }

    action update_flow_action() {
        hdr.meta.flow_id = hdr.meta.register_id;
        hdr.meta.flow_freq = hdr.meta.counter_val;
    }

    action preprocessing_4() {
        hdr.meta.index_4 = hash_4.get({hdr.ipv4.src_addr, hdr.ipv4.dst_addr, hdr.ipv4.protocol, hdr.udp.src_port, hdr.udp.dst_port});
    }

    //@stage(0) 
    table preprocessing_table_4{
        actions = {
            preprocessing_4;
        }
        size = 100;
        const default_action = preprocessing_4;
    }

    action coco_preprocessing_1() {
        hdr.meta.index_coco = coco_hash_1.get({hdr.meta.flow_id});
    }

    table coco_preprocessing_table_01{
        actions = {
            coco_preprocessing_1;
        }
        size = 100;
        const default_action = coco_preprocessing_1;
    }

    table coco_preprocessing_table_11{
        actions = {
            coco_preprocessing_1;
        }
        size = 100;
        const default_action = coco_preprocessing_1;
    }

    //elastic 04
    Register<b32_bucket_len_t, bucket_index_len_t>(BUCKET_SIZE) total_vote_04;
    RegisterAction<b32_bucket_len_t, bucket_index_len_t, b32_bucket_len_t>(total_vote_04) total_vote_salu_04 = {
        void apply(inout b32_bucket_len_t reg_data, out b32_bucket_len_t out_data) {
            reg_data = reg_data + 1;
            out_data = reg_data;
        }
    };

    action total_vote_action_04() {
        hdr.meta.totVotes = total_vote_salu_04.execute(hdr.meta.index_4);
        hdr.meta.register_id = 0;
    }

    //@stage(1)
    table total_vote_table_04 {
        actions = {
            total_vote_action_04;
        }
        size = 100;
        const default_action = total_vote_action_04;
    }

    Register<b64_bucket_t, bucket_index_len_t>(BUCKET_SIZE) freq_vote_04;
    RegisterAction<b64_bucket_t, bucket_index_len_t, b32_bucket_len_t>(freq_vote_04) freq_vote_salu_04 = {
        void apply(inout b64_bucket_t reg_data, out b32_bucket_len_t out_data) {
                if(hdr.meta.totVotes >= reg_data.hi || hdr.myflow.id == reg_data.lo) {
                    out_data = reg_data.lo;
                    reg_data.lo = hdr.myflow.id;
                    reg_data.hi = reg_data.hi + LAMBDA;
                }
                else {
                    out_data = 0;
                }
        }
    };

    action freq_vote_action_04() {
        hdr.meta.register_id = freq_vote_salu_04.execute(hdr.meta.index_4);
    }

    //@stage(2)
    table freq_vote_table_04 {
        actions = {
            freq_vote_action_04;
        }
        size = 100;
        const default_action = freq_vote_action_04;
    }

    //2023-9-13 add
    RegisterAction<b64_bucket_t, bucket_index_len_t, b32_bucket_len_t>(freq_vote_04) read_counter_freq_vote_salu_04 = {
        void apply(inout b64_bucket_t reg_data, out b32_bucket_len_t out_data) {
            out_data = reg_data.hi;
        }
    };

    RegisterAction<b64_bucket_t, bucket_index_len_t, b32_bucket_len_t>(freq_vote_04) read_id_freq_vote_salu_04 = {
        void apply(inout b64_bucket_t reg_data, out b32_bucket_len_t out_data) {
            out_data = reg_data.lo;
        }
    };

    action read_counter_freq_vote_action_04() {
        hdr.data.data = read_counter_freq_vote_salu_04.execute(hdr.info.bgn_index);
	hdr.info.bgn_index = hdr.info.bgn_index+1;
    }

    action read_id_freq_vote_action_04() {
        hdr.data.data = read_id_freq_vote_salu_04.execute(hdr.info.bgn_index);
	hdr.info.bgn_index = hdr.info.bgn_index+1;
    }

    table read_freq_vote_table_04 {
        key = {
            hdr.info.read_flag: exact;
        }
        actions = {
            read_counter_freq_vote_action_04;
            read_id_freq_vote_action_04;
            NoAction;
        }
        size = 2;
        const default_action = NoAction;
        const entries = {
            11: read_counter_freq_vote_action_04();
            10: read_id_freq_vote_action_04();
        }
    }

    //@stage(3)
    table drop_flow_table_04 {
        actions = {
            drop_flow_action;
        }
        size = 100;
        const default_action = drop_flow_action;
    }

    Register<b32_bucket_len_t, bucket_index_len_t>(BUCKET_SIZE) freq_vote_copy_04;
    RegisterAction<b32_bucket_len_t, bucket_index_len_t, b32_bucket_len_t>(freq_vote_copy_04) freq_vote_copy_salu_04 = {
        void apply(inout b32_bucket_len_t reg_data, out b32_bucket_len_t out_data) {
            reg_data = reg_data + LAMBDA;
            out_data = reg_data;
        }
    };

    action freq_vote_copy_action_04() {
        hdr.meta.counter_val = freq_vote_copy_salu_04.execute(hdr.meta.index_4);
    }

    table freq_vote_copy_table_04 {
        actions = {
            freq_vote_copy_action_04;
        }
        size = 100;
        const default_action = freq_vote_copy_action_04;
    }

    //@stage(3)
    table update_flow_table_04 {
        actions = {
            update_flow_action;
        }
        size = 100;
        const default_action = update_flow_action;
    }

    // action freq_div_01() {
    //     hdr.meta.totVotes = hdr.meta.totVotes >> LAMBDA_SHIFT;
    // }

    // //@stage(4)
    // table freq_div_table_01 {
    //     actions = {
    //         freq_div_01;
    //     }
    //     size = 100;
    //     const default_action = freq_div_01;
    // }

    //coco

	Random<bit<16>>() random_generator_01;


    Register<b32_bucket_len_t, bucket_index_len_t>(BUCKET_SIZE) coco_counter_01;
    RegisterAction<b32_bucket_len_t, bucket_index_len_t, b32_bucket_len_t>(coco_counter_01) coco_counter_salu_01 = {
        void apply(inout b32_bucket_len_t reg_data, out b32_bucket_len_t out_data) {
            reg_data = reg_data + hdr.meta.totVotes;
            out_data = reg_data;
        }
    };

    action coco_counter_action_01() {
        meta.count = coco_counter_salu_01.execute(hdr.meta.index_coco);
    }

    //@stage(5)
    table coco_counter_table_01 {
        actions = {
            coco_counter_action_01;
        }
        size = 100;
        const default_action = coco_counter_action_01;
    }

    //2023-9-13 add
    RegisterAction<b32_bucket_len_t, bucket_index_len_t, b32_bucket_len_t>(coco_counter_01) read_counter_coco_salu_01 = {
        void apply(inout b32_bucket_len_t reg_data, out b32_bucket_len_t out_data) {
            out_data = reg_data;
        }
    };

    action read_counter_coco_action_01() {
        hdr.data.data = read_counter_coco_salu_01.execute(hdr.info.bgn_index);
	hdr.info.bgn_index = hdr.info.bgn_index+1;
    }


    table read_counter_coco_table_01 {
        key = {
            hdr.info.read_flag: exact;
        }
        actions = {
            read_counter_coco_action_01;
            NoAction;
        }
        size = 100;
        const default_action = NoAction;
        const entries = {
            15: read_counter_coco_action_01();
        }
    }

	action generate_random_action_01(){
		meta.rng = random_generator_01.get();
	}

    //@stage(5)
	table random_number_table_01{
		actions = {
			generate_random_action_01;
		}
		size = 100;
		const default_action = generate_random_action_01;
	}

    Register<b32_bucket_len_t, bit<1>>(1) num_32_01;
	MathUnit<b32_bucket_len_t>(true,0,9,{68,73,78,85,93,102,113,128,0,0,0,0,0,0,0,0}) prog_64K_div_mu_01;
	RegisterAction<b32_bucket_len_t,bit<1>,b32_bucket_len_t>(num_32_01) prog_64K_div_x_01 = {
		void apply(inout b32_bucket_len_t reg_data, out b32_bucket_len_t mau_value){
			reg_data = prog_64K_div_mu_01.execute(meta.count);
            mau_value = reg_data;
		}
	};

	action calc_cond_pre_01(){
		meta.cond = prog_64K_div_x_01.execute(0);
	}

    //@stage(6)
	table calc_cond_pre_table_01{
		actions = {
			calc_cond_pre_01;
		}
		size = 100;
		const default_action = calc_cond_pre_01;
	}

	action calc_cond_01(){
		meta.cond = (bit<32>)meta.rng - meta.cond;
	}

    //@stage(7)
	table calc_cond_table_01{
		actions = {
			calc_cond_01;
		}
		size = 100;
		const default_action = calc_cond_01;
	}

    Register<b32_bucket_len_t, bucket_index_len_t>(BUCKET_SIZE) coco_id_01;
    RegisterAction<b32_bucket_len_t, bucket_index_len_t, b32_bucket_len_t>(coco_id_01) coco_id_salu_01 = {
        void apply(inout b32_bucket_len_t reg_data, out b32_bucket_len_t out_data) {
            reg_data = hdr.myflow.id;
        }
    };

	action check_id_01(){
		coco_id_salu_01.execute(hdr.meta.index_coco);
	}

    //@stage(8)
	table check_id_table_01{
		actions = {
			check_id_01;
		}
		size = 100;
		const default_action = check_id_01;
	}

    //2023-9-13 add
    RegisterAction<b32_bucket_len_t, bucket_index_len_t, b32_bucket_len_t>(coco_id_01) read_id_coco_salu_01 = {
        void apply(inout b32_bucket_len_t reg_data, out b32_bucket_len_t out_data) {
            out_data = reg_data;
        }
    };

    action read_id_coco_action_01() {
        hdr.data.data = read_id_coco_salu_01.execute(hdr.info.bgn_index);
	hdr.info.bgn_index = hdr.info.bgn_index+1;
    }


    table read_id_coco_table_01 {
        key = {
            hdr.info.read_flag: exact;
        }
        actions = {
            read_id_coco_action_01;
            NoAction;
        }
        size = 100;
        const default_action = NoAction;
        const entries = {
            14: read_id_coco_action_01();
        }
    }

    //elastic 14
    Register<b32_bucket_len_t, bucket_index_len_t>(BUCKET_SIZE) total_vote_14;
    RegisterAction<b32_bucket_len_t, bucket_index_len_t, b32_bucket_len_t>(total_vote_14) total_vote_salu_14 = {
        void apply(inout b32_bucket_len_t reg_data, out b32_bucket_len_t out_data) {
            reg_data = reg_data + 1;
            out_data = reg_data;
        }
    };

    action total_vote_action_14() {
        hdr.meta.totVotes = total_vote_salu_14.execute(hdr.meta.index_4);
        hdr.meta.register_id = 0;
    }

    //@stage(1)
    table total_vote_table_14 {
        actions = {
            total_vote_action_14;
        }
        size = 100;
        const default_action = total_vote_action_14;
    }

    Register<b64_bucket_t, bucket_index_len_t>(BUCKET_SIZE) freq_vote_14;
    RegisterAction<b64_bucket_t, bucket_index_len_t, b32_bucket_len_t>(freq_vote_14) freq_vote_salu_14 = {
        void apply(inout b64_bucket_t reg_data, out b32_bucket_len_t out_data) {
                if(hdr.meta.totVotes >= reg_data.hi || hdr.myflow.id == reg_data.lo) {
                    out_data = reg_data.lo;
                    reg_data.lo = hdr.myflow.id;
                    reg_data.hi = reg_data.hi + LAMBDA;
                }
                else {
                    out_data = 0;
                }
        }
    };

    action freq_vote_action_14() {
        hdr.meta.register_id = freq_vote_salu_14.execute(hdr.meta.index_4);
    }

    //@stage(2)
    table freq_vote_table_14 {
        actions = {
            freq_vote_action_14;
        }
        size = 100;
        const default_action = freq_vote_action_14;
    }

    //2023-9-13 add
    RegisterAction<b64_bucket_t, bucket_index_len_t, b32_bucket_len_t>(freq_vote_14) read_counter_freq_vote_salu_14 = {
        void apply(inout b64_bucket_t reg_data, out b32_bucket_len_t out_data) {
            out_data = reg_data.hi;
        }
    };

    RegisterAction<b64_bucket_t, bucket_index_len_t, b32_bucket_len_t>(freq_vote_14) read_id_freq_vote_salu_14 = {
        void apply(inout b64_bucket_t reg_data, out b32_bucket_len_t out_data) {
            out_data = reg_data.lo;
        }
    };

    action read_counter_freq_vote_action_14() {
        hdr.data.data = read_counter_freq_vote_salu_14.execute(hdr.info.bgn_index);
	hdr.info.bgn_index = hdr.info.bgn_index+1;
    }

    action read_id_freq_vote_action_14() {
        hdr.data.data = read_id_freq_vote_salu_14.execute(hdr.info.bgn_index);
	hdr.info.bgn_index = hdr.info.bgn_index+1;
    }

    table read_freq_vote_table_14 {
        key = {
            hdr.info.read_flag: exact;
        }
        actions = {
            read_counter_freq_vote_action_14;
            read_id_freq_vote_action_14;
            NoAction;
        }
        size = 2;
        const default_action = NoAction;
        const entries = {
            9: read_counter_freq_vote_action_14();
            8: read_id_freq_vote_action_14();
        }
    }

    //@stage(3)
    table drop_flow_table_14 {
        actions = {
            drop_flow_action;
        }
        size = 100;
        const default_action = drop_flow_action;
    }

    Register<b32_bucket_len_t, bucket_index_len_t>(BUCKET_SIZE) freq_vote_copy_14;
    RegisterAction<b32_bucket_len_t, bucket_index_len_t, b32_bucket_len_t>(freq_vote_copy_14) freq_vote_copy_salu_14 = {
        void apply(inout b32_bucket_len_t reg_data, out b32_bucket_len_t out_data) {
            reg_data = reg_data + LAMBDA;
            out_data = reg_data;
        }
    };

    action freq_vote_copy_action_14() {
        hdr.meta.counter_val = freq_vote_copy_salu_14.execute(hdr.meta.index_4);
    }

    table freq_vote_copy_table_14 {
        actions = {
            freq_vote_copy_action_14;
        }
        size = 100;
        const default_action = freq_vote_copy_action_14;
    }

    //@stage(3)
    table update_flow_table_14 {
        actions = {
            update_flow_action;
        }
        size = 100;
        const default_action = update_flow_action;
    }

    // action freq_div_11() {
    //     hdr.meta.totVotes = hdr.meta.totVotes >> LAMBDA_SHIFT;
    // }

    // //@stage(4)
    // table freq_div_table_11 {
    //     actions = {
    //         freq_div_11;
    //     }
    //     size = 100;
    //     const default_action = freq_div_11;
    // }

    //coco
	Random<bit<16>>() random_generator_11;

    Register<b32_bucket_len_t, bucket_index_len_t>(BUCKET_SIZE) coco_counter_11;
    RegisterAction<b32_bucket_len_t, bucket_index_len_t, b32_bucket_len_t>(coco_counter_11) coco_counter_salu_11 = {
        void apply(inout b32_bucket_len_t reg_data, out b32_bucket_len_t out_data) {
            reg_data = reg_data + hdr.meta.totVotes;
            out_data = reg_data;
        }
    };

    action coco_counter_action_11() {
        meta.count = coco_counter_salu_11.execute(hdr.meta.index_coco);
    }

    //@stage(5)
    table coco_counter_table_11 {
        actions = {
            coco_counter_action_11;
        }
        size = 100;
        const default_action = coco_counter_action_11;
    }

    //2023-9-13 add
    RegisterAction<b32_bucket_len_t, bucket_index_len_t, b32_bucket_len_t>(coco_counter_11) read_counter_coco_salu_11 = {
        void apply(inout b32_bucket_len_t reg_data, out b32_bucket_len_t out_data) {
            out_data = reg_data;
        }
    };

    action read_counter_coco_action_11() {
        hdr.data.data = read_counter_coco_salu_11.execute(hdr.info.bgn_index);
	hdr.info.bgn_index = hdr.info.bgn_index+1;
    }


    table read_counter_coco_table_11 {
        key = {
            hdr.info.read_flag: exact;
        }
        actions = {
            read_counter_coco_action_11;
            NoAction;
        }
        size = 100;
        const default_action = NoAction;
        const entries = {
            13: read_counter_coco_action_11();
        }
    }


	action generate_random_action_11(){
		meta.rng = random_generator_11.get();
	}

    //@stage(5)
	table random_number_table_11{
		actions = {
			generate_random_action_11;
		}
		size = 100;
		const default_action = generate_random_action_11;
	}

    Register<b32_bucket_len_t, bit<1>>(1) num_32_11;
	MathUnit<b32_bucket_len_t>(true,0,9,{68,73,78,85,93,102,113,128,0,0,0,0,0,0,0,0}) prog_64K_div_mu_11;
	RegisterAction<b32_bucket_len_t,bit<1>,b32_bucket_len_t>(num_32_11) prog_64K_div_x_11 = {
		void apply(inout b32_bucket_len_t reg_data, out b32_bucket_len_t mau_value){
			reg_data = prog_64K_div_mu_11.execute(meta.count);
            mau_value = reg_data;
		}
	};

	action calc_cond_pre_11(){
		meta.cond = prog_64K_div_x_11.execute(0);
	}

    //@stage(6)
	table calc_cond_pre_table_11{
		actions = {
			calc_cond_pre_11;
		}
		size = 100;
		const default_action = calc_cond_pre_11;
	}

	action calc_cond_11(){
		meta.cond = (bit<32>)meta.rng - meta.cond;
	}

    //@stage(7)
	table calc_cond_table_11{
		actions = {
			calc_cond_11;
		}
		size = 100;
		const default_action = calc_cond_11;
	}

    Register<b32_bucket_len_t, bucket_index_len_t>(BUCKET_SIZE) coco_id_11;
    RegisterAction<b32_bucket_len_t, bucket_index_len_t, b32_bucket_len_t>(coco_id_11) coco_id_salu_11 = {
        void apply(inout b32_bucket_len_t reg_data, out b32_bucket_len_t out_data) {
            reg_data = hdr.myflow.id;
        }
    };

	action check_id_11(){
		coco_id_salu_11.execute(hdr.meta.index_coco);
	}

    //@stage(8)
	table check_id_table_11{
		actions = {
			check_id_11;
		}
		size = 100;
		const default_action = check_id_11;
	}

    //2023-9-13 add
    RegisterAction<b32_bucket_len_t, bucket_index_len_t, b32_bucket_len_t>(coco_id_11) read_id_coco_salu_11 = {
        void apply(inout b32_bucket_len_t reg_data, out b32_bucket_len_t out_data) {
            out_data = reg_data;
        }
    };

    action read_id_coco_action_11() {
        hdr.data.data = read_id_coco_salu_11.execute(hdr.info.bgn_index);
	hdr.info.bgn_index = hdr.info.bgn_index+1;
    }


    table read_id_coco_table_11 {
        key = {
            hdr.info.read_flag: exact;
        }
        actions = {
            read_id_coco_action_11;
            NoAction;
        }
        size = 100;
        const default_action = NoAction;
        const entries = {
            12: read_id_coco_action_11();
        }
    }

    apply {
        if(hdr.udp.isValid()) {
            // hdr.meta.index_coco = hdr.meta.index_1;
            preprocessing_table_4.apply();
            if(hdr.meta.choose_flag == 1) {
                if(hdr.meta.heavy_flag == 1) {
                    total_vote_table_14.apply();
                    freq_vote_table_14.apply();
                    if(hdr.meta.register_id != 0) {
                        if(hdr.meta.register_id == hdr.myflow.id) {
                            drop_flow_table_14.apply();
                        }
                        freq_vote_copy_table_14.apply();
                        update_flow_table_14.apply();
                    }
                }
                // freq_div_table_11.apply();
                //coco
                coco_preprocessing_table_11.apply();
                if(hdr.meta.light_flag == 1) {
                    coco_counter_table_11.apply();
                    random_number_table_11.apply();
                    calc_cond_pre_table_11.apply();
                    calc_cond_table_11.apply();
                    if(meta.cond < 65536){
                        check_id_table_11.apply();
                    }
                }
            }
            else if(hdr.meta.choose_flag == 0) {
                if(hdr.meta.heavy_flag == 1) {
                    total_vote_table_04.apply();
                    freq_vote_table_04.apply();
                    if(hdr.meta.register_id != 0) {
                        if(hdr.meta.register_id == hdr.myflow.id) {
                            drop_flow_table_04.apply();
                        }
                        freq_vote_copy_table_04.apply();
                        update_flow_table_04.apply();
                    }
                }

                // freq_div_table_01.apply();
                //coco
                coco_preprocessing_table_01.apply();
                if(hdr.meta.light_flag == 1) {
                    coco_counter_table_01.apply();
                    random_number_table_01.apply();
                    calc_cond_pre_table_01.apply();
                    calc_cond_table_01.apply();
                    if(meta.cond < 65536){
                        check_id_table_01.apply();
                    }
                }
            }

        hdr.myflow.setInvalid();
        hdr.meta.setInvalid();
        }
        else if(hdr.info.isValid()){
            if(hdr.info.end_index != hdr.info.bgn_index) {
                read_freq_vote_table_14.apply();
                read_freq_vote_table_04.apply();

                read_counter_coco_table_11.apply();
                read_counter_coco_table_01.apply();
                read_id_coco_table_11.apply();
                read_id_coco_table_01.apply();
            }
        }
    }
}

control EgressDeparser(packet_out pkt,
	inout egress_header_t hdr,
	in egress_metadata_t meta,
	in egress_intrinsic_metadata_for_deparser_t eg_dprsr_md)
{
	apply{
        pkt.emit(hdr);
	}
}


/* main */
Pipeline(IngressParser(),Ingress(),IngressDeparser(),
EgressParser(),Egress(),EgressDeparser()) pipe;

Switch(pipe) main;
