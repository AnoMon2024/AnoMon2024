// E4 (R2-4): why is per-flow DISTRIBUTION needed, beyond scalar counters?
// We model a transient-congestion anomaly that inflates the TAIL of the per-flow
// queuing-delay distribution (a fraction of packets see high delay) while the
// mean and max are only mildly affected and overlap with normal flows. We then
// detect the anomalous flows using different per-flow features and report the
// best achievable F1 of each:
//   count  : packet count            (no delay info)
//   mean   : average queuing delay    (scalar)
//   max    : maximum queuing delay    (scalar)
//   p90/p99: tail quantiles           (distribution)
// If the tail quantiles separate anomalous from normal flows far better than the
// scalar counters, then capturing the per-flow distribution (AnoTable/CellSketch)
// is necessary, not merely nice-to-have.
#include <bits/stdc++.h>
using namespace std;

static double quantile(vector<double> v, double q){ sort(v.begin(),v.end()); return v[(size_t)(v.size()*q)]; }

// best F1 over all thresholds for a 1-D feature (higher feature => more anomalous)
static double bestF1(const vector<double>& feat, const vector<int>& label){
    int P=accumulate(label.begin(),label.end(),0);
    vector<int> idx(feat.size()); iota(idx.begin(),idx.end(),0);
    sort(idx.begin(),idx.end(),[&](int a,int b){return feat[a]>feat[b];});
    int tp=0,fp=0; double best=0;
    for(int i=0;i<(int)idx.size();i++){
        if(label[idx[i]]) tp++; else fp++;
        double prec=tp/(double)(tp+fp), rec=tp/(double)P;
        double f1=(prec+rec)?2*prec*rec/(prec+rec):0;
        best=max(best,f1);
    }
    return best;
}

int main(int argc,char**argv){
    int n_normal = argc>1?atoi(argv[1]):1000;
    int n_anom   = argc>2?atoi(argv[2]):200;
    int K        = argc>3?atoi(argv[3]):500;     // packets per flow
    double tail_frac = argc>4?atof(argv[4]):0.15;// fraction of inflated packets in anomalous flows
    string out = argc>5?argv[5]:"../../results/E4_ablation.csv";
    mt19937 rng(2026);
    // base traffic; RARE extreme spikes shared by ALL flows (so max/p99 overlap);
    // anomalous flows add a moderate "congestion shoulder" that inflates the BULK
    // tail (p90) without changing the rare extreme spikes and only mildly the mean.
    lognormal_distribution<double> base(log(100.0),0.45);    // normal delay (us)
    lognormal_distribution<double> shoulder(log(350.0),0.30);// congestion shoulder
    lognormal_distribution<double> spike(log(1500.0),0.40);  // rare extreme (shared)
    uniform_real_distribution<double> U(0,1);
    const double spike_rate = 0.02;                          // both normal & anomalous

    vector<double> Fcount,Fmean,Fmax,Fp90,Fp99; vector<int> label;
    auto add_flow=[&](bool anom){
        vector<double> d(K);
        for(int i=0;i<K;i++){
            double u=U(rng);
            if(u<spike_rate)                 d[i]=spike(rng);            // shared rare spike
            else if(anom && u<spike_rate+tail_frac) d[i]=shoulder(rng); // anomaly: bulk-tail
            else                             d[i]=base(rng);
        }
        double s=0,mx=0; for(double x:d){s+=x; mx=max(mx,x);}
        Fcount.push_back(K);
        Fmean.push_back(s/K);
        Fmax.push_back(mx);
        Fp90.push_back(quantile(d,0.90));
        Fp99.push_back(quantile(d,0.99));
        label.push_back(anom?1:0);
    };
    for(int i=0;i<n_normal;i++) add_flow(false);
    for(int i=0;i<n_anom;i++)   add_flow(true);

    struct M{const char*name; vector<double>*f;};
    vector<M> ms={{"count",&Fcount},{"mean",&Fmean},{"max",&Fmax},{"p90",&Fp90},{"p99",&Fp99}};
    ofstream fo(out); fo<<"feature,bestF1\n";
    printf("=== distribution vs scalar ablation (tail_frac=%.2f) ===\n",tail_frac);
    for(auto&m:ms){ double f1=bestF1(*m.f,label); printf("%-6s bestF1=%.3f\n",m.name,f1); fo<<m.name<<','<<f1<<'\n'; }
    fo.close();
    return 0;
}
