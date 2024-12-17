# Codes of AnoSketch


- We emulate and test the performance of our AnoSketch using CAIDA2018 dataset.


## File Descriptions

- ``heavy_hitter`` contains the codes to calculate RR,PR,F1 Score,ARE of the heavy hitter detection of AnoSketch with different number of partial keys. 
	
- ``heavy_change`` contains the codes to calculate RR,PR,F1 Score,ARE of the heavy change detection of AnoSketch with different number of partial keys. 

- ``packet_interval_distribution`` contains the codes to calculate WMRE of packet inter-arrival time of AnoSketch with different number of partial keys. 

## How to Run

- Replace `filename` in `trace.h` with the path of your data. 
- Run the following command.

```bash
$ make
$ ./main
```

