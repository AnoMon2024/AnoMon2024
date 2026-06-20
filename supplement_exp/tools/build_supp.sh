#!/bin/bash
# Build the online supplement and report pages + the order of the last sections.
set -u
DIR=/data/jjc/AnoMon/AnoMon_Supplementary_TON25
export TEXINPUTS=/tmp//:/tmp/tlsci//:
export BSTINPUTS=/tmp:.:
export BIBINPUTS=.:
cd "$DIR"
pdflatex -interaction=nonstopmode main.tex > /tmp/supp_l1.log 2>&1
bibtex main > /tmp/supp_bib.log 2>&1
pdflatex -interaction=nonstopmode main.tex > /tmp/supp_l2.log 2>&1
pdflatex -interaction=nonstopmode main.tex > /tmp/supp_l3.log 2>&1
N=$(pdfinfo main.pdf 2>/dev/null | awk '/Pages/{print $2}')
echo "=== exit $? | pages: $N ==="
grep -nE '^! ' /tmp/supp_l3.log | head
echo "--- section order (last pages) ---"
for i in $(seq 1 "$N"); do
  t=$(pdftotext -f "$i" -l "$i" main.pdf - 2>/dev/null)
  echo "$t" | grep -q 'Algorithm Pseudocode'        && echo "p$i: [Algorithm Pseudocode heading]"
  echo "$t" | grep -q 'Query workflow of CellSketch' && echo "p$i: [Algorithm 4 = last pseudocode]"
  echo "$t" | grep -qiE 'references' && echo "p$i: [References]"
done
