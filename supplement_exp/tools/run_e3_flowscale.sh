#!/bin/bash
# E3 flow-scale sweep (R2-2): does AnoMon still detect/localize anomalies as the
# number of flows grows? FatTree k=4, blackhole(PD-AFG), AFG-detection F1 (test=2)
# and flow-localization F1 (test=0). Runs are slow (~13s/sim-time-unit), so this
# script runs them sequentially in the background and appends rows to one CSV.
set -u
source /home/jjc/miniconda3/etc/profile.d/conda.sh && conda activate AnoMon
cd "$(dirname "$0")/../src/anomon/sim/workplace/simu"
OUT=/data/jjc/AnoMon/AnoMon2024/supplement_exp/results/E3_flowscale.csv
LOG=/data/jjc/AnoMon/AnoMon2024/supplement_exp/logs/E3_flowscale.log
ALL_TIME=30
EPOCH=10
echo "=== E3 flow-scale sweep start ===" > "$LOG"
for NF in 25000 50000 100000 200000; do
  for TEST in 2 0; do   # 2=AFG detection F1, 0=flow localization F1
    echo ">>> n_flows=$NF test=$TEST $(date +%T)" >> "$LOG"
    python3 fattree.py --culprit_typ 0 --mem 100 --algo dleft --error_ratio 0.5 \
      --window 0.1 --err_flow_ratio 0.25 --flow_group_typ path --test $TEST \
      --n_flows $NF --epoch $EPOCH --all_time $ALL_TIME \
      --outcsv "$OUT" --tag "flowscale_nf${NF}_test${TEST}" >> "$LOG" 2>&1
    echo "    -> exit $? $(date +%T)" >> "$LOG"
  done
done
echo "=== E3 flow-scale sweep done ===" >> "$LOG"
