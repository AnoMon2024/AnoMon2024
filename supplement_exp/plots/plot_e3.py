#!/usr/bin/env python3
"""E3 (R2-2): F1 vs number of flows at fixed per-switch memory.
Shows AFG detection (edge gating) is robust to flow scale, while flow
localization at FIXED memory degrades (AnoTable must be provisioned per
abnormal flow -- consistent with the memory sweep in Fig.10)."""
import csv, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

CSV = "../results/E3_flowscale.csv"
afg, loc = {}, {}
with open(CSV) as f:
    for row in csv.DictReader(f):
        nf = int(row["n_flows"]); t = int(row["test"])
        if t == 2: afg[nf] = float(row["afg_f1"])
        if t == 0: loc[nf] = float(row["loc_f1"])

xs = sorted(set(afg))
plt.figure(figsize=(4.3, 3.0))
plt.plot(xs, [afg.get(x, float("nan")) for x in xs], "o-", color="#d62728",
         label="AFG detection F1")
plt.xscale("log")
plt.xticks(xs, [f"{x//1000}K" for x in xs])
plt.ylim(0, 1.05)
plt.xlabel("# flows (fixed per-switch memory)")
plt.ylabel("AFG detection F1")
plt.legend(fontsize=8, loc="lower left")
plt.grid(True, ls=":", alpha=0.5)
plt.tight_layout()
out = "../plots/E3_flowscale.pdf"
os.makedirs(os.path.dirname(out), exist_ok=True)
plt.savefig(out)
for p in [out, "/data/jjc/AnoMon/AnoMon_TON25_Overleaf/pictures/E3_flowscale.pdf"]:
    try: plt.savefig(p); print("wrote", p)
    except Exception as e: print("skip", p, e)
print("AFG:", afg); print("LOC:", loc)
