import csv, os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
fl,f1=[],[]
with open("../results/E9_synflood_intensity.csv") as f:
    for r in csv.DictReader(f): fl.append(int(r["flood"])); f1.append(float(r["F1"]))
plt.figure(figsize=(4.2,3.0))
plt.plot(fl,f1,"o-",color="#d62728")
plt.xscale("log"); plt.ylim(-0.05,1.08)
plt.xlabel("SYN-flood intensity (SYNs per victim /24)"); plt.ylabel("AFG detection F1")
plt.grid(True,ls=":",alpha=0.5); plt.tight_layout()
for p in ["../plots/E9_synflood.pdf","/data/jjc/AnoMon/AnoMon_TON25_Overleaf/pictures/E9_synflood.pdf"]:
    plt.savefig(p); print("wrote",p)
