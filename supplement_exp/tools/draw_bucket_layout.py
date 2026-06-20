#!/usr/bin/env python3
"""R1-5: schematic of how one AnoTable bucket is laid out in Tofino registers.

v5: the in-image title and the bottom "All arrays..." note are REMOVED -- both
are now described in the LaTeX caption. The figure keeps only the register boxes,
the per-row role labels, and the "32-bit register" braces; the remaining fonts
are slightly enlarged. Widths are the actual CellSketch.p4 values."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

plt.rcParams.update({"font.family": "Liberation Sans", "pdf.fonttype": 42})
BLUE, ORANGE, YELLOW, GREEN, PURPLE = "#cfe2f3", "#fce5cd", "#fff2cc", "#d9ead3", "#e6d5f2"
EDGE = {"blue": "#3d6fa5", "orange": "#b45f06", "yellow": "#bf9000",
        "green": "#6aa84f", "purple": "#8e7cc3"}
FS_FIELD, FS_BRACE, FS_ROLE = 21, 18, 17

fig, ax = plt.subplots(figsize=(7.2, 4.8))
ax.set_xlim(0, 104); ax.set_ylim(-1, 69); ax.axis("off")

def ekey(e):
    for k, v in EDGE.items():
        if v == e: return k
    return "blue"

def reg(x, y, w, h, color, edge, fields):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.2",
                                fc=color, ec=edge, lw=1.8))
    fx = x
    for label, frac, hatched in fields:
        fw = w * frac
        if hatched:
            ax.add_patch(Rectangle((fx, y), fw, h, fc="none", ec=edge, lw=1.0, hatch="////"))
        else:
            ax.text(fx + fw/2, y + h/2, label, ha="center", va="center",
                    fontsize=FS_FIELD, color=EDGE[ekey(edge)])
        fx += fw
    fx = x
    for label, frac, hatched in fields[:-1]:
        fx += w*frac
        ax.plot([fx, fx], [y, y+h], color=edge, lw=1.1)

def brace(x, w, ytop, text):
    y = ytop + 1.3
    ax.plot([x+1, x+w-1], [y, y], color="black", lw=1.1)
    ax.plot([x+1, x+1], [y, y-1.6], color="black", lw=1.1)
    ax.plot([x+w-1, x+w-1], [y, y-1.6], color="black", lw=1.1)
    ax.plot([x+w/2, x+w/2], [y, y+1.6], color="black", lw=1.1)
    ax.text(x+w/2, y+3.9, text, ha="center", va="center", fontsize=FS_BRACE)

def role(x, y, text):
    ax.text(x, y, text, ha="center", va="center", fontsize=FS_ROLE,
            style="italic", color="#333333")

W, H = 40, 10
xL, xR = 6, 56
cL, cR = xL+W/2, xR+W/2

# ---- row 1: flow-identity digest ----
y1 = 52
brace(xL, W, y1+H, "32-bit register"); brace(xR, W, y1+H, "32-bit register")
reg(xL, y1, W, H, BLUE,   EDGE["blue"],   [("srcIP tag", 1.0, False)])
reg(xR, y1, W, H, ORANGE, EDGE["orange"], [("dstIP tag", 1.0, False)])
role(52, y1-3.4, "flow-identity digest (srcIP + dstIP tags)")

# ---- row 2: per-flow metric | distribution sub-counters ----
y2 = 28
brace(xL, W, y2+H, "32-bit register"); brace(xR, W, y2+H, "32-bit register")
reg(xL, y2, W, H, YELLOW, EDGE["yellow"], [("Counter", 1.0, False)])
reg(xR, y2, W, H, GREEN,  EDGE["green"],  [("CellSketch", 1.0, False)])
role(cL, y2-3.4, "per-flow metric")
role(cR, y2-3.4, "distribution counters")

# ---- row 3: bucket->cell overflow index + reserved ----
y3 = 4
brace(xL, W, y3+H, "32-bit register")
reg(xL, y3, W, H, PURPLE, EDGE["purple"], [("cellIdx", 0.5, False), ("", 0.5, True)])
role(cL, y3-3.4, "16-bit overflow index + reserved (hatched)")

plt.tight_layout(pad=0.2)
for p in ["../plots/bucket_layout.pdf",
          "/data/jjc/AnoMon/AnoMon_TON25_Overleaf/pictures/bucket_layout.pdf",
          "../plots/bucket_layout.png"]:
    fig.savefig(p, bbox_inches="tight", dpi=170)
    print("wrote", p)
