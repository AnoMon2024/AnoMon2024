import csv, os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
feats,f1=[],[]
with open("../results/E4_ablation_0.08.csv") as f:
    for r in csv.DictReader(f): feats.append(r["feature"]); f1.append(float(r["bestF1"]))
colors=["#999999","#1f77b4","#ff7f0e","#2ca02c","#9467bd"]
plt.figure(figsize=(4.3,3.0))
bars=plt.bar(feats,f1,color=colors[:len(feats)])
for b,v in zip(bars,f1): plt.text(b.get_x()+b.get_width()/2, v+0.02, f"{v:.2f}", ha="center", fontsize=8)
plt.ylim(0,1.12); plt.ylabel("best F1 (anomalous-flow detection)")
plt.xlabel("per-flow feature used")
plt.axhspan(0,0.55,color="red",alpha=0.05)
plt.grid(True,axis="y",ls=":",alpha=0.5); plt.tight_layout()
for p in ["../plots/E4_ablation.pdf","/data/jjc/AnoMon/AnoMon_TON25_Overleaf/pictures/E4_ablation.pdf"]:
    plt.savefig(p); print("wrote",p)
