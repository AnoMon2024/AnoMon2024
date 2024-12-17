# Codes for Testbed Experiments 

We have fully implemented AnoMon in a testbed built with 10 Edgecore Wedge 100BF-32X switches (with Tofino ASIC) and 8 end-hosts in a FatTree topology. On the programmable data plane of networkedge/inside-network switch, we implement our two key algorithms (AnoSketch and AnoTable) and the other logic(marking packets, splitting time epochs, etc.) using P4. Both sketches are implemented in a fully pipelined manner without using the mirror and recirculate mechanism. On the central analyzer, we implement the modules of sketch collection, sketch analysis (AFG identification, querying per-flow distribution, etc.), and sending reconfiguration packets in a DPDK framework. We describe specific system implementation details in Appendix C, where we also show that both sketches achieve low hardware resource usage.


## File Description

We provide two sets of codes of AnoMon implemented on our testbed. 

- `testbed_code_py` contains the codes in which the sketch collection and analysis modules are implemented using Python scripts. These codes can be used to conduct the experiments verifying the correctness and accuracy of our system. However, the process of using Python scripts to collect the sketches from data plane is very slow. Therefore, we provide another set of codes in which we implement the skectch collection modules using C++. 

- `testbed_code_cpp` contains the codes in which the sketch collection module is implemented using C++. We use the techniques of sending tailored packets to read the sketches from data plane, and then send the collected sketches to the central analyzer. These codes can be used to evluate the efficiency of our system. 

More implementation details can be found in Section 7 and Appendix C of our paper. 