// E1: per-flow interval-distribution accuracy — AnoTable(CellSketch) vs
// FlowLens vs SketchFeature vs DDSketch, on a shared (synthetic) trace, with
// ONE identical ground-truth + ALE metric for every algorithm.
//
// Metric (matches the paper's Fig.8a "ALE"): for every flow with >=1000 pkts,
// estimate the 0.95-quantile of its inter-packet interval, and report
// ALE = mean_f | log2(est_p95+1) - log2(true_p95+1) |.
//
// Build: g++ -O2 -std=c++17 run_e1.cpp -I../baselines/E1_distribution/AnoTable -o run_e1
// Run:   ./run_e1 <trace.dat> <out.csv> <memKB1,memKB2,...>
#include <bits/stdc++.h>
#include "Util.h"          // TUPLES, BOBHash  (from E1_distribution/AnoTable)
#include "micro.h"         // MicroSketch / CellSketch (AnoTable)
#include "flowlens.h"
#include "sketchfeature.h"
using namespace std;

// ----- minimal faithful DDSketch (relative-error quantile sketch), per-flow
// copies hashed under a byte budget (as in the paper's DDSketch baseline) -----
struct DDBucket {
    static const int CAP = 400;
    struct Slot { uint32_t s, e, f; };
    Slot slot[CAP]; int n = 0; uint32_t tot = 0;
    void insert(uint32_t T) {
        tot++;
        for (int i = 0; i < n; i++) if (slot[i].s <= T && T < slot[i].e) { slot[i].f++; return; }
        if (n < CAP) { slot[n++] = {T, T + 1, 1}; sort(slot, slot + n, [](const Slot&a,const Slot&b){return a.s<b.s;}); }
        else { for (int i = 0; i < n; i++) if (T < slot[i].s) { slot[i].f++; return; } slot[n-1].f++; }
    }
    uint64_t query(double w) {
        long m = (long)(tot * w);
        for (int i = 0; i < n; i++) { m -= slot[i].f; if (m < 0) return (uint64_t)pow(1.5, (slot[i].s + slot[i].e) / 2.0); }
        return n ? (uint64_t)pow(1.5, (slot[n-1].s + slot[n-1].e) / 2.0) : 1;
    }
};
struct DDSketchAll {
    vector<DDBucket> b; size_t B;
    DDSketchAll(size_t mem_bytes) { B = max((size_t)1, mem_bytes / (DDBucket::CAP * sizeof(DDBucket::Slot))); b.resize(B); }
    void insert(const TUPLES &f, uint32_t interval) { uint32_t T = (uint32_t)(log((double)max(1u,interval)) / log(1.5) + 0.5); b[BOBHash(f, 1) % B].insert(T); }
    uint32_t query(const TUPLES &f, double w) { return (uint32_t)b[BOBHash(f, 1) % B].query(w); }
};

// ----- AnoTable p95 from CellSketch histogram (value,count) pairs -----
static uint32_t anotable_p95(MicroSketch &mt, const TUPLES &f, double w) {
    vector<pair<int,int>> est = mt.query_delay(f);     // (value, count)
    if (est.empty()) return 1;
    sort(est.begin(), est.end());
    long tot = 0; for (auto &p : est) tot += p.second;
    if (tot == 0) return 1;
    long target = (long)(tot * w), acc = 0;
    for (auto &p : est) { acc += p.second; if (acc >= target) return p.first ? (uint32_t)p.first : 1; }
    return est.back().first ? (uint32_t)est.back().first : 1;
}

struct Pkt { TUPLES key; uint32_t tick; };

int main(int argc, char **argv) {
    string trace = argc > 1 ? argv[1] : "../traces/synth_caida.dat";
    string out   = argc > 2 ? argv[2] : "../results/E1_ale_vs_mem.csv";
    vector<int> mems;
    if (argc > 3) { stringstream ss(argv[3]); string t; while (getline(ss, t, ',')) mems.push_back(stoi(t)); }
    else mems = {50, 100, 150, 200, 300, 400};
    int FL_BINS = argc > 4 ? atoi(argv[4]) : 256;   // FlowLens bins per marker
    int SF_QL   = argc > 5 ? atoi(argv[5]) : 50;    // SketchFeature uniform levels
    fprintf(stderr, "FlowLens bins=%d, SketchFeature num_ql=%d\n", FL_BINS, SF_QL);

    // ---- load trace (21-byte records: 13B key + 8B double absolute tick) ----
    fprintf(stderr, "loading %s ...\n", trace.c_str());
    FILE *pf = fopen(trace.c_str(), "rb");
    if (!pf) { fprintf(stderr, "trace not found\n"); return 1; }
    vector<Pkt> data; char rec[21];
    while (fread(rec, 1, 21, pf) == 21) {
        Pkt p; memcpy(p.key.data, rec, 13);
        double tt = *(double*)(rec + 13); p.tick = (uint32_t)tt;
        data.push_back(p);
    }
    fclose(pf);
    fprintf(stderr, "loaded %zu packets\n", data.size());

    // ---- ground truth: per-flow intervals + sizes ----
    unordered_map<TUPLES, vector<uint32_t>> gt;
    unordered_map<TUPLES, uint32_t> last;
    gt.reserve(1 << 20);
    for (auto &p : data) {
        auto it = last.find(p.key);
        if (it != last.end() && p.tick > it->second) gt[p.key].push_back(p.tick - it->second);
        last[p.key] = p.tick;
    }
    vector<const TUPLES*> bigflows;
    for (auto &kv : gt) if (kv.second.size() >= 1000) bigflows.push_back(&kv.first);
    // precompute true p95
    unordered_map<TUPLES, uint32_t> truep95;
    for (auto *k : bigflows) { auto v = gt[*k]; sort(v.begin(), v.end()); truep95[*k] = v[(size_t)(v.size() * 0.95)]; }
    fprintf(stderr, "%zu flows with >=1000 pkts\n", bigflows.size());

    auto LE = [](uint32_t est, uint32_t tru) { return fabs(log2((double)est + 1) - log2((double)tru + 1)); };

    ofstream fo(out);
    fo << "memKB,AnoTable,FlowLens,SketchFeature,DDSketch\n";
    printf("memKB    AnoTable  FlowLens  SketchFeature  DDSketch\n");
    for (int memKB : mems) {
        size_t mem = (size_t)memKB * 1024;
        // build
        MicroSketch anot((int)mem);
        FlowLens fl(mem, FL_BINS);
        SketchFeature sf(mem, 3, 3, SF_QL);
        DDSketchAll dd(mem);
        // replay
        unordered_map<TUPLES, uint32_t> lt; lt.reserve(1 << 20);
        for (auto &p : data) {
            auto it = lt.find(p.key);
            if (it != lt.end() && p.tick > it->second) {
                uint32_t iv = p.tick - it->second;
                anot.insert(p.key, p.tick, iv);
                fl.insert(p.key, iv);
                sf.insert(p.key, iv);
                dd.insert(p.key, iv);
            }
            lt[p.key] = p.tick;
        }
        // evaluate
        double e_a = 0, e_f = 0, e_s = 0, e_d = 0; int n = bigflows.size();
        for (auto *k : bigflows) {
            uint32_t tp = truep95[*k];
            e_a += LE(anotable_p95(anot, *k, 0.95), tp);
            e_f += LE(fl.query(*k, 0.95), tp);
            e_s += LE(sf.query(*k, 0.95), tp);
            e_d += LE(dd.query(*k, 0.95), tp);
        }
        e_a/=n; e_f/=n; e_s/=n; e_d/=n;
        printf("%-8d %-9.4f %-9.4f %-13.4f %-9.4f\n", memKB, e_a, e_f, e_s, e_d);
        fo << memKB << ',' << e_a << ',' << e_f << ',' << e_s << ',' << e_d << '\n';
    }
    fo.close();
    fprintf(stderr, "wrote %s\n", out.c_str());
    return 0;
}
