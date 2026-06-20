#!/bin/bash
# E8 (R3-1): AFG candidate-dimension ablation. Anomalies are injected at
# path-midpoint switches, so the path dimension should localize the abnormal
# group better than the source-subnet dimension; if a single fixed dimension is
# insufficient, the analyzer benefits from generating candidate groups along
# multiple dimensions (the dynamic candidate generation of S VI-B). We compare
# AFG detection F1 under subnet vs path grouping. test=2 (AFG detection).
set -u
source /home/jjc/miniconda3/etc/profile.d/conda.sh && conda activate AnoMon
cd "$(dirname "$0")/../src/anomon/sim/workplace/simu"
OUT=/data/jjc/AnoMon/AnoMon2024/supplement_exp/results/E8_grouping.csv
LOG=/data/jjc/AnoMon/AnoMon2024/supplement_exp/logs/E8_grouping.log
echo "=== E8 grouping ablation $(date +%T) ===" > "$LOG"
rm -f "$OUT"
for FG in subnet path; do
  echo ">>> flow_group_typ=$FG $(date +%T)" >> "$LOG"
  python3 fattree.py --culprit_typ 0 --mem 100 --algo dleft --error_ratio 0.5 \
    --window 0.1 --err_flow_ratio 0.25 --flow_group_typ $FG --test 2 \
    --n_flows 50000 --epoch 10 --all_time 40 \
    --outcsv "$OUT" --tag "grouping_${FG}" >> "$LOG" 2>&1
  echo "    -> exit $? $(date +%T)" >> "$LOG"
done
echo "=== E8 done $(date +%T) ===" >> "$LOG"
