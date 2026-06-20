#!/usr/bin/env python3
"""Mark revision additions on the *marked* Overleaf copy with PER-REVIEWER colors.

Color scheme (matches the Response letter):
    R1 -> green (revR1), R2 -> red (revR2), R3 -> blue (revR3), AE -> purple (revAE).
Macros \rA \rB \rC \rD and the revRx colors are defined in the marked main.tex.

Block prose  -> {\color{revRx} ... }
New-float caption (whole) -> insert \color{revRx} right after \caption{
Partial caption / inline addition -> {\color{revRx} ...frag... }
"""
import os
ROOT = "/data/jjc/AnoMon/AnoMon_TON25_Overleaf_marked/tex"

def load(f): return open(os.path.join(ROOT, f), encoding="utf-8").read()
def save(f, s): open(os.path.join(ROOT, f), "w", encoding="utf-8").write(s)

miss = []
def block(s, start, end, col, tag):
    """Wrap the span [start..end] (inclusive of end) in {\color{col} ...}."""
    i = s.find(start)
    if i < 0: miss.append("BLOCK-start ["+tag+"]"); return s
    j = s.find(end, i)
    if j < 0: miss.append("BLOCK-end ["+tag+"]"); return s
    j += len(end)
    return s[:i] + "{\\color{"+col+"}" + s[i:j] + "}" + s[j:]

def cap(s, lead, col, tag):
    """Color a whole caption that begins with `lead`."""
    key = "\\caption{" + lead
    i = s.find(key)
    if i < 0: miss.append("CAP ["+tag+"]"); return s
    ins = i + len("\\caption{")
    return s[:ins] + "\\color{"+col+"}" + s[ins:]

def inl(s, frag, col, tag):
    """Wrap a verbatim fragment (e.g. one clause of a caption) in color."""
    if frag not in s: miss.append("INLINE ["+tag+"]"); return s
    return s.replace(frag, "{\\color{"+col+"}" + frag + "}", 1)

def wrap_table(s, label, col, tag):
    """Color a whole table float (caption + every cell + rules) in `col`.

    The color group is injected INSIDE the float (right after \\begin{table..}[..])
    and closed just before \\end{table..}. Putting \\color *before* \\begin{table}
    does NOT work: the color-push special lands outside the deferred float box, so
    the cell text stays black. Inside the float, the caption/tabular inherit the
    color, \\arrayrulecolor colors the rules, and the \\cmarkt/\\xmarkt marks are
    locally redefined so they drop their hard-coded green/red and inherit `col`."""
    li = s.find("\\label{"+label+"}")
    if li < 0: miss.append("TBL-label ["+tag+"]"); return s
    bi = s.rfind("\\begin{table", 0, li)
    if bi < 0: miss.append("TBL-begin ["+tag+"]"); return s
    # position right after \begin{table} / \begin{table*}, skipping an optional [..]
    p = s.find("}", bi) + 1
    q = p
    while q < len(s) and s[q] in " \t\n": q += 1
    if q < len(s) and s[q] == "[":
        p = s.find("]", q) + 1
    ee = s.find("\\end{table", li)
    if ee < 0: miss.append("TBL-end ["+tag+"]"); return s
    # NOTE: do NOT wrap the float in a brace group -- that would break the
    # table's \centering. Instead set \color/\arrayrulecolor right after
    # \begin{table..}; the table environment itself scopes \color (so the
    # surrounding text is unaffected). \arrayrulecolor, however, is NOT reverted
    # by the environment for floats, so we explicitly reset it to black before
    # \end{table..} (otherwise the next, unrelated table inherits these rules).
    body = ("\\color{"+col+"}\\arrayrulecolor{"+col+"}"
            "\\renewcommand{\\cmarkt}{\\checkmark}"
            "\\renewcommand{\\xmarkt}{\\ensuremath{\\times}}%\n")
    reset = "\\arrayrulecolor{black}%\n"
    # The double-column (table*) caption does not inherit the ambient color, so
    # prepend \color inside the \caption{...} argument. We must NOT use
    # \renewcommand there (it breaks \caption's argument parser), so we instead
    # rewrite the hard-coded \cmarkt/\xmarkt/\pmarkt marks inside the caption to
    # plain symbols that inherit the injected color.
    ci = s.find("\\caption{", p)
    if 0 <= ci < ee:
        cj = ci + len("\\caption{")
        depth, k = 1, cj
        while k < len(s) and depth > 0:
            if s[k] == "{": depth += 1
            elif s[k] == "}": depth -= 1
            k += 1
        ck = k - 1  # the } closing \caption{
        captext = (s[cj:ck]
                   .replace("\\cmarkt{}", "\\ensuremath{\\checkmark}")
                   .replace("\\xmarkt{}", "\\ensuremath{\\times}")
                   .replace("\\pmarkt{}", "\\ensuremath{\\sim}"))
        newcap = "\\color{"+col+"}" + captext
        return s[:p] + body + s[p:cj] + newcap + s[ck:ee] + reset + s[ee:]
    return s[:p] + body + s[p:ee] + reset + s[ee:]

R1, R2, R3, AE = "revR1", "revR2", "revR3", "revAE"

# ====================== 1.introduction.tex ======================
f = "1.introduction.tex"; s = load(f)
s = block(s, "We do not argue that sketch-based measurement is wasteful",
             "irrelevant to anomalies.", R1, "R1-1 intro")
s = block(s, "1) \\sysname{} is applicable to a range of network-wide",
             "such as SYN floods (\\S~\\ref{subsec:octopus:afg}).", R1, "R1-4 contrib1")
s = block(s, "2) \\sysname{} decouples always-on coverage",
             "rather than all flows.", R1, "R1-1 contrib2")
s = block(s, "Here, the \\textit{per-flow per-hop attribute distribution} of a flow",
             "nor which path they take.", R1, "R1-2 def")
s = block(s, "To make the objective concrete, we informally define",
             "monitor the traffic in AFG with fine-grained active measurement inside the network.",
             R2, "R2-4 terms")
save(f, s)

# ====================== 2.background&motivation.tex ======================
f = "2.background&amp;motivation.tex"; s = load(f)
s = block(s, "\\subsection{Closely Related Measurements}",
             "selective per-flow per-hop attribute-distribution measurement for network-wide anomaly localization.",
             R2, "R2-1 II-C prose")
s = wrap_table(s, "tab:related", R2, "tab:related")
save(f, s)

# ====================== 3.workflow.tex ======================
f = "3.workflow.tex"; s = load(f)
s = block(s, "\\bbb{Rationale for the two-phase design:}",
             "proportional to the (few) abnormal flows inside the network, rather than to all traffic.",
             R1, "R1-3")
s = block(s, "Initially, all buckets in both HotFilter and ColdSampler are empty",
             "the frequency/vote fields set to zero.", R1, "R1-4 Fig3 datastruct")
s = block(s, "Beyond common metrics, \\tname{} captures per-flow per-hop attribute distributions",
             "gating-then-localization workflow (\\S~\\ref{sec:related:closely}).", R2, "R2-1 V soften")
s = block(s, "\\bbb{Extending \\algoname{} to other anomaly signals:}",
             "it does not perform payload- or signature-level analysis.", R1, "R1-4 SYN")
s = block(s, "The intuition is that packet-level attributes such as queuing delay",
             "we use $\\alpha=2$ by default.", R1, "R1-6 geometric")
s = block(s, "\\bbb{Timestamp and tag lifecycle:}",
             "or switch-local metadata, without affecting the algorithm.", R3, "R3-4")
s = block(s, "\\bbb{Control-plane overhead and scalability:}",
             "at different topology scales in $\\S$~\\ref{subsec:exp:sim}.", R2, "R2-3 model")
s = block(s, "\\bbb{Detection latency and short-lived anomalies:}",
             "shorter anomalies are detected less reliably, consistent with the bound above.", R3, "R3-3 latency")
s = block(s, "Afterwards, the analyzer \\textit{dynamically generates} candidate flow groups",
             "mark the traffic of confirmed AFGs to trigger active measurement inside the network.", R3, "R3-1")
save(f, s)

# ====================== 6.implementation.tex ======================
f = "6.implementation.tex"; s = load(f)
s = block(s, "The AFG membership is decided by a match-action table",
             "installing rules only at ingress edge switches.", R2, "R2-4 marking mem")
s = block(s, "\\bbb{\\tname{} bucket layout on Tofino:}",
             "realizable under the register-width constraints of programmable ASICs.", R1, "R1-5 prose")
s = cap(s, "Layout of one \\tname{} bucket across Tofino", R1, "fig:bucketlayout")
s = wrap_table(s, "tab:bucketlayout", R1, "tab:bucketlayout")
save(f, s)

# ====================== 7.evaluation.tex ======================
f = "7.evaluation.tex"; s = load(f)
# ---- R3-2 parameter guidelines prose + table ----
s = block(s, "\\bbb{Parameter guidelines:}",
             "the geometric ratio $\\alpha$ (Figure~\\ref{exp:cell:alpha}).", R3, "R3-2 prose")
s = wrap_table(s, "tab:param", R3, "tab:param")
# ---- R3-5 baseline fairness ----
s = block(s, "\\bbb{Baseline configuration and fairness:}",
             "make the comparison unfair.", R3, "R3-5")
# ---- Fig 8 = AnoSketch accuracy+extensibility: only (c) SYN-flood clause is new (R1-4) ----
s = inl(s, "(c) SYN-flood AFG detection F1 \\textit{vs.} flood intensity, where \\algoname{} inserts only SYN packets and queries destination $/24$ groups (precision is always $1.0$).",
        R1, "Fig8 main (c) clause")
s = cap(s, "SYN-flood F1.", R1, "Fig8c subcap")
s = block(s, "\\bbb{\\textit{Extensibility to SYN floods (Figure",
             "a full DDoS/IDS pipeline (\\eg{}, payload analysis) is beyond our scope.", R1, "E9 SYN para")
# ---- Fig 11 = additional AnoTable eval (a)E1 red (b)E7 green (c)E4 red ----
s = cap(s, "ALE \\textit{vs.} memory.", R2, "Fig11a E1")
s = cap(s, "Vary ratio $\\alpha$.", R1, "Fig11b E7")
s = cap(s, "Dist.\\ \\textit{vs.} scalar.", R2, "Fig11c E4")
s = cap(s, "Additional evaluation of \\tname{}", R2, "Fig11 main")
# subfigure (b) is the geometric-ratio study (R1-6, green): keep its clause of
# the main caption green so it matches the green (b) subcaption.
s = inl(s, "(b) estimation error \\textit{vs.} the geometric interval ratio $\\alpha$ ($\\alpha{=}1$ is uniform binning);",
        R1, "Fig11 main (b) green")
s = block(s, "\\bbb{\\textit{Comparison with FlowLens and SketchFeature",
             "adaptively refine only the dense regions via cell division.", R2, "E1 para")
s = block(s, "\\bbb{\\textit{Impact of the geometric ratio $\\alpha$ (Figure",
             "balance between accuracy and memory.", R1, "E7 para")
s = block(s, "\\bbb{\\textit{Benefit of distribution over scalar counters",
             "justifying \\tname{}'s per-flow per-hop distribution measurement.", R2, "E4 para")
# ---- Fig 14 = scalability + CFS + flow-scale (all R2) ----
s = cap(s, "Analyze time.", R2, "Fig14a E2a")
s = cap(s, "CFS coverage.", R2, "Fig14b E2b")
s = cap(s, "Flow-scale F1.", R2, "Fig14c E3")
s = cap(s, "Scalability and system-level comparison", R2, "Fig14 main")
s = block(s, "\\bbb{Scalability of control-plane overhead (Figure",
             "AnoMon's control plane scales to large data-center topologies.", R2, "E2a para")
s = block(s, "We note that controller-free designs such as ISDC",
             "remains bounded and scalable.", R2, "E2c para")
s = block(s, "\\bbb{\\textit{Comparison with cooperative flow selection (Figure",
             "complementary to the coverage-oriented objective of CFS.", R2, "E2b para")
s = block(s, "\\bbb{Impact of flow scale (Figure~\\ref{exp:simu:flowscale}):}",
             "balances accuracy and resolution without re-configuring the data plane.", R2, "E3 para")
# ---- R3-3 fast-trigger experiment (E10): new figure + paragraph ----
s = cap(s, "Benefit of the optional fast-trigger mode", R3, "Fig E10 caption")
s = block(s, "\\bbb{Benefit of the fast-trigger mode (Figure~\\ref{exp:simu:fasttrigger}):}",
             "at the cost of a few additional control-plane messages.", R3, "E10 para")
# ---- R1-7 discussion / failure cases ----
s = block(s, "\\bbb{Discussion and failure cases:}",
             "scalable, diagnosis-oriented measurement.", R1, "R1-7 failure")
save(f, s)

print("MISSES:", len(miss))
for m in miss: print("  ", m)
print("done")
