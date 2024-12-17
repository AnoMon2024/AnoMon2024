#include "../../../AnoTable/common/Util.h"
#include <vector>
#include <bits/stdc++.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
namespace py = pybind11;
using namespace std;

class Netseer {
public:
    struct Counter{
        TUPLES ID;
        int count;
    };

    Netseer(){

    }

    Netseer(int _C, uint32_t _memory) {
        C = _C;
        memory = _memory;
        L = memory/ sizeof(Counter);

        counter = new Counter[L];
        memset(counter, 0, sizeof(Counter) * L);
    }
    void clear() {
        memset(counter, 0, sizeof(Counter) * L);
    }
    ~Netseer() {
        delete counter;
    }

    void insert(TUPLES flow_id) {
        int pos = BOBHash(flow_id, 0) % L;
        if (counter[pos].ID.empty()) {
            counter[pos].ID = flow_id;
            counter[pos].count = 1;
        }else if (counter[pos].ID == flow_id) {
            counter[pos].count++;
            if(counter[pos].count > C){
                TUPLES f_id = flow_id;
                vector<uint32_t> id = {f_id.srcIP(),f_id.dstIP(),f_id.srcPort(),f_id.dstPort(),f_id.proto(),counter[pos].count};
                report_flow_id = id;
                //clear
                counter[pos].ID = TUPLES();
                counter[pos].count = 0;
            }
        }else{
            TUPLES f_id = counter[pos].ID;
            vector<uint32_t> id = {f_id.srcIP(),f_id.dstIP(),f_id.srcPort(),f_id.dstPort(),f_id.proto(),counter[pos].count};
            report_flow_id = id;
            counter[pos].ID = flow_id;
            counter[pos].count = 1;
        }
        return;
    }

    void insert_pre(uint32_t src_ip,uint32_t dst_ip,uint16_t src_port,uint16_t dst_port,uint8_t _proto){
        TUPLES item(src_ip,dst_ip,src_port,dst_port,_proto);
        insert(item);
    }

    vector<uint32_t> check_report(){
        vector<uint32_t> ans(6,0);
        if(!report_flow_id.empty()){
            ans = report_flow_id;
        }
        report_flow_id.clear();
        return ans;
    }

    vector<vector<uint32_t>> query_all(){
        vector<vector<uint32_t>> ans;
        for(int i=0;i<L;++i){
            TUPLES f_id = counter[i].ID;
            if(!f_id.empty()){
                vector<uint32_t> tmp = {f_id.srcIP(),f_id.dstIP(),f_id.srcPort(),f_id.dstPort(),f_id.proto(),counter[i].count};;
                ans.push_back(tmp);
            }
        }
        return ans;
    }


private:
    Counter *counter;
    int L, C;
    uint32_t memory;
    vector<uint32_t> report_flow_id;
};

PYBIND11_MODULE(Netseer, m) {
	py::class_<Netseer> netseer(m, "Netseer");
	
    
    netseer.def(py::init<>())
        .def(py::init<int,uint32_t>())
        .def("insert_pre", &Netseer::insert_pre)
        .def("check_report", &Netseer::check_report)
        .def("query_all", &Netseer::query_all);

	// py::class_<TUPLES>(netseer, "TUPLES")
    //     .def(py::init<>())
    //     .def(py::init<uint32_t, uint32_t, uint16_t, uint16_t, uint8_t>())
	// 	.def("srcIP", &TUPLES::srcIP)
	// 	.def("dstIP", &TUPLES::dstIP)
	// 	.def("srcPort", &TUPLES::srcPort)
	// 	.def("dstPort", &TUPLES::dstPort)
	// 	.def("proto", &TUPLES::proto)
	// 	.def("srcIP_dstIP", &TUPLES::srcIP_dstIP)
	// 	.def("srcIP_srcPort", &TUPLES::srcIP_srcPort)
	// 	.def("dstIP_dstPort", &TUPLES::dstIP_dstPort);

}

