#!/bin/bash
# E5 (R3-3): AFG detection F1 vs anomaly duration. error_ratio controls the mean
# anomaly duration = sec_time(=epoch units) * error_ratio, so sweeping it varies
# the anomaly duration relative to the epoch. Short anomalies (< epoch) are harder
# to catch within a measurement window -> lower recall. test=2 (AFG detection).
set -u
source /home/jjc/miniconda3/etc/profile.d/conda.sh && conda activate AnoMon
cd "$(dirname "$0")/../src/anomon/sim/workplace/simu"
OUT=/data/jjc/AnoMon/AnoMon2024/supplement_exp/results/E5_shortlived.csv
LOG=/data/jjc/AnoMon/AnoMon2024/supplement_exp/logs/E5_shortlived.log
echo "=== E5 short-lived sweep $(date +%T) ===" > "$LOG"
rm -f "$OUT"
for ER in 0.05 0.1 0.25 0.5 1.0; do
  echo ">>> error_ratio=$ER $(date +%T)" >> "$LOG"
  python3 fattree.py --culprit_typ 0 --mem 100 --algo dleft --error_ratio $ER \
    --window 0.1 --err_flow_ratio 0.25 --flow_group_typ path --test 2 \
    --n_flows 50000 --epoch 10 --all_time 40 \
    --outcsv "$OUT" --tag "shortlived_er${ER}" >> "$LOG" 2>&1
  echo "    -> exit $? $(date +%T)" >> "$LOG"
done
echo "=== E5 done $(date +%T) ===" >> "$LOG"
