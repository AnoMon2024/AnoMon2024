# Control Plane Implementation

This folder contain the codes for network core swtich.  ``CellSketch_controller.cpp`` is the control plane code.

## Requirements

- Please compile and run the codes on a Tofino ASIC.
- We can compile the cpp code in SDE 9.9.0.
- use CMakeLists.txt in path $SDE/pkgsrc/bf-drivers/bf-switchd/bfrt-examples to complete compile work
- Step to run :
```
   -cd $SDE/pkgsrc/bf-drivers/bf-switchd/bfrt-example
   -mkdir -p build
   -cmake..
   -cmake --build . --target install
   -sudo env "SDE=$SDE" "SDE_INSTALL=$SDE_INSTALL" "PATH=$PATH" "LD_LIBRARY_PATH=/usr/local/lib:$SDE_INSTALL/lib:$LD_LIBRARY_PATH"
   -./CellSketch_controller_example --install-dir $SDE_INSTALL --conf-file$SDE_INSTALL/share/p4/targets/tofino/CellSketch.conf (need to complie CellSketch.p4 first)
```

- We send packets to read data plane sketches
   - every packet use payload to storage sketches' data fields
   - when begin index is not equal to end index, packet will loopback in data plane and continue read
   - after one loopback turn, the begin index will plus 1
   - when begin index is equal to end index, packet will be send back to control plane by port 192
   - control plane sends packets and collects packets
