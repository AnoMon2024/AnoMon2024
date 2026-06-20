#!/usr/bin/env python3
"""
E2a (R2-3 / AE): control-plane overhead & scalability of the central analyzer.

The reviewer's concern is that AnoMon "relies heavily on the central controller to
receive and analyze all tables and then notify each edge switch", so the overhead
"may grow significantly with the topology complexity". We answer this with the
complexity model of S VI and project it to larger fat-tree topologies, using the
per-table costs MEASURED on our 10-switch Tofino testbed (paper Fig.11) as anchors.

Fat-tree(k): edge=k^2/2, aggregation=k^2/2, core=k^2/4, total switches N_s=5k^2/4,
inside(agg+core)=3k^2/4, hosts=k^3/4. Topology depth (edge->agg->core) = 3 layers.

Anchors (from testbed, paper Fig.11, per-switch, at S_table=100KB):
  t_collect : time to read one switch's table to the analyzer        ~2.5 ms
  t_analyze : time to analyze one switch's table (scan buckets etc.)  ~14  ms  (100KB)
  S_table   : per-switch table size (collected bytes)                 100 KB
  S_rule    : per-AFG marking-rule entry                              ~8  B (match+action)

Two collection strategies:
  (a) naive sequential: analyzer processes switches one by one
        T_total = N_s * (t_collect + t_analyze)
  (b) layer-by-layer parallel (S VI-A): switches in the same layer are collected/
      analyzed concurrently; the critical path is the topology depth
        T_total ~= depth * (t_collect + t_analyze)   (depth=3, ~constant in k)
"""
import argparse, csv, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---- measured per-switch anchors (testbed, 100KB table) ----
T_COLLECT_MS = 2.5      # per-switch table collection
T_ANALYZE_MS = 14.0     # per-switch table analysis at 100KB
S_TABLE_KB   = 100.0    # per-switch collected bytes
S_RULE_B     = 8        # per-AFG marking-rule entry
DEPTH        = 3        # fat-tree edge->agg->core

def fattree(k):
    edge = k*k//2; agg = k*k//2; core = (k//2)*(k//2)
    return dict(k=k, edge=edge, agg=agg, core=core,
                total=edge+agg+core, inside=agg+core, hosts=k*k*k//4)

def project(ks, epoch_s, n_afg):
    rows = []
    for k in ks:
        t = fattree(k)
        Ns, Ne = t["total"], t["edge"]
        # collection bandwidth (all tables once per epoch), Mbps on control network
        B_collect = Ns * S_TABLE_KB*1024*8 / epoch_s / 1e6
        # notification bandwidth, Mbps
        B_notify  = Ne * n_afg * S_RULE_B*8 / epoch_s / 1e6
        # per-edge marking-table memory, bytes
        M_mark    = n_afg * S_RULE_B
        # analysis/collection latency
        T_seq   = Ns * (T_COLLECT_MS + T_ANALYZE_MS)          # ms, naive sequential
        T_layer = DEPTH * (T_COLLECT_MS + T_ANALYZE_MS)        # ms, layer-by-layer parallel
        rows.append(dict(k=k, switches=Ns, edge=Ne, hosts=t["hosts"],
                         B_collect_Mbps=round(B_collect,3), B_notify_Mbps=round(B_notify,4),
                         M_mark_B=M_mark, T_seq_ms=round(T_seq,1), T_layer_ms=round(T_layer,1),
                         epoch_s=epoch_s, n_afg=n_afg))
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ks", default="4,8,16,32")
    ap.add_argument("--epoch", type=float, default=5.0)
    ap.add_argument("--n_afg", type=int, default=50)
    ap.add_argument("--out", default="../results/E2a_control_overhead.csv")
    a = ap.parse_args()
    ks = [int(x) for x in a.ks.split(",")]
    rows = project(ks, a.epoch, a.n_afg)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(f"epoch={a.epoch}s, n_afg={a.n_afg}")
    print(f"{'k':>3} {'switches':>8} {'B_collect(Mbps)':>15} {'T_seq(ms)':>10} {'T_layer(ms)':>11}")
    for r in rows:
        print(f"{r['k']:>3} {r['switches']:>8} {r['B_collect_Mbps']:>15} {r['T_seq_ms']:>10} {r['T_layer_ms']:>11}")

    # ---- plot: analysis latency vs topology scale (seq vs layer-by-layer) ----
    sw = [r["switches"] for r in rows]
    plt.figure(figsize=(4.2,3.0))
    plt.plot(sw, [r["T_seq_ms"]/1000 for r in rows], "o-", color="#d62728", label="sequential")
    plt.plot(sw, [r["T_layer_ms"]/1000 for r in rows], "s-", color="#1f77b4", label="layer-by-layer")
    plt.axhline(a.epoch, ls="--", color="gray", label=f"epoch={a.epoch:.0f}s")
    plt.xlabel("# switches (fat-tree k=4,8,16,32)"); plt.ylabel("collect+analyze time (s)")
    plt.yscale("log"); plt.legend(fontsize=8); plt.grid(True, ls=":", alpha=0.5); plt.tight_layout()
    out_pdf = "../plots/E2a_control_overhead.pdf"
    os.makedirs(os.path.dirname(out_pdf), exist_ok=True)
    plt.savefig(out_pdf)
    for p in [out_pdf, "/data/jjc/AnoMon/AnoMon_TON25_Overleaf/pictures/E2a_control_overhead.pdf"]:
        try: plt.savefig(p); print("wrote", p)
        except Exception as e: print("skip", p, e)

if __name__ == "__main__":
    main()
