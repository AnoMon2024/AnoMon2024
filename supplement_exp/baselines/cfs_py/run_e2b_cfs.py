#!/usr/bin/env python3
"""
E2b (R2-1 system line): Python reimplementation of CFS (Cooperative Network-wide
Flow Selection, IWQoS'20) -- the Java original is in RevisionCompareRepo/CFS.

CFS measures network-wide FLOW COVERAGE: given `cells` per-switch counters, what
fraction of distinct flows can be monitored. The key mechanism (faithful to
FatTree.addFlow + Network.compine + CFSswitch): every flow traverses a path of
1/3/5 switches; each switch keeps its top-`cells` flows by a global priority.
- CFS: each flow is made the RESPONSIBILITY of exactly one switch on its path
  (chosen routing-obliviously by a hash of the flow id), eliminating redundancy
  -> coverage approaches the optimal cells*N_switch/N_flow.
- CFS-FR (Flow-Radar): every on-path switch monitors independently, so a flow can
  occupy a counter at several switches -> redundancy -> lower distinct coverage.

We reproduce CFS's headline result (CFS coverage >> Flow-Radar, near optimal) and
use it to position AnoMon: AnoMon does NOT aim to cover all flows; it selectively
monitors only AFG flows, so for the anomaly task its effective coverage need is the
(small) AFG fraction rather than all flows.
"""
import argparse, csv, hashlib, os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

def H(*xs):
    return int(hashlib.md5(("_".join(map(str,xs))).encode()).hexdigest(), 16)

def fattree_path(s, d, k, N_edge, N_agg, N_core):
    """Return the list of switch ids on the flow's path (edge..core..edge)."""
    h1, h2 = H('p',s)% (k), H('p',d)%(k)          # pods
    e1, e2 = H('e',s)%(k//2), H('e',d)%(k//2)     # edges within pod
    if h1==h2 and e1==e2:
        return [h1*(k//2)+e1]                      # same edge: 1 switch
    if h1==h2:
        agg = N_edge + h1*(k//2) + (H('a',s)%(k//2))
        return [h1*(k//2)+e1, agg, h1*(k//2)+e2]   # same pod: 3 switches
    a1 = N_edge + h1*(k//2) + (H('a',s)%(k//2))
    a2 = N_edge + h2*(k//2) + (H('a',d)%(k//2))
    core = N_edge + N_agg + (H('c',s,d)%N_core)
    return [h1*(k//2)+e1, a1, core, a2, h2*(k//2)+e2]

def coverage(n_flows, cells, k, seed=1):
    N_edge=k*k//2; N_agg=k*k//2; N_core=(k//2)*(k//2); N_sw=N_edge+N_agg+N_core
    # generate flows + paths + global priority
    paths={}; prio={}
    for f in range(n_flows):
        s=H('s',seed,f)%100000; d=H('d',seed,f)%100000
        paths[f]=fattree_path(s,d,k,N_edge,N_agg,N_core); prio[f]=H('prio',f)
    # CFS: each flow responsible to one switch on its path (hash % path_len)
    resp={}  # switch -> list of (prio,flow)
    for f,p in paths.items():
        sw=p[prio[f]%len(p)]; resp.setdefault(sw,[]).append((prio[f],f))
    cfs=set()
    for sw,lst in resp.items():
        lst.sort(reverse=True)
        for _,f in lst[:cells]: cfs.add(f)
    # Flow-Radar: every on-path switch independently keeps top-cells passing flows
    passing={}
    for f,p in paths.items():
        for sw in p: passing.setdefault(sw,[]).append((prio[f],f))
    fr=set()
    for sw,lst in passing.items():
        lst.sort(reverse=True)
        for _,f in lst[:cells]: fr.add(f)
    optimal=min(1.0, cells*N_sw/n_flows)
    return len(cfs)/n_flows, len(fr)/n_flows, optimal, N_sw

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--n_flows", type=int, default=200000)
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--out", default="../../results/E2b_cfs.csv")
    a=ap.parse_args()
    cells_list=[200,500,1000,2000,4000]
    rows=[]
    print(f"{'cells':>6} {'CFS':>8} {'CFS-FR':>8} {'Optimal':>8}")
    for c in cells_list:
        cfs,fr,opt,N=coverage(a.n_flows,c,a.k)
        rows.append(dict(cells=c,N_switch=N,CFS=round(cfs,4),CFS_FR=round(fr,4),Optimal=round(opt,4)))
        print(f"{c:>6} {cfs:>8.4f} {fr:>8.4f} {opt:>8.4f}")
    os.makedirs(os.path.dirname(a.out),exist_ok=True)
    with open(a.out,"w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    # plot
    cs=[r["cells"] for r in rows]
    plt.figure(figsize=(4.3,3.0))
    plt.plot(cs,[r["Optimal"] for r in rows],"k--",label="Optimal")
    plt.plot(cs,[r["CFS"] for r in rows],"o-",color="#d62728",label="CFS")
    plt.plot(cs,[r["CFS_FR"] for r in rows],"s-",color="#1f77b4",label="CFS-FR (Flow-Radar)")
    plt.xlabel("counters per switch"); plt.ylabel("flow coverage")
    plt.legend(fontsize=8); plt.grid(True,ls=":",alpha=0.5); plt.tight_layout()
    for p in ["../../plots/E2b_cfs.pdf","/data/jjc/AnoMon/AnoMon_TON25_Overleaf/pictures/E2b_cfs.pdf"]:
        plt.savefig(p); print("wrote",p)

if __name__=="__main__":
    main()
