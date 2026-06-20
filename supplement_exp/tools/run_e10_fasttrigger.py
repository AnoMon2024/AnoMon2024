#!/usr/bin/env python3
# coding=utf-8
"""E10 (R3-3): benefit of the optional fast-trigger mode.

In the default PERIODIC mode, a first-time AFG is detected only at the next
table-collection boundary, and the in-network fine-grained measurement is then
activated one epoch later; hence its per-hop distribution is captured only if the
anomaly is still active at the 2nd epoch boundary after its onset (i.e. it must
last ~>=2 epochs). In the FAST-TRIGGER mode, an edge device that observes a
threshold-crossing sketch counter immediately triggers AFG marking, so the
in-network measurement is activated within t_cross+T_notify of the onset and the
per-hop distribution is captured whenever the anomaly outlives that short delay.

We Monte-Carlo the onset of a single first-time anomaly uniformly within an epoch
and report, as a function of the anomaly duration, (i) the fraction of anomalies
whose fine-grained per-hop localization is captured, and (ii) the mean detection
latency, for the two modes.  Output matches the paper figure style.
"""
import csv, os
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams.update({"font.family": "Liberation Sans", "mathtext.default": "regular",
                     "pdf.fonttype": 42})
LABEL_FS, TICK_FS, LEG_FS = 24, 19, 19
COLORS = ["#1f77b4", "#ff7f0e"]; MARKERS = ["D", "s"]

E        = 5000.0   # epoch length (ms)  -> 5 s
T_PROC   = 25.0     # edge collect+analyze (ms), from testbed Fig.11
T_NOTIFY = 10.0     # fast-trigger notification (ms)
T_CROSS  = 100.0    # time for the edge sketch counter to cross the threshold (ms)
N        = 200000
RNG = np.random.default_rng(2026)

durations = [50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000]
rows = []
for D in durations:
    onset = RNG.uniform(0, E, N)                 # onset within the current epoch
    # periodic: detect at next boundary (E), activate in-network at 2E; captured
    # iff anomaly still active then.
    cap_p = np.mean(onset + D > 2 * E)
    lat_p = np.mean(E - onset + T_PROC)          # detection latency (ms)
    # fast-trigger: threshold crossed at onset+T_CROSS, in-network active at
    # onset+T_CROSS+T_NOTIFY; captured iff anomaly outlives that delay.
    cap_f = float(D > T_CROSS + T_NOTIFY)
    lat_f = T_CROSS + T_PROC                      # detection latency (ms)
    rows.append(dict(duration_ms=D, cap_periodic=round(cap_p, 4), cap_fast=round(cap_f, 4),
                     lat_periodic_ms=round(lat_p, 1), lat_fast_ms=round(lat_f, 1)))
    print(f"D={D:>6}ms  capture: periodic={cap_p:.2f} fast={cap_f:.2f} | "
          f"latency: periodic={lat_p:.0f}ms fast={lat_f:.0f}ms")

RES = "/data/jjc/AnoMon/AnoMon2024/supplement_exp/results"
os.makedirs(RES, exist_ok=True)
with open(os.path.join(RES, "E10_fasttrigger.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

# ---- plot: fine-grained localization capture rate vs anomaly duration ----
xs = list(range(len(durations)))
fig = plt.figure(figsize=(6, 4.5)); ax = plt.gca()
plt.tick_params(labelsize=TICK_FS)
ax.plot(xs, [r["cap_fast"] for r in rows], linestyle="-", marker=MARKERS[0], color=COLORS[0],
        markersize=8.8, lw=2, markerfacecolor="none", markeredgewidth=2, label="fast-trigger")
ax.plot(xs, [r["cap_periodic"] for r in rows], linestyle="-", marker=MARKERS[1], color=COLORS[1],
        markersize=8.8, lw=2, markerfacecolor="none", markeredgewidth=2, label="periodic")
ax.axvline(np.interp(E, durations, xs), ls="--", color="gray", lw=1.5)
ax.set_xlabel("Anomaly Duration (ms)", fontweight="bold", fontsize=LABEL_FS)
ax.set_ylabel("Localization Capture", fontweight="bold", fontsize=LABEL_FS)
ax.set_xticks(xs); ax.set_xticklabels([str(d) for d in durations], rotation=40, ha="right")
ax.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0]); ax.set_ylim(-0.05, 1.18)
ax.grid(True, ls="--", axis="y"); ax.grid(True, ls="--", axis="x")
leg = ax.legend(loc="upper center", ncol=2, handlelength=2.2, columnspacing=1.0, borderpad=0.3)
plt.setp(leg.get_texts(), fontweight="bold", fontsize=LEG_FS)
fig.tight_layout()
for d in [RES.replace("results", "plots"), "/data/jjc/AnoMon/AnoMon_TON25_Overleaf/pictures"]:
    fig.savefig(os.path.join(d, "E10_fasttrigger.pdf"))
print("wrote E10_fasttrigger.pdf")
