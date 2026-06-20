# Revision experiments (E1–E10)

This directory holds the experiments added for the TON major revision. Every
experiment is scripted and maps to a figure/table in the revised manuscript and
to the reviewer comment it answers (see the table in the
[top-level README](../README.md)).

## Environment

Two toolchains are used:

* **Python (simulation & analysis).** Used by E2a, E3, E5, E8, E10 and all
  plotting.
  ```bash
  conda create -n AnoMon python=3.9 -y && conda activate AnoMon
  pip install numpy scipy pandas matplotlib simpy networkx pybind11==2.10.0
  ```
  The NS.PY simulator generates its own traffic, so these experiments need **no
  external trace** and run out of the box.

* **C++ (data-plane-faithful baselines).** Used by E1, E4, E7, E9. Each has a
  `Makefile` (or a prebuilt binary); build with `make` and run the produced
  executable. These read a CAIDA-2018 trace (see below).

> **CAIDA trace.** The CPU/C++ experiments (E1, E7, E9) read a CAIDA-2018 trace.
> Point the loader at your local copy, or use `tools/gen_synth_trace.py` to
> generate a synthetic trace for a smoke test (relative trends are preserved).

## Directory layout

```
supplement_exp/
├── tools/        # entry-point scripts (run_*.{py,sh}) and plotting helpers
├── baselines/    # C++/Python baselines: E1_distribution, E3_coverage,
│                 #   E4_ablation, E7_alpha, E9_synflood, cfs_py (E2b)
├── src/          # NS.PY simulation sources (anomon/sim, common)
├── results/      # output CSVs (one per experiment) -- cached, ready to plot
├── plots/        # plotting scripts + generated PDFs
├── traces/       # (place CAIDA / synthetic traces here)
└── logs/         # run logs
```

## Running the experiments

| ID | Command | Output | Manuscript |
|----|---------|--------|-----------|
| E1 | `cd baselines/E1_distribution/AnoTable && make && ./main` | `results/E1_ale_vs_mem.csv` | Fig. 10(a) |
| E2a | `python tools/control_overhead.py` | `results/E2a_control_overhead.csv` | Fig. 13(a) |
| E2b | `python baselines/cfs_py/run_e2b_cfs.py` | `results/E2b_cfs.csv` | Fig. 13(b) |
| E3 | `bash tools/run_e3_flowscale.sh` | `results/E3_flowscale.csv` | Fig. 13(c) |
| E4 | `cd baselines/E4_ablation && ./run_e4` | `results/E4_ablation_*.csv` | Fig. 10(c) |
| E5 | `bash tools/run_e5_shortlived.sh` | `results/E5_shortlived.csv` | Supplement |
| E7 | `cd baselines/E7_alpha && ./run_e7` | `results/E7_alpha.csv` | Fig. 10(b) |
| E8 | `bash tools/run_e8_grouping.sh` | `results/E8_grouping.csv` | Supplement |
| E9 | `cd baselines/E9_synflood && ./run_e9` | `results/E9_synflood*.csv` | Fig. 8(c) |
| E10 | `python tools/run_e10_fasttrigger.py` | `results/E10_fasttrigger.csv` | Fig. 14 |
| T1 | `python tools/draw_bucket_layout.py` | `plots/bucket_layout.pdf` | Fig. 6 |

The result CSVs are committed, so you can regenerate every figure without
re-running the (slow) simulations:

```bash
python plots/plot_unified.py     # E1,E2a,E2b,E3,E4,E7,E9,E10 in the paper style
python tools/draw_bucket_layout.py
```

## Key results

* **E1** — AnoTable attains **1.9–4.2×** lower per-flow distribution error (ALE)
  than FlowLens/SketchFeature at equal memory.
* **E2a** — layer-by-layer collection keeps the control-plane critical path
  bounded (~50 ms) up to `k=32` fat-trees, while sequential central analysis
  grows linearly.
* **E3** — AFG-detection F1 stays robust (**0.59–0.84**) across an 8× flow-count
  range at fixed memory.
* **E4** — for a tail-inflating anomaly only the `p90` quantile detects it
  (F1=1.0); count/mean/max and even `p99` fail.
* **E9** — SYN-flood victims are flagged with F1=1.0 once the flood exceeds the
  threshold (precision always 1.0).
* **E10** — fast-trigger captures anomalies as short as **~200 ms** and cuts the
  mean detection latency by **~20×** (2.5 s → 0.13 s).

## Notes for reproduction

* The shell wrappers assume the repository lives at its current path and that the
  `AnoMon` conda env exists; adjust the `OUT`/`cd` lines at the top of each
  `run_*.sh` if you relocate the repo.
* `plots/plot_unified.py` writes the PDFs both into `plots/` and into the paper's
  `pictures/` directory; edit the `PICS` constant if you only want local output.
