# P4 Implementation

The codes for network core. `CellSketch.p4` is the data plane code. `switchcontrol.py` is the control plane code. `switchtable.py` is the code to set p4 tables.

## Requirements

- Please compile and run the codes on a Tofino ASIC.
- We can compile the p4 code in SDE 9.6.0 or 9.7.0.

## Usage

- Set the forward tables at the beginning of `switchtable.py`.
- compile and run `CellSketch.p4`.
- start `switchcontrol.py.`.

