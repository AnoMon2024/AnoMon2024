# AnoMon: Network-wide Measurement on Anomalies

This repository contains the source code, simulation/testbed artifacts, and the
**revision experiments** for our paper *"Network-wide Measurement on Anomalies"*
(AnoMon), submitted to *IEEE/ACM Transactions on Networking*.

## Introduction

Network measurement is crucial for successful network maintenance. The tension
between limited measurement resources and immense network traffic has always
been a great challenge: an ideal measurement system should keep its monitoring
overhead from growing with the traffic scale. Towards this goal, AnoMon is an
efficient and accurate network-wide measurement system. Its design philosophy is
**two-phase**: first identify the flow groups that carry abnormal traffic —
called **Abnormal Flow Groups (AFGs)** — with a cheap, always-on *passive*
measurement at the network edge (**AnoSketch**); then monitor the traffic of
those AFGs with fine-grained *active* measurement inside the network
(**AnoTable** with **CellSketch**), recording the per-flow per-hop attribute
distribution.

We fully implement an AnoMon prototype on a testbed of programmable switches and
run extensive experiments. AnoMon achieves up to **4.0× / 5.6×** higher accuracy
in locating anomalies than the always-on baselines LightGuardian and Marple, and
up to **3.9×** smaller bandwidth overhead than the trigger-based NetSeer.

## Repository layout

| Path | Contents |
|------|----------|
| `CPU/` | AnoSketch and AnoTable implemented on the CPU platform. |
| `NSPY/` | Implementation on the NS.PY network simulator. |
| `testbed/` | P4 / control-plane code for the Tofino testbed (10× Edgecore Wedge 100BF-32X switches, 8 end-hosts, FatTree). |
| `supplement_exp/` | **New revision experiments** (E1–E10) added for the TON major revision, with reproducible scripts. See [`supplement_exp/README.md`](supplement_exp/README.md). |
| `AnoMon_Supplementary.pdf` | Online-only supplement (algorithm pseudocode, proofs, extra examples). |

## Revision experiments (TON major revision)

All experiments added during the revision live under
[`supplement_exp/`](supplement_exp/) and are fully scripted. Each one maps to a
figure/table in the revised manuscript and to the reviewer comment it addresses:

| ID | Experiment | Manuscript | Addresses |
|----|------------|-----------|-----------|
| **E1** | AnoTable vs. FlowLens / SketchFeature (per-flow distribution ALE) | Fig. 10(a) | R2-1 |
| **E2a** | Control-plane overhead & scalability (fat-trees `k=4–32`) | Fig. 13(a) | R2-3 |
| **E2b** | Reimplemented CFS: cooperative flow coverage | Fig. 13(b) | R2-1 |
| **E3** | AFG detection F1 across an 8× flow-count range | Fig. 13(c) | R2-2 |
| **E4** | Distribution-vs-scalar ablation (only `p90` detects the anomaly) | Fig. 10(c) | R2-4 |
| **E5** | Short-lived anomaly duration sweep | Supplement | R3-3 |
| **E7** | Sensitivity to the geometric interval ratio `α` | Fig. 10(b) | R1-6 |
| **E8** | Dynamic AFG candidate-generation ablation | Supplement | R3-1 |
| **E9** | SYN-flood case study (feature extensibility) | Fig. 8(c) | R1-4 |
| **E10** | Optional fast-trigger mode for sub-epoch response | Fig. 14 | R3-3 |
| **T1** | AnoTable register layout on Tofino (schematic) | Fig. 6 / Table III | R1-5 |

## Quick start

```bash
# 1. Create the Python environment used for the simulation/analysis experiments
conda create -n AnoMon python=3.9 -y && conda activate AnoMon
pip install numpy scipy pandas matplotlib simpy networkx

# 2. Reproduce a self-contained simulation experiment (no external trace needed)
python supplement_exp/tools/run_e10_fasttrigger.py     # -> Fig. 14
python supplement_exp/tools/control_overhead.py        # -> Fig. 13(a)

# 3. Regenerate all revision figures from the cached result CSVs
python supplement_exp/plots/plot_unified.py
```

See [`supplement_exp/README.md`](supplement_exp/README.md) for the full
environment, the C++ baselines (E1/E4/E7/E9), the CAIDA-trace dependency of the
CPU experiments, and per-experiment run instructions.
