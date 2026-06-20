#!/usr/bin/env python3
"""E7 (R1-6): ALE vs geometric ratio alpha (alpha=1 is uniform binning).
Shows geometric binning with alpha=2 minimizes the error on skewed interval data."""
import csv, os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

CSV="../results/E7_alpha.csv"
data={}  # mem -> list of (alpha, ALE)
with open(CSV) as f:
    for r in csv.DictReader(f):
        data.setdefault(int(r["memKB"]),[]).append((float(r["alpha"]),float(r["ALE"])))
plt.figure(figsize=(4.3,3.0))
marks={50:"o-",100:"s-",200:"^-"}
for mem in sorted(data):
    pts=sorted(data[mem]); xs=[a for a,_ in pts]; ys=[e for _,e in pts]
    plt.plot(range(len(xs)), ys, marks.get(mem,"o-"), label=f"{mem} KB")
    labels=[("uniform" if a==1.0 else f"{a:g}") for a in xs]
plt.xticks(range(len(labels)), labels)
plt.xlabel(r"geometric ratio $\alpha$")
plt.ylabel("ALE")
plt.legend(fontsize=8, title="memory")
plt.grid(True, ls=":", alpha=0.5)
plt.tight_layout()
out="../plots/E7_alpha.pdf"; os.makedirs(os.path.dirname(out),exist_ok=True)
for p in [out, "/data/jjc/AnoMon/AnoMon_TON25_Overleaf/pictures/E7_alpha.pdf"]:
    try: plt.savefig(p); print("wrote",p)
    except Exception as e: print("skip",p,e)
