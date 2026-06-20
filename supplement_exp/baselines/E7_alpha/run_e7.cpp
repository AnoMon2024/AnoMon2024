// E7 (R1-6): sensitivity of the geometric interval ratio alpha.
// We estimate the per-flow p95 inter-packet interval with a per-flow histogram
// whose r bins follow a GEOMETRIC sequence of ratio alpha, and report the ALE
// as a function of alpha (at several memory budgets). This empirically validates
// Theorem V.1: a smaller alpha gives finer resolution and lower relative error,
// but needs more counters (memory) to cover the same value range. Default alpha=2.
#include <bits/stdc++.h>
#include "Util.h"     // TUPLES, BOBHash
using namespace std;

static const int MAXIV = (1 << 23);

// per-flow geometric histogram, flows hashed to S slots, B bins each (counter=4B)
struct GeoHist {
    int S, B; double alpha; vector<double> edge; vector<uint32_t> h;
    GeoHist(size_t mem_bytes, int bins, double a): B(bins), alpha(a) {
        edge.assign(B+1,0);
        if (alpha==1.0) {                 // UNIFORM bins of equal width over [0,MAXIV)
            for (int i=0;i<=B;i++) edge[i] = (double)MAXIV*i/B;
        } else {                          // GEOMETRIC bins, finest bin width w=1 at the low end
            for (int i=0;i<=B;i++) edge[i] = (pow(alpha,i)-1)/(alpha-1); // 0,1,1+a,1+a+a^2,...
            if (edge[B] < MAXIV) edge[B] = MAXIV; // last bin absorbs the tail
        }
        S = max(1,(int)(mem_bytes/((size_t)B*4)));
        h.assign((size_t)S*B,0);
    }
    inline int slot(const TUPLES&f) const { return BOBHash(f,909)%S; }
    inline int bin(uint32_t x) const {
        // binary search over edges
        int lo=0, hi=B; while(lo<hi){int m=(lo+hi)/2; if(edge[m+1]<=x) lo=m+1; else hi=m;} return min(lo,B-1);
    }
    void insert(const TUPLES&f, uint32_t x){ uint32_t&c=h[(size_t)slot(f)*B+bin(x)]; if(c<0xffffffff)c++; }
    uint32_t query(const TUPLES&f, double q){
        uint32_t*hh=&h[(size_t)slot(f)*B]; long tot=0; for(int b=0;b<B;b++)tot+=hh[b];
        if(!tot)return 1; long tgt=(long)(tot*q),acc=0;
        for(int b=0;b<B;b++){acc+=hh[b]; if(acc>=tgt){double v=(edge[b]+edge[b+1])/2; return v<1?1:(uint32_t)v;}}
        double v=(edge[B-1]+edge[B])/2; return v<1?1:(uint32_t)v;
    }
};

struct Pkt{TUPLES key; uint32_t tick;};

int main(int argc,char**argv){
    string trace=argc>1?argv[1]:"../../traces/synth_caida.dat";
    string out=argc>2?argv[2]:"../../results/E7_alpha.csv";
    fprintf(stderr,"loading %s\n",trace.c_str());
    FILE*pf=fopen(trace.c_str(),"rb"); if(!pf){fprintf(stderr,"no trace\n");return 1;}
    vector<Pkt> data; char rec[21];
    while(fread(rec,1,21,pf)==21){Pkt p;memcpy(p.key.data,rec,13);double tt=*(double*)(rec+13);p.tick=(uint32_t)tt;data.push_back(p);}
    fclose(pf);
    unordered_map<TUPLES,vector<uint32_t>> gt; unordered_map<TUPLES,uint32_t> last; gt.reserve(1<<20);
    for(auto&p:data){auto it=last.find(p.key); if(it!=last.end()&&p.tick>it->second) gt[p.key].push_back(p.tick-it->second); last[p.key]=p.tick;}
    vector<const TUPLES*> big; unordered_map<TUPLES,uint32_t> tp95;
    for(auto&kv:gt) if(kv.second.size()>=1000){auto v=kv.second; sort(v.begin(),v.end()); tp95[kv.first]=v[(size_t)(v.size()*0.95)]; big.push_back(&kv.first);}
    fprintf(stderr,"%zu big flows\n",big.size());
    auto LE=[](uint32_t e,uint32_t t){return fabs(log2((double)e+1)-log2((double)t+1));};

    vector<double> alphas={1.0,1.5,2.0,4.0};   // 1.0 = UNIFORM baseline
    vector<int> mems={50,100,200};
    int B=32;
    ofstream fo(out); fo<<"memKB,alpha,bins,ALE\n";
    printf("memKB alpha  bins   ALE   (alpha=1.0 is uniform binning)\n");
    for(int memKB:mems) for(double a:alphas){
        GeoHist g((size_t)memKB*1024,B,a);
        unordered_map<TUPLES,uint32_t> lt; lt.reserve(1<<20);
        for(auto&p:data){auto it=lt.find(p.key); if(it!=lt.end()&&p.tick>it->second) g.insert(p.key,p.tick-it->second); lt[p.key]=p.tick;}
        double e=0; for(auto*k:big) e+=LE(g.query(*k,0.95),tp95[*k]); e/=big.size();
        printf("%-5d %-5.2f %-5d %.4f\n",memKB,a,B,e);
        fo<<memKB<<','<<a<<','<<B<<','<<e<<'\n';
    }
    fo.close(); fprintf(stderr,"wrote %s\n",out.c_str());
    return 0;
}
