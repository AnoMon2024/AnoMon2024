#!/bin/bash
# Build the Overleaf paper locally and report errors / undefined refs.
# The minimal local TeX install was missing IEEEtran.cls/.bst, relsize.sty,
# algorithm2e.sty; we staged them under /tmp (see paths below). Re-fetch if /tmp
# was cleared: IEEEtran.cls + bibtex/IEEEtran.bst + relsize.sty from CTAN, and
# algorithm2e.sty via `apt-get download texlive-science && dpkg -x ... /tmp/tlsci`.
set -u
DIR=/data/jjc/AnoMon/AnoMon_TON25_Overleaf
export TEXINPUTS=/tmp//:/tmp/tlsci//:
export BSTINPUTS=/tmp:.:
export BIBINPUTS=.:
cd "$DIR"
pdflatex -interaction=nonstopmode main.tex > /tmp/build_l1.log 2>&1
bibtex main > /tmp/build_bib.log 2>&1
pdflatex -interaction=nonstopmode main.tex > /tmp/build_l2.log 2>&1
pdflatex -interaction=nonstopmode main.tex > /tmp/build_l3.log 2>&1
echo "=== exit $? | pages: $(pdfinfo main.pdf 2>/dev/null | awk '/Pages/{print $2}') ==="
echo "--- LaTeX errors (! ...) ---"; grep -nE '^! ' /tmp/build_l3.log | head -15
echo "--- undefined refs/citations ---"; grep -nE 'Warning: (Reference|Citation).*undefined' /tmp/build_l3.log | sed 's/ on input.*//' | sort -u | head -30
echo "--- missing files ---"; grep -nE 'not found|Fatal' /tmp/build_l3.log | head
