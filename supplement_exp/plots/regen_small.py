#!/usr/bin/env python3
"""Regenerate the 6 new evaluation plots at sub-figure size (three per row in a
two-column figure*), with consistent fonts and no tick-label overlap.
Fixes: (1) E3 x-axis label overlap (categorical positions instead of log scale);
(2) uniform compact sizing so figures no longer each occupy a full column."""
import csv, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams.update({
    "font.size": 9, "axes.labelsize": 9, "legend.fontsize": 7.5,
    "xtick.labelsize": 8, "ytick.labelsize": 8, "pdf.fonttype": 42,
})
FIGSIZE = (2.55, 1.95)
OUT = ["../plots", "/data/jjc/AnoMon/AnoMon_TON25_Overleaf/pictures"]
R = "../results"

def save(name):
    plt.tight_layout(pad=0.3)
    for d in OUT:
        plt.savefig(os.path.join(d, name))
    plt.close()
    print("wrote", name)

def rows(f):
    with open(os.path.join(R, f)) as fh:
        return list(csv.DictReader(fh))

# ---------- E1: ALE vs memory ----------
d = rows("E1_ale_vs_mem.csv")
mem = [float(r["memKB"]) for r in d]
st = {"AnoTable": ("o", "#d62728", "AnoTable (ours)"),
      "FlowLens": ("s", "#1f77b4", "FlowLens"),
      "SketchFeature": ("^", "#2ca02c", "SketchFeature"),
      "DDSketch": ("v", "#9467bd", "DDSketch")}
plt.figure(figsize=FIGSIZE)
for k, (m, c, lb) in st.items():
    plt.plot(mem, [float(r[k]) for r in d], marker=m, color=c, lw=1.4, ms=4, label=lb)
plt.xlabel("Memory (KB)"); plt.ylabel("ALE")
plt.legend(ncol=1, handlelength=1.4, labelspacing=0.2, borderpad=0.25)
plt.grid(True, ls=":", alpha=0.5)
save("E1_ale_vs_mem.pdf")

# ---------- E7: ALE vs alpha ----------
d = rows("E7_alpha.csv")
bymem = {}
for r in d:
    bymem.setdefault(int(r["memKB"]), []).append((float(r["alpha"]), float(r["ALE"])))
plt.figure(figsize=FIGSIZE)
marks = {50: "o-", 100: "s-", 200: "^-"}
for memk in sorted(bymem):
    pts = sorted(bymem[memk]); xs = [a for a, _ in pts]; ys = [e for _, e in pts]
    plt.plot(range(len(xs)), ys, marks.get(memk, "o-"), lw=1.4, ms=4, label=f"{memk} KB")
labels = [("unif." if a == 1.0 else f"{a:g}") for a in xs]
plt.xticks(range(len(labels)), labels)
plt.xlabel(r"geometric ratio $\alpha$"); plt.ylabel("ALE")
plt.legend(title="memory", handlelength=1.4, labelspacing=0.2, borderpad=0.25, title_fontsize=7.5)
plt.grid(True, ls=":", alpha=0.5)
save("E7_alpha.pdf")

# ---------- E4: ablation bars ----------
d = rows("E4_ablation_0.08.csv")
feats = [r["feature"] for r in d]; f1 = [float(r["bestF1"]) for r in d]
colors = ["#999999", "#1f77b4", "#ff7f0e", "#2ca02c", "#9467bd"]
plt.figure(figsize=FIGSIZE)
bars = plt.bar(feats, f1, color=colors[:len(feats)], width=0.62)
for b, v in zip(bars, f1):
    plt.text(b.get_x() + b.get_width() / 2, v + 0.02, f"{v:.2f}", ha="center", fontsize=7)
plt.ylim(0, 1.14); plt.ylabel("best F1"); plt.xlabel("per-flow feature")
plt.grid(True, axis="y", ls=":", alpha=0.5)
save("E4_ablation.pdf")

# ---------- E2a: control-plane scalability ----------
d = rows("E2a_control_overhead.csv")
sw = [int(r["switches"]) for r in d]
tseq = [float(r["T_seq_ms"]) / 1000 for r in d]
tlay = [float(r["T_layer_ms"]) / 1000 for r in d]
ep = float(d[0]["epoch_s"])
plt.figure(figsize=FIGSIZE)
x = range(len(sw))
plt.plot(x, tseq, "o-", color="#d62728", lw=1.4, ms=4, label="sequential")
plt.plot(x, tlay, "s-", color="#1f77b4", lw=1.4, ms=4, label="layer-by-layer")
plt.axhline(ep, ls="--", color="gray", lw=1, label=f"epoch={ep:g}s")
plt.xticks(x, [str(s) for s in sw])
plt.yscale("log")
plt.xlabel("# switches"); plt.ylabel("collect+analyze (s)")
plt.legend(handlelength=1.4, labelspacing=0.2, borderpad=0.25)
plt.grid(True, ls=":", alpha=0.5)
save("E2a_control_overhead.pdf")

# ---------- E2b: CFS coverage ----------
d = rows("E2b_cfs.csv")
cs = [int(r["cells"]) for r in d]
plt.figure(figsize=FIGSIZE)
x = range(len(cs))
plt.plot(x, [float(r["Optimal"]) for r in d], "k--", lw=1.2, label="Optimal")
plt.plot(x, [float(r["CFS"]) for r in d], "o-", color="#d62728", lw=1.4, ms=4, label="CFS")
plt.plot(x, [float(r["CFS_FR"]) for r in d], "s-", color="#1f77b4", lw=1.4, ms=4, label="CFS-FR")
plt.xticks(x, [str(c) for c in cs])
plt.xlabel("counters per switch"); plt.ylabel("flow coverage")
plt.legend(handlelength=1.4, labelspacing=0.2, borderpad=0.25)
plt.grid(True, ls=":", alpha=0.5)
save("E2b_cfs.pdf")

# ---------- E3: AFG F1 vs flow scale (categorical x: fixes label overlap) ----------
d = rows("E3_flowscale.csv")
afg = {}
for r in d:
    if int(r["test"]) == 2:
        afg[int(r["n_flows"])] = float(r["afg_f1"])
xs = sorted(afg)
plt.figure(figsize=FIGSIZE)
plt.plot(range(len(xs)), [afg[x] for x in xs], "o-", color="#d62728", lw=1.4, ms=4)
plt.xticks(range(len(xs)), [f"{x//1000}K" for x in xs])
plt.ylim(0, 1.05)
plt.xlabel("# flows"); plt.ylabel("AFG detection F1")
plt.grid(True, ls=":", alpha=0.5)
save("E3_flowscale.pdf")

# ---------- E9: synflood (slightly smaller, single-column 0.5 width) ----------
d = rows("E9_synflood_intensity.csv")
fl = [int(r["flood"]) for r in d]; f1 = [float(r["F1"]) for r in d]
plt.figure(figsize=FIGSIZE)
plt.plot(range(len(fl)), f1, "o-", color="#d62728", lw=1.4, ms=4)
plt.xticks(range(len(fl)), [str(v) for v in fl], fontsize=7)
plt.ylim(-0.05, 1.08)
plt.xlabel("SYNs per victim /24"); plt.ylabel("AFG detection F1")
plt.grid(True, ls=":", alpha=0.5)
save("E9_synflood.pdf")
