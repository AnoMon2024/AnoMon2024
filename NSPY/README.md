# Codes for NS.PY Simulations


## Reference
Our implementation of simulation is based on ns.py (https://github.com/TL-System/ns.py), which is a pythonic discrete-event network simulator. It can be used to connect multiple networking components together easily, including packet generators, network links, switch elements, schedulers, traffic shapers, traffic monitors, and demultiplexing elements.

## File Descriptions

- `ns.py-main` contains the ns.py package for simulation.
- `AnoTable` contains the codes of AnoSketch and AnoTable.
- `workplace` contains the main program and parameter settings for simulation.

## Usage
### Basic Setups
##### ns.py Setups
- Go to `./ns.py-main`
- Type `python setup.py install` to build ns.py environment


##### pybind Setups
- Go to `./` folder.
- Type `pip install pybind11-2.10.0-py3-none-any.whl` to install pybind

### More functions and tools

- Generate errors using `./workplace/utils/create_error.py`.
- Generate DCTCP distribution using `./workplace/utils/TCP_distribution.py`. 

### Network Components
- You can find all the components in `./ns.py-main/ns`, including the definition of packet and flow, realization of all parts of the switch and the algorithm of generating paths for all flows.

### C algorithm
- You can find the realization of our sketch algorithm as well as two comparison algorithm in `./AnoTable`.
- The C class used for pybind is in `./workplace/C`, you can change per-switch memory and the size of fattree here.

### Simulation Params
The following are the explainations of main params used in simu.sh
- '-- culprit_typ' : 0 for black hole error, 1 for loop error, 2 for jitter error, 3 for inflated latency error.
- '-- algo' : decide which algroithm to use, dleft, sumax or marple.
- '-- error_ratio' : the average culprit time is 10*error_ratio.
- '-- window' : the average length of culprit window is 10*window.
- '-- err_flow_ratio' : k*k*err_flow_ratio decide the number of culprit flow groups.
- '-- flow_group_num' : you can set this param to any number but zero to limit the number of flow groups.
- '-- heavy_change' : if you want to test heavy change, you can set this param to any number but zero to decide the frequency threshold.
- '-- test_ns' : if you want to test netseer, set this value to 1.

### Error Rate
- You can change the error rate by setting 'self.err_rate' in `./ns.py-main/ns/demux/fib_demux.py` from 0 to 1.

### Running Simulations
- Go to `./workplace/simu` folder.
- Type `bash c.sh` to bind the AnoMon implemented in C++ to the simulation implemented in Python
- Type `bash simu.sh` to run the simulation

### Results
- The output file of simulation results are in `./workplace/res`

The output of the simulation is the accuracy of anomaly location and AFG detection.
