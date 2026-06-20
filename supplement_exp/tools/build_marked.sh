#!/bin/bash
# Build the per-reviewer COLOR-MARKED version of the paper.
#   1) refresh the marked copy from the clean Overleaf source
#   2) inject the revRx color macros into the marked main.tex (marked-only)
#   3) run mark_revisions.py to wrap each reviewer's additions in its color
#   4) compile and report pages / errors
set -u
CLEAN=/data/jjc/AnoMon/AnoMon_TON25_Overleaf
MARK=/data/jjc/AnoMon/AnoMon_TON25_Overleaf_marked
TOOLS=/data/jjc/AnoMon/AnoMon2024/supplement_exp/tools

rsync -a --delete \
  --exclude='/main.pdf' --exclude='/main.aux' --exclude='/main.log' \
  --exclude='/main.bbl' --exclude='/main.blg' --exclude='/main.out' \
  --exclude='/main.synctex.gz' --exclude='*.orig' "$CLEAN"/ "$MARK"/

# (2) inject macros right after the reviewF color definition, once.
python3 - "$MARK/main.tex" <<'PY'
import sys
p = sys.argv[1]; s = open(p, encoding="utf-8").read()
if "revR1" not in s:
    anchor = "\\definecolor{reviewF}{HTML}{1D7322}"
    macros = anchor + r"""

	\usepackage{colortbl} % \arrayrulecolor for coloring table rules in marked ver.
	% ==== per-reviewer revision marking (ONLY in the marked version) ====
	% R1 -> green, R2 -> red, R3 -> blue, AE/Editor -> purple.
	\definecolor{revR1}{HTML}{348017} % Reviewer 1  : green
	\definecolor{revR2}{HTML}{EE220D} % Reviewer 2  : red
	\definecolor{revR3}{HTML}{2B65EC} % Reviewer 3  : blue
	\definecolor{revAE}{HTML}{7F007F} % AE / Editor : purple
	\newcommand{\rA}[1]{{\color{revR1}#1}}
	\newcommand{\rB}[1]{{\color{revR2}#1}}
	\newcommand{\rC}[1]{{\color{revR3}#1}}
	\newcommand{\rD}[1]{{\color{revAE}#1}}"""
    s = s.replace(anchor, macros, 1)
    open(p, "w", encoding="utf-8").write(s)
    print("macros injected")
else:
    print("macros already present")
PY

# (3) apply per-reviewer color wraps
python3 "$TOOLS/mark_revisions.py" 2>/dev/null

# (4) compile
export TEXINPUTS=/tmp//:/tmp/tlsci//:
export BSTINPUTS=/tmp:.:
export BIBINPUTS=.:
cd "$MARK"
pdflatex -interaction=nonstopmode main.tex > /tmp/mk_l1.log 2>&1
bibtex main > /tmp/mk_bib.log 2>&1
pdflatex -interaction=nonstopmode main.tex > /tmp/mk_l2.log 2>&1
pdflatex -interaction=nonstopmode main.tex > /tmp/mk_l3.log 2>&1
echo "=== MARKED build exit $? | pages: $(pdfinfo main.pdf 2>/dev/null | awk '/Pages/{print $2}') ==="
echo "--- LaTeX errors (! ...) ---"; grep -nE '^! ' /tmp/mk_l3.log | head -15
echo "--- undefined refs/citations ---"; grep -nE 'Warning: (Reference|Citation).*undefined' /tmp/mk_l3.log | sed 's/ on input.*//' | sort -u | head
