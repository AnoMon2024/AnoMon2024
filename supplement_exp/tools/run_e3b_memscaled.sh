#!/bin/bash
# E3b (R2-2): localization F1 vs flow scale when per-switch memory is provisioned
# proportionally to the abnormal-flow count (mem ∝ n_flows). AnoMon's claim is that
# overhead/accuracy scales with ABNORMAL (not total) flows; this variant should keep
# localization F1 ~stable as total flows grow, in contrast to the fixed-memory E3a
# where F1 degrades. blackhole(PD), test=0 (flow localization).
set -u
source /home/jjc/miniconda3/etc/profile.d/conda.sh && conda activate AnoMon
cd "$(dirname "$0")/../src/anomon/sim/workplace/simu"
OUT=/data/jjc/AnoMon/AnoMon2024/supplement_exp/results/E3b_memscaled.csv
LOG=/data/jjc/AnoMon/AnoMon2024/supplement_exp/logs/E3b_memscaled.log
ALL_TIME=40
EPOCH=10
echo "=== E3b mem-scaled sweep start $(date +%T) ===" > "$LOG"
# (n_flows, mem) with mem proportional to n_flows (base 100 @ 25k)
for pair in "25000 100" "50000 200" "100000 400" "200000 800"; do
  set -- $pair; NF=$1; MEM=$2
  echo ">>> n_flows=$NF mem=$MEM $(date +%T)" >> "$LOG"
  python3 fattree.py --culprit_typ 0 --mem $MEM --algo dleft --error_ratio 0.5 \
    --window 0.1 --err_flow_ratio 0.25 --flow_group_typ path --test 0 \
    --n_flows $NF --epoch $EPOCH --all_time $ALL_TIME \
    --outcsv "$OUT" --tag "memscaled_nf${NF}_mem${MEM}" >> "$LOG" 2>&1
  echo "    -> exit $? $(date +%T)" >> "$LOG"
done
echo "=== E3b done $(date +%T) ===" >> "$LOG"
