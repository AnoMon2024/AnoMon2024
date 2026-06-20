import csv, os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
er,f1=[],[]
with open("../results/E5_shortlived.csv") as f:
    for r in csv.DictReader(f): er.append(float(r["err_flow_ratio"]) if False else float(r["tag"].split("er")[1])); f1.append(float(r["afg_f1"]))
pts=sorted(zip(er,f1)); er=[d for d,_ in pts]; f1=[v for _,v in pts]
plt.figure(figsize=(4.2,3.0))
plt.plot(er,f1,"o-",color="#d62728")
plt.xlabel("anomaly duration (fraction of epoch)"); plt.ylabel("AFG detection F1")
plt.ylim(0,1.05); plt.grid(True,ls=":",alpha=0.5); plt.tight_layout()
plt.savefig("../plots/E5_shortlived.pdf"); print("wrote ../plots/E5_shortlived.pdf (supplement)")
