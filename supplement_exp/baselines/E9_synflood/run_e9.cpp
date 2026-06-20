// E9 (R1-4): extensibility of AnoSketch to volume/security anomalies -- a
// SYN-flood case study. We configure the edge to insert ONLY SYN packets into a
// dedicated AnoSketch, and the analyzer queries destination /24 groups: a group
// whose SYN subset-sum exceeds a threshold is flagged as a SYN-flood AFG.
// We report the AFG detection F1 vs memory. This shows AnoSketch is a general
// arbitrary-flow-set event-count estimator, not limited to drop/latency signals.
//
// Workload: many normal flows each send a few SYNs to a random destination;
// a few victim /24 destinations additionally receive a flood of SYNs from many
// spoofed sources (the classic SYN-flood pattern: many distinct src -> one dst).
#include <bits/stdc++.h>
#include "param.h"
#include "Util.h"
#include "anosketch.h"
using namespace std;

struct SynFlow { TUPLES key; uint32_t syn; };

static vector<SynFlow> gen(int n_dst, int n_normal, int n_victim, int flood_per_victim, uint32_t seed,
                           set<uint32_t>& victim_grp) {
    mt19937 rng(seed);
    vector<uint32_t> dpref(n_dst);
    for (int i=0;i<n_dst;i++) dpref[i] = (0x0B000000u | (i<<8));   // 11.x.x.0/24 destinations
    vector<SynFlow> v;
    // normal: each flow = (random src, random dst), 1-3 SYNs
    for (int i=0;i<n_normal;i++) {
        int g = rng()%n_dst; uint32_t dip = dpref[g] | (rng()&0xff);
        TUPLES k(rng(), dip, rng()&0xffff, rng()&0xffff, 6);
        v.push_back({k, 1u + (rng()%3)});
    }
    // pick victim groups, flood them with many spoofed-src single-SYN flows
    vector<int> idx(n_dst); iota(idx.begin(),idx.end(),0); shuffle(idx.begin(),idx.end(),rng);
    for (int j=0;j<n_victim;j++) {
        int g = idx[j]; victim_grp.insert(dpref[g] & 0xffffff00u);
        for (int f=0; f<flood_per_victim; f++) {
            uint32_t dip = dpref[g] | (rng()&0xff);
            TUPLES k(rng(), dip, rng()&0xffff, 80, 6);  // spoofed src -> victim:80
            v.push_back({k, 1u});
        }
    }
    return v;
}

template<int BN, int MEM>
static void run_one(const vector<SynFlow>& flows, uint32_t mask, uint32_t thr,
                    const set<uint32_t>& victim, ofstream& fo, int memKB) {
    AnoSketch<BN,MEM>* sk = new AnoSketch<BN,MEM>();
    for (auto& f : flows) sk->insert(f.key, f.syn);
    // estimate per-dst-group SYN sum from ONE query_all()
    HashMap rec = sk->query_all();
    unordered_map<uint32_t,double> est;
    for (auto& kv : rec) est[kv.first.dstIP() & mask] += kv.second;
    // flag groups over threshold
    set<uint32_t> flagged;
    for (auto& kv : est) if (kv.second > thr) flagged.insert(kv.first);
    // F1 vs victim ground truth
    int tp=0; for (auto g: flagged) if (victim.count(g)) tp++;
    double prec = flagged.empty()?0:(double)tp/flagged.size();
    double rec_=  victim.empty()?0:(double)tp/victim.size();
    double f1 = (prec+rec_)?2*prec*rec_/(prec+rec_):0;
    fo<<memKB<<','<<thr<<','<<prec<<','<<rec_<<','<<f1<<'\n';
    printf("mem=%dKB thr=%u  prec=%.3f recall=%.3f F1=%.3f (flagged=%zu victim=%zu)\n",
           memKB, thr, prec, rec_, f1, flagged.size(), victim.size());
    delete sk;
}

int main(int argc,char**argv){
    int n_dst = argc>1?atoi(argv[1]):2000;
    int n_normal = argc>2?atoi(argv[2]):40000;
    int n_victim = argc>3?atoi(argv[3]):10;
    int flood = argc>4?atoi(argv[4]):3000;
    string out = argc>5?argv[5]:"../../results/E9_synflood.csv";
    set<uint32_t> victim;
    auto flows = gen(n_dst, n_normal, n_victim, flood, 2026, victim);
    fprintf(stderr,"flows=%zu victims=%zu flood_per_victim=%d\n", flows.size(), victim.size(), flood);
    uint32_t mask = 0xffffff00u;            // dst /24 groups
    uint32_t thr  = (uint32_t)(flood*0.5);  // detect groups with clearly elevated SYN count
    ofstream fo(out); fo<<"memKB,threshold,prec,recall,F1\n";
    printf("=== SYN-flood AFG detection vs memory (dst /24, flood=%d) ===\n", flood);
    run_one<100,50000 >(flows,mask,thr,victim,fo,50);
    run_one<200,100000>(flows,mask,thr,victim,fo,100);
    run_one<300,150000>(flows,mask,thr,victim,fo,150);
    run_one<400,200000>(flows,mask,thr,victim,fo,200);
    fo.close();

    // flood-intensity sweep at fixed 100KB memory and a FIXED threshold (above
    // the normal SYN background): shows the minimum flood intensity that AnoMon
    // can flag as a SYN-flood AFG.
    string out2 = "../../results/E9_synflood_intensity.csv";
    ofstream fo2(out2); fo2<<"flood,threshold,prec,recall,F1\n";
    uint32_t fixed_thr = 300;               // normal per-/24 SYN background is ~tens
    printf("=== SYN-flood AFG detection vs flood intensity (100KB, thr=%u) ===\n", fixed_thr);
    for (int fl : {50,100,200,400,800,1600,3000}) {
        set<uint32_t> vic2;
        auto fw = gen(n_dst, n_normal, n_victim, fl, 2026, vic2);
        AnoSketch<200,100000>* sk = new AnoSketch<200,100000>();
        for (auto& f : fw) sk->insert(f.key, f.syn);
        HashMap rec = sk->query_all();
        unordered_map<uint32_t,double> est;
        for (auto& kv : rec) est[kv.first.dstIP() & mask] += kv.second;
        set<uint32_t> flagged;
        for (auto& kv : est) if (kv.second > fixed_thr) flagged.insert(kv.first);
        int tp=0; for (auto g: flagged) if (vic2.count(g)) tp++;
        double p = flagged.empty()?0:(double)tp/flagged.size();
        double r = vic2.empty()?0:(double)tp/vic2.size();
        double f1=(p+r)?2*p*r/(p+r):0;
        printf("flood=%-5d  prec=%.3f recall=%.3f F1=%.3f\n", fl, p, r, f1);
        fo2<<fl<<','<<fixed_thr<<','<<p<<','<<r<<','<<f1<<'\n';
        delete sk;
    }
    fo2.close();
    return 0;
}
