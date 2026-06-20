#!/usr/bin/env python3
"""E1 plot: ALE vs memory — AnoTable vs FlowLens/SketchFeature/DDSketch.
Extends paper Fig.8a by adding the two reviewer-requested data-plane per-flow
distribution baselines (FlowLens, SketchFeature)."""
import csv, sys, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

CSV = sys.argv[1] if len(sys.argv) > 1 else "../results/E1_ale_vs_mem.csv"
OUT = sys.argv[2] if len(sys.argv) > 2 else "../plots/E1_ale_vs_mem.pdf"

mem, cols = [], {"AnoTable": [], "FlowLens": [], "SketchFeature": [], "DDSketch": []}
with open(CSV) as f:
    r = csv.DictReader(f)
    for row in r:
        mem.append(float(row["memKB"]))
        for k in cols: cols[k].append(float(row[k]))

style = {
    "AnoTable":      dict(marker="o", color="#d62728", lw=2, label="AnoTable (ours)"),
    "FlowLens":      dict(marker="s", color="#1f77b4", lw=2, label="FlowLens"),
    "SketchFeature": dict(marker="^", color="#2ca02c", lw=2, label="SketchFeature"),
    "DDSketch":      dict(marker="v", color="#9467bd", lw=2, label="DDSketch"),
}
plt.figure(figsize=(4.2, 3.0))
for k in ["AnoTable", "FlowLens", "SketchFeature", "DDSketch"]:
    plt.plot(mem, cols[k], **style[k])
plt.xlabel("Memory (KB)")
plt.ylabel("ALE")
plt.legend(fontsize=8, ncol=1)
plt.grid(True, ls=":", alpha=0.5)
plt.tight_layout()
os.makedirs(os.path.dirname(OUT), exist_ok=True)
plt.savefig(OUT)
print("wrote", OUT)
# also drop a copy into the Overleaf pictures dir for direct \includegraphics
overleaf = "/data/jjc/AnoMon/AnoMon_TON25_Overleaf/pictures/E1_ale_vs_mem.pdf"
try:
    plt.savefig(overleaf); print("wrote", overleaf)
except Exception as e:
    print("overleaf copy skipped:", e)
