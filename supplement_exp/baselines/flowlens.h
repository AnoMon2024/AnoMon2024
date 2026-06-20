#ifndef FLOWLENS_H
#define FLOWLENS_H
// FlowLens (NDSS'21) baseline for per-flow interval-distribution estimation.
//
// Faithful to the FlowLens "flow marker accumulator" (flowlens-v1model.p4):
//   - Each flow keeps an EQUI-WIDTH quantized histogram ("flow marker"): the
//     P4 marker computes binIndex = value >> BIN_WIDTH_SHIFT (power-of-2 bins)
//     and increments a 16-bit grid counter at (flow_offset + binIndex).
//   - Under a fixed memory budget we cannot store one marker per live flow, so
//     (exactly as the AnoMon paper budgets DDSketch/KLL/GK) we instantiate S
//     marker slots and hash each flow to a slot; colliding flows share a marker.
//   - Truncation in FlowLens keeps only the most informative bins, chosen
//     offline from labels. CAIDA has no such labels, so we keep the full
//     equi-width grid (no supervised truncation). This is the canonical
//     equi-width behaviour whose weakness on skewed data the paper highlights.
//
// Interface mirrors the harness: ctor(mem_bytes), insert(flow,interval),
// query(flow, w) -> raw w-quantile interval value.
#include "Util.h"
#include <cstdint>
#include <cstring>

class FlowLens {
public:
    int S;            // number of marker slots (flow copies)
    int B;            // bins per marker (grid width)
    int shift;        // power-of-2 bin width = 1<<shift
    uint16_t *hist;   // S*B 16-bit counters (as in P4 reg_grid<bit<16>>)

    FlowLens(size_t mem_bytes, int bins = 256, int max_interval = (1 << 23)) {
        B = bins;
        // pick power-of-2 bin width so B bins cover [0, max_interval)
        shift = 0;
        while ((((size_t)B) << shift) < (size_t)max_interval) shift++;
        S = (int)(mem_bytes / ((size_t)B * sizeof(uint16_t)));
        if (S < 1) S = 1;
        hist = new uint16_t[(size_t)S * B];
        memset(hist, 0, (size_t)S * B * sizeof(uint16_t));
    }
    ~FlowLens() { delete[] hist; }

    inline int slot_of(const TUPLES &f) const { return BOBHash(f, 777) % S; }

    void insert(const TUPLES &f, uint32_t interval) {
        int b = interval >> shift;
        if (b >= B) b = B - 1;
        uint16_t &c = hist[(size_t)slot_of(f) * B + b];
        if (c < 0xFFFF) c++;
    }

    uint32_t query(const TUPLES &f, double w) {
        uint16_t *h = &hist[(size_t)slot_of(f) * B];
        long tot = 0;
        for (int b = 0; b < B; b++) tot += h[b];
        if (tot == 0) return 1;
        long target = (long)(tot * w);
        long acc = 0;
        for (int b = 0; b < B; b++) {
            acc += h[b];
            if (acc >= target) {
                uint64_t lo = ((uint64_t)b) << shift;
                uint64_t hi = (((uint64_t)b + 1) << shift) - 1;
                uint64_t mid = (lo + hi) / 2;
                return mid ? (uint32_t)mid : 1;
            }
        }
        uint64_t v = ((uint64_t)(B - 1)) << shift;
        return v ? (uint32_t)v : 1;
    }
};

#endif
