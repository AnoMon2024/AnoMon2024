// E3-coverage (R2-2): is AnoMon only effective for "hot/top" flow groups?
// We measure AnoSketch's subset-sum accuracy (ARE) for flow-group size estimation
// across query COVERAGE (top-300, top-1K, top-3K, ... all groups) and across
// prefix GRANULARITY (/16,/20,/24,/28). If AnoSketch is accurate even for ALL
// groups (not just the top ones), then AnoMon is not limited to hot flows, and
// /24 is merely one representative grouping rule rather than a system assumption.
//
// Self-contained: flows are synthesized with /24 source-prefix structure (Zipf
// group sizes and Zipf per-flow packet counts), inserted into AnoSketch, and the
// estimated per-group packet sum is compared against ground truth.
#include <bits/stdc++.h>
#include "param.h"
#include "Util.h"
#include "anosketch.h"
using namespace std;

struct Flow { TUPLES key; uint32_t pkts; uint32_t grp; };

static vector<Flow> gen_flows(int n_groups, int n_flows, double g_zipf, double f_zipf, uint32_t seed) {
    mt19937 rng(seed);
    // group sizes (number of flows per /24 group) ~ Zipf
    vector<double> gw(n_groups);
    for (int i = 0; i < n_groups; i++) gw[i] = 1.0 / pow(i + 1.0, g_zipf);
    discrete_distribution<int> gpick(gw.begin(), gw.end());
    // per-flow packet count ~ Zipf-ish (1..~10^4)
    auto pkt_of = [&](void)->uint32_t {
        double u = uniform_real_distribution<double>(0,1)(rng);
        return (uint32_t)max(1.0, pow(u, -1.0/ f_zipf));   // power-law tail
    };
    vector<uint32_t> prefix(n_groups);
    for (int i = 0; i < n_groups; i++) prefix[i] = (0x0A000000u | (i << 8)); // 10.x.x.0/24 distinct
    vector<Flow> flows; flows.reserve(n_flows);
    for (int i = 0; i < n_flows; i++) {
        int g = gpick(rng);
        uint32_t sip = prefix[g] | (rng() & 0xff);
        uint32_t dip = rng();
        TUPLES k(sip, dip, rng() & 0xffff, rng() & 0xffff, (rng() & 1) ? 6 : 17);
        flows.push_back({k, pkt_of(), (uint32_t)g});
    }
    return flows;
}

// ARE of subset-sum group-size estimation for the top-K groups under a srcIP mask
template<int BN, int MEM>
static void run_one(const vector<Flow>& flows, const vector<pair<string,uint32_t>>& masks,
                    const vector<int>& Ks, ofstream& fo, int memKB) {
    AnoSketch<BN, MEM>* sk = new AnoSketch<BN, MEM>();
    for (auto& f : flows) sk->insert(f.key, f.pkts);     // weighted insert (packet count)
    for (auto& [mname, mask] : masks) {
        // ground-truth group sizes under this mask
        unordered_map<uint32_t, double> truth; unordered_map<uint32_t, TUPLES> rep;
        for (auto& f : flows) { uint32_t g = f.key.srcIP() & mask; truth[g] += f.pkts; rep[g] = f.key; }
        vector<pair<double,uint32_t>> order;
        for (auto& kv : truth) order.push_back({kv.second, kv.first});
        sort(order.rbegin(), order.rend());
        int G = order.size();
        for (int K : Ks) {
            int kk = (K < 0 || K > G) ? G : K;
            double are = 0; int cnt = 0;
            for (int i = 0; i < kk; i++) {
                uint32_t g = order[i].second; double t = order[i].first;
                if (t <= 0) continue;
                double est = (double)sk->query_partial_key(rep[g], srcIP, mask);
                are += fabs(t - est) / t; cnt++;
            }
            are = cnt ? are / cnt : 0;
            string kl = (K < 0 || K > G) ? "all" : to_string(K);
            fo << memKB << ',' << mname << ',' << kl << ',' << kk << ',' << are << '\n';
            printf("mem=%dKB mask=%-4s topK=%-5s (%d grps) ARE=%.4f\n", memKB, mname.c_str(), kl.c_str(), kk, are);
        }
    }
    delete sk;
}

int main(int argc, char** argv) {
    int n_groups = argc > 1 ? atoi(argv[1]) : 5000;
    int n_flows  = argc > 2 ? atoi(argv[2]) : 50000;
    string out   = argc > 3 ? argv[3] : "../../results/E3_coverage.csv";
    fprintf(stderr, "generating %d flows over %d /24 groups...\n", n_flows, n_groups);
    auto flows = gen_flows(n_groups, n_flows, 1.1, 1.2, 2026);
    double totp = 0; for (auto& f : flows) totp += f.pkts;
    fprintf(stderr, "total packets ~ %.0f\n", totp);

    vector<pair<string,uint32_t>> masks = {
        {"/16", 0xffff0000u}, {"/20", 0xfffff000u}, {"/24", 0xffffff00u}, {"/28", 0xfffffff0u}};
    vector<int> Ks = {300, 1000, 3000, -1};   // -1 = all

    ofstream fo(out); fo << "memKB,mask,topK,n_groups,ARE\n";
    // memory sweep via template instantiation (bucket_num = MEM/500)
    printf("=== coverage & granularity (ARE) ===\n");
    run_one<100, 50000 >(flows, masks, Ks, fo, 50);
    run_one<200, 100000>(flows, masks, Ks, fo, 100);
    run_one<300, 150000>(flows, masks, Ks, fo, 150);
    run_one<400, 200000>(flows, masks, Ks, fo, 200);
    fo.close();
    fprintf(stderr, "wrote %s\n", out.c_str());
    return 0;
}
