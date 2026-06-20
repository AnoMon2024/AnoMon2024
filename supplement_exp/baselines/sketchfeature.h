#ifndef SKETCHFEATURE_H
#define SKETCHFEATURE_H
// SketchFeature (NDSS'25) baseline for per-flow interval-distribution estimation.
//
// Faithful C++ port of RevisionCompareRepo/SketchFeature/CPU/sketchfeature.py:
//   - The attribute range [min_q, max_q] is split into num_ql UNIFORM levels
//     (np.linspace); get_ql(value) returns the level index (uniform binning).
//   - encoding(flow,value): ql=get_ql(value); set d_bf Bloom bits at
//     hash_mt(flow,ql,i)%w_bf; increment d CM counters at hash(flow,ql,i)%w.
//   - decoding(flow,ql): Bloom membership test; if present return min over d CM
//     rows (the count of packets of `flow` whose value falls in level ql).
//   - Memory: total bits split into Bloom (m_bf) and CM (m-m_bf); w=cm_bits/32/d
//     (32-bit counters), w_bf=bloom_bits/d_bf.
// The UNIFORM levels are the key contrast vs CellSketch's geometric levels:
// on heavy-tailed intervals uniform bins waste resolution in the dense small
// region and over-allocate the sparse tail.
//
// Per-flow quantile query: read the count of every level via decoding(), form
// the histogram over levels, and return the w-quantile level's representative
// value (raw interval), matching the harness interface.
#include "Util.h"
#include <cstdint>
#include <cstring>
#include <vector>

class SketchFeature {
public:
    int d, d_bf, num_ql;
    double min_q, max_q;
    size_t w, w_bf;
    std::vector<std::vector<uint32_t>> cm;     // d x w
    std::vector<std::vector<uint8_t>>  bf;     // d_bf x w_bf

    // hash over (flow, ql, row, tag): tag distinguishes CM (0) vs Bloom-membership (137)
    struct HKey { uint8_t key[13]; uint32_t ql; uint32_t mix; };
    static inline uint32_t hkhash(const TUPLES &f, uint32_t ql, uint32_t i, uint32_t tag) {
        HKey hk; memcpy(hk.key, f.data, 13); hk.ql = ql; hk.mix = (i + tag);
        return BOBHash(hk, 0);
    }

    SketchFeature(size_t mem_bytes, int d_ = 3, int d_bf_ = 3, int num_ql_ = 50,
                  double min_q_ = 0, double max_q_ = (1 << 23), double bloom_frac = 1.0/3.0) {
        d = d_; d_bf = d_bf_; num_ql = num_ql_; min_q = min_q_; max_q = max_q_;
        size_t total_bits = mem_bytes * 8;
        size_t bloom_bits = (size_t)(total_bits * bloom_frac);
        size_t cm_bits = total_bits - bloom_bits;
        w = cm_bits / 32 / d; if (w < 1) w = 1;
        w_bf = bloom_bits / d_bf; if (w_bf < 1) w_bf = 1;
        cm.assign(d, std::vector<uint32_t>(w, 0));
        bf.assign(d_bf, std::vector<uint8_t>(w_bf, 0));
    }

    inline int get_ql(double value) const {
        if (value <= min_q) return 0;
        if (value >= max_q) return num_ql - 1;
        int q = (int)((value - min_q) / (max_q - min_q) * num_ql);
        if (q < 0) q = 0; if (q >= num_ql) q = num_ql - 1;
        return q;
    }
    inline double ql_value(int ql) const {   // representative (midpoint) raw value of a level
        double width = (max_q - min_q) / num_ql;
        return min_q + (ql + 0.5) * width;
    }

    void insert(const TUPLES &f, uint32_t interval) {
        int ql = get_ql((double)interval);
        for (int i = 0; i < d_bf; i++) bf[i][hkhash(f, ql, i, 137) % w_bf] = 1;
        for (int i = 0; i < d; i++)    cm[i][hkhash(f, ql, i, 0)   % w] += 1;
    }

    bool membership(const TUPLES &f, int ql) {
        for (int i = 0; i < d_bf; i++)
            if (bf[i][hkhash(f, ql, i, 137) % w_bf] == 0) return false;
        return true;
    }
    uint32_t decode(const TUPLES &f, int ql) {
        if (!membership(f, ql)) return 0;
        uint32_t v = 0xFFFFFFFF;
        for (int i = 0; i < d; i++) {
            uint32_t c = cm[i][hkhash(f, ql, i, 0) % w];
            if (c < v) v = c;
        }
        return v;
    }

    uint32_t query(const TUPLES &f, double w_q) {
        long tot = 0;
        std::vector<uint32_t> cnt(num_ql);
        for (int ql = 0; ql < num_ql; ql++) { cnt[ql] = decode(f, ql); tot += cnt[ql]; }
        if (tot == 0) return 1;
        long target = (long)(tot * w_q), acc = 0;
        for (int ql = 0; ql < num_ql; ql++) {
            acc += cnt[ql];
            if (acc >= target) { double v = ql_value(ql); return v < 1 ? 1 : (uint32_t)v; }
        }
        double v = ql_value(num_ql - 1); return v < 1 ? 1 : (uint32_t)v;
    }
};

#endif
