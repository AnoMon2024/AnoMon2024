#include <bf_rt/bf_rt_info.hpp>
#include <bf_rt/bf_rt_init.hpp>
#include <bf_rt/bf_rt_common.h>
#include <bf_rt/bf_rt_table_key.hpp>
#include <bf_rt/bf_rt_table_data.hpp>
#include <bf_rt/bf_rt_table_operations.hpp>
#include <bf_rt/bf_rt_table.hpp>
#include <getopt.h>
#include<sys/time.h>
#include <unistd.h>
#include <iostream>
#include <fstream>
#include <chrono>
#include <thread>
#include<vector>
#include <arpa/inet.h>
extern "C"
{
    #include <bf_pm/bf_pm_intf.h>
    #include <pkt_mgr/pkt_mgr_intf.h>
    #include <bf_switchd/bf_switchd.h>
}
#define ALL_PIPES 0xffff
#define SWITCH_ID 1

const uint16_t max_array_size = 65535;
const uint16_t bench_size = 256; 
uint64_t flag = 0;
bf_rt_target_t dev_tgt;
std::shared_ptr<bfrt::BfRtSession> session;
struct timeval bgn_tmv,end_tmv;

struct __attribute__((__packed__)) eth_header_t
{
  uint8_t ethdstAddr[6];//6
  uint8_t ethsrcAddr[6];//6
  uint16_t ethtype;//2
};

struct __attribute__((__packed__)) ipv4_header_t
{
  uint8_t version_ihl;
  uint8_t diffserv;
  uint16_t total_len;
  uint16_t ident;
  uint16_t flags;
  uint8_t ttl;
  uint8_t protocol;
  uint16_t checksum;
  uint32_t src_addr;
  uint32_t dst_addr;
};

struct __attribute__((__packed__)) udp_header_t
{
  uint16_t src_port;
  uint16_t dst_port;
  uint16_t total_len;
  uint16_t checksum;
};

struct __attribute__((__packed__)) info_header_t
{
  uint8_t class_flag;
  uint8_t read_flag;
  uint16_t bgn_idx;
  uint16_t end_idx;
  uint16_t zero_zone;
};

typedef struct __attribute__((__packed__)) collect_packet_t
{
    struct eth_header_t eth;
    struct info_header_t info;
} collect_packet;

size_t collect_pkt_sz = sizeof(collect_packet);
bf_pkt_tx_ring_t tx_ring1 = BF_PKT_TX_RING_0;



void send_collect_packet(uint16_t array_size) {
    for(int i = 0; i < 16; i += 2) {
        for(uint16_t bgn_idx = 0; bgn_idx < array_size; bgn_idx += bench_size) {
            bf_pkt *bfpkt = NULL;
            collect_packet pkt{};
            while(1) {
                if(bf_pkt_alloc(0, &bfpkt, collect_pkt_sz, (enum bf_dma_type_e)(17)) == 0) {
                    break;
                }
                else {
                    printf("failed alloc\n");
                }
            }
            uint16_t cur_bgn_idx = htons(bgn_idx);
            uint16_t cur_end_idx = htons(bgn_idx+bench_size);

	    pkt.eth.ethtype = 0xffff;
            pkt.info.bgn_idx = cur_bgn_idx;
            pkt.info.end_idx = cur_end_idx;
            pkt.info.class_flag = 1;
            pkt.info.read_flag = i;

            if(bf_pkt_data_copy(bfpkt, (uint8_t*)&pkt, collect_pkt_sz) != 0) {
                printf("Failed data copy\n");
            }

            bf_status_t stat = bf_pkt_tx(0, bfpkt, (bf_pkt_tx_ring_t)(0), (void *)bfpkt);
            if (stat != BF_SUCCESS) 
            {
                printf("Failed to send packet status = %s\n", bf_err_str(stat));
                bf_pkt_free(0, bfpkt);
            }
        }
    }
}

namespace bfrt
{
    namespace OctopusSketch
    {
        const bfrt::BfRtInfo *bfrtInfo = nullptr;
        void init()
        {   
            dev_tgt.dev_id = 0;
            dev_tgt.pipe_id = ALL_PIPES;
            auto &devMgr = bfrt::BfRtDevMgr::getInstance();
            devMgr.bfRtInfoGet(dev_tgt.dev_id, "OctopusSketch", &bfrtInfo);
        }


    }
}

void init_ports()
{
  system("$SDE_INSTALL/bin/bfshell -f $SDE/port_setup.txt");
  //bf_pm_port_add_all(dev_tgt.dev_id,BF_SPEED_10G,BF_FEC_TYP_NONE);
 // bf_pm_port_enable_all(dev_tgt.dev_id);
  //struct bf_pal_front_port_handle_t port;
  //port.conn_id = 15;
 // port.chnl_id = 2;
 // bf_pm_port_loopback_mode_set(dev_tgt.dev_id,&port,BF_LPBK_MAC_NEAR);
}

void init_tables()
{
    // system("pwd");
    // system("./bfshell -b /mnt/onl/data/Hierarchical_Fermat/tableinit.py");
}

static bf_status_t switch_pktdriver_tx_complete(bf_dev_id_t device,
                                                bf_pkt_tx_ring_t tx_ring,
                                                uint64_t tx_cookie,
                                                uint32_t status) {

  bf_pkt *pkt = (bf_pkt *)(uintptr_t)tx_cookie;
  (void)device;
  (void)tx_ring;
  (void)tx_cookie;
  (void)status;
  bf_pkt_free(device, pkt);
  return 0;
}

bf_status_t rx_packet_callback (bf_dev_id_t dev_id,
                                bf_pkt *pkt,
                                void *cookie,
                                bf_pkt_rx_ring_t rx_ring) {
    (void)dev_id;
    (void)cookie;
    (void)rx_ring;
    //printf("Packet received..\n");
    uint32_t data[bench_size] = {};
    uint8_t * pkt_info = (uint8_t *)pkt->pkt_data+sizeof(eth_header_t);
    if((*((uint16_t*)((uint8_t*)pkt->pkt_data+12))) == 0xffff) {
    	//printf("a CPU loopback packet, read %u %u\n", *(pkt->pkt_data+12),*(pkt->pkt_data+13));
    }
    else {
    	bf_pkt_free(0,pkt);
    	return 0;
    }
    //memcpy(data, (uint8_t*)pkt->pkt_data+sizeof(collect_packet), bench_size);
    bf_pkt_free(0,pkt);
     //read
    gettimeofday(&end_tmv, NULL);

    uint64_t diff_ts = (end_tmv.tv_sec-bgn_tmv.tv_sec)*1000000+(end_tmv.tv_usec-bgn_tmv.tv_usec);

    printf( " spend time: %llu\n",diff_ts);
    return 0;
}

void switch_pktdriver_callback_register(bf_dev_id_t device) {

    bf_pkt_tx_ring_t tx_ring;
    bf_pkt_rx_ring_t rx_ring;
    bf_status_t status;
    int cookie;
    /* register callback for TX complete */
    for (tx_ring = BF_PKT_TX_RING_0; tx_ring < BF_PKT_TX_RING_MAX; tx_ring = (bf_pkt_tx_ring_t)(tx_ring + 1)) {
        bf_pkt_tx_done_notif_register(device, switch_pktdriver_tx_complete, tx_ring);
    }
    /* register callback for RX */
    for (rx_ring = BF_PKT_RX_RING_0; rx_ring < BF_PKT_RX_RING_MAX; rx_ring = (bf_pkt_rx_ring_t)(rx_ring + 1)) {
        status = bf_pkt_rx_register(device, rx_packet_callback, rx_ring, (void *) &cookie);
    }
    printf("rx register done. stat = %d\n", status);
}

static void parse_options(bf_switchd_context_t *switchd_ctx,
                          int argc,
                          char **argv) {
  int option_index = 0;
  enum opts {
    OPT_INSTALLDIR = 1,
    OPT_CONFFILE,
  };
  static struct option options[] = {
      {"help", no_argument, 0, 'h'},
      {"install-dir", required_argument, 0, OPT_INSTALLDIR},
      {"conf-file", required_argument, 0, OPT_CONFFILE}};

  while (1) {
    int c = getopt_long(argc, argv, "h", options, &option_index);

    if (c == -1) {
      break;
    }
    switch (c) {
      case OPT_INSTALLDIR:
        switchd_ctx->install_dir = strdup(optarg);
        printf("Install Dir: %s\n", switchd_ctx->install_dir);
        break;
      case OPT_CONFFILE:
        switchd_ctx->conf_file = strdup(optarg);
        printf("Conf-file : %s\n", switchd_ctx->conf_file);
        break;
      break;

      case 'h':
      case '?':
        printf("bfrt_perf \n");
        printf(
            "Usage : bfrt_perf --install-dir <path to where the SDE is "
            "installed> --conf-file <full path to the conf file "
            "(bfrt_perf.conf)\n");
        exit(c == 'h' ? 0 : 1);
        break;
      default:
        printf("Invalid option\n");
        exit(0);
        break;
    }
  }
  if (switchd_ctx->install_dir == NULL) {
    printf("ERROR : --install-dir must be specified\n");
    exit(0);
  }

  if (switchd_ctx->conf_file == NULL) {
    printf("ERROR : --conf-file must be specified\n");
    exit(0);
  }
}

int main(int argc, char **argv) {
    bf_switchd_context_t *switchd_ctx;
    if ((switchd_ctx = (bf_switchd_context_t *)calloc(1, sizeof(bf_switchd_context_t))) == NULL) {
        printf("Cannot Allocate switchd context\n");
        exit(1);
    }
    parse_options(switchd_ctx, argc, argv);
    switchd_ctx->running_in_background = true;
    bf_status_t status = bf_switchd_lib_init(switchd_ctx);
    init_ports();
    init_tables();
    switch_pktdriver_callback_register(0);
    bfrt::OctopusSketch::init();


    for(int i = 0; i < 8; ++i) {
	std::cout << "begin send packets, turn " << i << std::endl;
        gettimeofday(&bgn_tmv, NULL);
        
        send_collect_packet(256<<i);
	
        gettimeofday(&end_tmv, NULL);
	uint64_t diff_ts = (end_tmv.tv_sec-bgn_tmv.tv_sec)*1000000+(end_tmv.tv_usec-bgn_tmv.tv_usec);

    	std::cout << "send packet spend time: " << diff_ts << std::endl;

	std::cout << "sleep 15s, wait for rx packets, num: " << (256<<i)*8 << std::endl;
        usleep(5000000);
    }
    return status;
}
