#!/usr/bin/env python3
"""
Synthetic CAIDA-format trace generator for AnoMon supplement experiments.

WHY: The real CAIDA2018 trace is not available on this host. We synthesize a
trace whose *per-flow inter-packet-interval distributions* are heavy-tailed and
span multiple orders of magnitude across flows — the exact property the paper
relies on to motivate geometric (relative-error) binning in CellSketch and that
makes equi-width (FlowLens) / uniform (SketchFeature) binning suffer.

Record format (21 bytes, little-endian), shared by all E1 baselines:
    [0:13]  13-byte 5-tuple key  = srcIP(4) dstIP(4) srcPort(2) dstPort(2) proto(1)
    [13:21] 8-byte double        = absolute arrival time in *ticks* (1 tick = 100 ns)
Records are globally sorted by arrival time (interleaved across flows), exactly
like a real packet capture.

Flow model:
  - Flow sizes ~ Zipf(s): a few elephant flows (>=1000 pkts, used by the ALE
    metric) and many mice.
  - Each flow f has a base interval scale mu_f drawn log-uniformly over
    [MIN_SCALE, MAX_SCALE] ticks  -> cross-flow multi-scale.
  - Within a flow, intervals ~ lognormal(log(mu_f), sigma) -> heavy tail,
    intervals span orders of magnitude (the skew geometric bins exploit).
"""
import argparse, struct, numpy as np, os

MAX_INTERVAL = (1 << 23)          # matches CellSketch::MAX_INTERVAL
MIN_SCALE, MAX_SCALE = 8.0, 2_000_000.0   # per-flow base interval scales (ticks)

def gen(n_flows, n_packets, zipf_s, sigma, seed, out_path):
    rng = np.random.default_rng(seed)

    # ---- flow sizes via Zipf, normalized to ~n_packets total ----
    ranks = np.arange(1, n_flows + 1)
    w = 1.0 / np.power(ranks, zipf_s)
    w /= w.sum()
    sizes = np.maximum(1, np.round(w * n_packets).astype(np.int64))
    rng.shuffle(sizes)
    total = int(sizes.sum())

    # ---- per-flow 5-tuple keys ----
    src = rng.integers(0, 2**32, size=n_flows, dtype=np.uint64)
    dst = rng.integers(0, 2**32, size=n_flows, dtype=np.uint64)
    sport = rng.integers(0, 2**16, size=n_flows, dtype=np.uint64)
    dport = rng.integers(0, 2**16, size=n_flows, dtype=np.uint64)
    proto = rng.choice([6, 17], size=n_flows).astype(np.uint64)

    # ---- per-flow base interval scale (log-uniform => multi-scale) ----
    mu = np.exp(rng.uniform(np.log(MIN_SCALE), np.log(MAX_SCALE), size=n_flows))

    # ---- generate (time, flow) events ----
    times = np.empty(total, dtype=np.float64)
    fids  = np.empty(total, dtype=np.int64)
    pos = 0
    for f in range(n_flows):
        c = int(sizes[f])
        # heavy-tailed intervals around the flow's scale
        iv = np.exp(rng.normal(np.log(mu[f]), sigma, size=c))
        iv = np.clip(iv, 1, MAX_INTERVAL)
        start = rng.uniform(0, 1_000_000)
        t = start + np.cumsum(iv)
        times[pos:pos+c] = t
        fids[pos:pos+c] = f
        pos += c

    order = np.argsort(times, kind="stable")
    times = times[order]
    fids = fids[order]

    # ---- write 21-byte records ----
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "wb") as fo:
        buf = bytearray()
        for i in range(total):
            f = int(fids[i])
            key = struct.pack("<IIHHB", int(src[f]) & 0xFFFFFFFF, int(dst[f]) & 0xFFFFFFFF,
                              int(sport[f]) & 0xFFFF, int(dport[f]) & 0xFFFF, int(proto[f]) & 0xFF)
            assert len(key) == 13
            buf += key + struct.pack("<d", float(times[i]))
            if len(buf) > (1 << 20):
                fo.write(buf); buf = bytearray()
        fo.write(buf)

    n_big = int((sizes >= 1000).sum())
    print(f"wrote {total} packets, {n_flows} flows, {n_big} flows with >=1000 pkts -> {out_path}")
    print(f"size sum={total}, max flow={int(sizes.max())}, file={os.path.getsize(out_path)} bytes")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n_flows", type=int, default=50000)
    ap.add_argument("--n_packets", type=int, default=5_000_000)
    ap.add_argument("--zipf_s", type=float, default=1.10)
    ap.add_argument("--sigma", type=float, default=1.6, help="per-flow lognormal interval sigma (skew)")
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--out", type=str, default="../traces/synth_caida.dat")
    a = ap.parse_args()
    gen(a.n_flows, a.n_packets, a.zipf_s, a.sigma, a.seed, a.out)
