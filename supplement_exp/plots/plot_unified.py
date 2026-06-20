#!/usr/bin/env python3
# coding=utf-8
"""Regenerate all supplement result figures in the SAME style as the paper's
original plots (per the author's reference code):
  - Liberation Sans (Arial-metric-compatible), bold large axis labels
  - hollow markers (markerfacecolor='none', markeredgewidth=2, ms~8.8), lw=2
  - matplotlib default color cycle; marker sequence D,s,v,o,^,p ; ours = C0 'D'
  - dashed grid on both axes; legend placed to NOT occlude curves (headroom)
  - figsize (6,4.5) so that, scaled into a 0.31\\textwidth subfigure, fonts match
"""
import csv, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---- global style matching the reference ----
plt.rcParams.update({
    "font.family": "Liberation Sans",   # Arial-compatible metrics
    "mathtext.default": "regular",
    "pdf.fonttype": 42, "ps.fonttype": 42,
})
LABEL_FS, TICK_FS, LEG_FS = 24, 19, 19
COLORS  = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]
MARKERS = ["D", "s", "v", "o", "^", "p"]
PLOTS = "/data/jjc/AnoMon/AnoMon2024/supplement_exp/plots"
PICS  = "/data/jjc/AnoMon/AnoMon_TON25_Overleaf/pictures"
RES   = "/data/jjc/AnoMon/AnoMon2024/supplement_exp/results"

def rows(f):
    with open(os.path.join(RES, f)) as fh: return list(csv.DictReader(fh))

def new_ax():
    fig = plt.figure(figsize=(6, 4.5))
    plt.tick_params(labelsize=TICK_FS)
    return fig, plt.gca()

def line(ax, x, y, idx, label):
    ax.plot(x, y, label=label, linestyle="-", marker=MARKERS[idx % len(MARKERS)],
            markersize=8.8, alpha=1, linewidth=2, color=COLORS[idx % len(COLORS)],
            markerfacecolor="none", markeredgewidth=2)

def finish(fig, ax, xlabel, ylabel, fname, legend=None, ylim=None, xticks=None,
           xticklabels=None, yticks=None, grid=True, legkw=None):
    ax.set_xlabel(xlabel, fontweight="bold", fontsize=LABEL_FS)
    ax.set_ylabel(ylabel, fontweight="bold", fontsize=LABEL_FS)
    if xticks is not None: ax.set_xticks(xticks)
    if xticklabels is not None: ax.set_xticklabels(xticklabels)
    if yticks is not None: ax.set_yticks(yticks)
    if ylim is not None: ax.set_ylim(*ylim)
    if grid:
        ax.grid(True, linestyle="--", axis="y")
        ax.grid(True, linestyle="--", axis="x")
    if legend:
        kw = dict(handlelength=2.4, columnspacing=1.0, borderpad=0.3, labelspacing=0.25)
        if legkw: kw.update(legkw)
        leg = ax.legend(**kw)
        plt.setp(leg.get_texts(), fontweight="bold", fontsize=LEG_FS)
    fig.tight_layout()
    for d in (PLOTS, PICS):
        fig.savefig(os.path.join(d, fname))
    plt.close(fig)
    print("wrote", fname)

# ============ E1: ALE vs memory (4 methods, lower=better) ============
d = rows("E1_ale_vs_mem.csv")
mem = [float(r["memKB"]) for r in d]
series = [("AnoTable (ours)", "AnoTable"), ("FlowLens", "FlowLens"),
          ("SketchFeature", "SketchFeature"), ("DDSketch", "DDSketch")]
fig, ax = new_ax()
for i, (lab, col) in enumerate(series):
    line(ax, mem, [float(r[col]) for r in d], i, lab)
finish(fig, ax, "Memory (KB)", "ALE", "E1_ale_vs_mem.pdf",
       legend=True, ylim=(0, 11.8), yticks=[0, 2, 4, 6, 8],
       legkw=dict(loc="upper center", ncol=2))

# ============ E7: ALE vs geometric ratio alpha (3 memory levels) ============
d = rows("E7_alpha.csv")
bymem = {}
for r in d: bymem.setdefault(int(r["memKB"]), []).append((float(r["alpha"]), float(r["ALE"])))
fig, ax = new_ax()
xs = None
for i, mk in enumerate(sorted(bymem)):
    pts = sorted(bymem[mk]); xs = [a for a, _ in pts]
    line(ax, range(len(xs)), [e for _, e in pts], i, f"{mk} KB")
labels = ["1\n(unif.)" if a == 1.0 else f"{a:g}" for a in xs]
finish(fig, ax, r"Geometric Ratio $\alpha$", "ALE", "E7_alpha.pdf",
       legend=True, ylim=(2.8, 7.6), xticks=list(range(len(labels))), xticklabels=labels,
       legkw=dict(loc="upper center", ncol=3))

# ============ E4: bar chart, distribution vs scalar ============
d = rows("E4_ablation_0.08.csv")
feats = [r["feature"] for r in d]; f1 = [float(r["bestF1"]) for r in d]
fig, ax = new_ax()
bars = ax.bar(range(len(feats)), f1, color=COLORS[:len(feats)], width=0.62,
              edgecolor="black", linewidth=1.2)
for b, v in zip(bars, f1):
    ax.text(b.get_x() + b.get_width()/2, v + 0.02, f"{v:.2f}", ha="center",
            fontsize=TICK_FS-3, fontweight="bold")
finish(fig, ax, "Per-flow Feature", "Best F1", "E4_ablation.pdf",
       ylim=(0, 1.18), xticks=range(len(feats)), xticklabels=feats,
       yticks=[0, 0.2, 0.4, 0.6, 0.8, 1.0], grid=True)

# ============ E2a: collect+analyze time vs switches (log y) ============
d = rows("E2a_control_overhead.csv")
sw = [int(r["switches"]) for r in d]
fig, ax = new_ax()
line(ax, range(len(sw)), [float(r["T_seq_ms"])/1000 for r in d], 0, "sequential")
line(ax, range(len(sw)), [float(r["T_layer_ms"])/1000 for r in d], 1, "layer-by-layer")
ep = float(d[0]["epoch_s"])
ax.axhline(ep, ls="--", color="gray", lw=2, label=f"epoch={ep:g}s")
ax.set_yscale("log")
finish(fig, ax, "# Switches", "Time (s)", "E2a_control_overhead.pdf",
       legend=True, ylim=(0.02, 800), xticks=range(len(sw)), xticklabels=[str(s) for s in sw],
       legkw=dict(loc="upper left", ncol=1))

# ============ E2b: flow coverage vs counters (CFS) ============
d = rows("E2b_cfs.csv")
cs = [int(r["cells"]) for r in d]
fig, ax = new_ax()
ax.plot(range(len(cs)), [float(r["Optimal"]) for r in d], "k--", lw=2, label="Optimal")
line(ax, range(len(cs)), [float(r["CFS"]) for r in d], 0, "CFS")
line(ax, range(len(cs)), [float(r["CFS_FR"]) for r in d], 1, "CFS-FR")
finish(fig, ax, "Counters per Switch", "Flow Coverage", "E2b_cfs.pdf",
       legend=True, ylim=(0, 1.12), xticks=range(len(cs)), xticklabels=[str(c) for c in cs],
       yticks=[0, 0.2, 0.4, 0.6, 0.8, 1.0], legkw=dict(loc="upper left", ncol=1))

# ============ E3: AFG detection F1 vs flow scale (single line) ============
d = rows("E3_flowscale.csv")
afg = {int(r["n_flows"]): float(r["afg_f1"]) for r in d if int(r["test"]) == 2}
xs = sorted(afg)
fig, ax = new_ax()
line(ax, range(len(xs)), [afg[x] for x in xs], 0, "AnoMon (ours)")
finish(fig, ax, "# Flows", "AFG Detection F1", "E3_flowscale.pdf",
       ylim=(0, 1.05), xticks=range(len(xs)), xticklabels=[f"{x//1000}K" for x in xs],
       yticks=[0, 0.2, 0.4, 0.6, 0.8, 1.0])

# ============ E9: SYN-flood detection F1 vs intensity (single line) ============
d = rows("E9_synflood_intensity.csv")
fl = [int(r["flood"]) for r in d]; f1 = [float(r["F1"]) for r in d]
fig, ax = new_ax()
line(ax, range(len(fl)), f1, 0, "AnoMon (ours)")
finish(fig, ax, "SYNs per Victim /24", "AFG Detection F1", "E9_synflood.pdf",
       ylim=(-0.04, 1.08), xticks=range(len(fl)), xticklabels=[str(v) for v in fl],
       yticks=[0, 0.2, 0.4, 0.6, 0.8, 1.0])

print("all done")
