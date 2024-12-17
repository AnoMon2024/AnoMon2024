# Codes of AnoTable


- We emulate and test the performance of our AnoTable using CAIDA2018 dataset.


## File Descriptions

- ``packet_interval_distribution`` contains the codes to calculate Average Absolute Error on top-k flow packet inter-arrival time estimation of AnoTable.
- `comparison` contains the codes to compare AnoTable with DDSketch, KLL Sketch and GK Sketch.

## Run

For AnoTable:

- Replace `filename` in `trace.h` with the path of your data. 
- Set the constant `MEMORY` in main.cpp to the memory usage of AnoTable.
- Run the following command.

```bash
$ make
$ ./main
```

For DD, KLL and GK:

- Replace `path_caida` in `main_[algo_name].cpp` with the path of your data. 
- Build:

```bash
$ cmake .
$ make
```

- For DDSketch, if you want to assign the total memory as 8000:

```
./main 8000
```

- For GK sketch, if you want to assign the total memory as 8000 and epsilon as 0.01:

```
./main 8000 0.01
```

- For KLL Sketch, if you want to assign the total memory as 8000 and K as 200:

```
./main 8000 200
```

For HistSketch:
- Go to ``HistSketch-master/interval_in_sketch``
- Change the memory in ``/common/parameters.h``
- run `bash initial.sh` and `bash run_lat.sh`