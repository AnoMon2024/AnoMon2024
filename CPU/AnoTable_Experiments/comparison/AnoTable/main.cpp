#include "micro.h"
#include "trace.h"
#include <bits/stdc++.h>
using namespace std;

const int MEMORY = 1000000;
ofstream fout("CellSketch_ALE.txt");

double calc_ale(const multiset<uint32_t> &real, const vector<pair<int, int>> &est) {
    int sum = 0, tot = 0;
    for (auto [avg, cnt]: est) {
        tot += cnt;
    }
    vector<pair<double, double>> points;
    points.push_back(make_pair(0, 0));
    for (auto [avg, cnt]: est) {
        assert(cnt != 0);
        sum += cnt / 2;
        double q = (double)sum / tot;
        points.push_back(make_pair(log10(avg), q));
        sum += (cnt + 1) / 2;
    }
    points.push_back(make_pair(log10(1 << 23), 1));

    tot = real.size();
    vector<int> interval_vec;
    for (auto interval: real) {
        interval_vec.push_back(interval);
    }

    int n = interval_vec.size();
    double query_p = 0.95;
    int query_idx = n * query_p;
    int qx = log10(interval_vec[query_idx]);
    for (unsigned i = 0; i < points.size(); i++) {
        if (i+1 == points.size() || points[i].first <= qx && qx <= points[i+1].first) {
            double est_y = i+1 == points.size() ? 1 : \
                        points[i].second + (qx - points[i].first)\
                        * (points[i+1].second - points[i].second)\
                        / (points[i+1].first - points[i].first);
            int est = est_y * n;
            double err = fabs(log2(est+1) - log2(query_idx+1));
            // fout << est << ' ' << query_idx << ' ' << n << endl;
            return err;
        }
    }
    return -10000000;
}


double distribution_estimation(int memory) {
    MicroSketch micro(memory);
    vector<pair<TUPLES, uint32_t>> data = loadCAIDA18();
    unordered_map<TUPLES, int> flow_size;
    unordered_map<TUPLES, uint32_t> last_time;
    unordered_map<TUPLES, multiset<uint32_t>> real_interval;
    for (auto [key, tm]: data)
        flow_size[key]++;

    cout << "inserting..." << endl;
    
    int cnt = 0;
    for (auto [key, tm]: data) {
        if (++cnt % 1000000 == 0)
            cout << cnt << endl;
        if (last_time.count(key)) {
            int interval = tm - last_time[key];
            micro.insert(key, tm, interval);
            real_interval[key].insert(interval);
        }
        last_time[key] = tm;
    }

    micro.check_memory();

    cout << "evaluating..." << endl;

    // vector<pair<int, TUPLES>> flow_list = micro.flow_list();
    vector<pair<int, TUPLES>> flow_list = groundtruth(data);
    sort(flow_list.begin(), flow_list.end(), greater<pair<int, TUPLES>>());

    const int point_cnt = 19;
    double p0 = 1.0 / (point_cnt + 1);
    vector<double> error(point_cnt, 0);
    int flow_num = flow_list.size();
    double ale = 0;
    int flow_cnt = 0;
    for (unsigned i = 0; i < flow_num; i++) {
        auto [size, key] = flow_list[i];
        if (size < 1000)
            break;
        flow_cnt++;
        vector<pair<int, int>> est = micro.query_delay(key);
        ale += calc_ale(real_interval[key], est);
    }
    ale /= flow_cnt;
    fout << "Memory usage = " << MEMORY << " Bytes" << endl;
    fout << "ALE = " << ale << endl;
    cout << "Result in CellSketch_ALE.txt" << endl;
    return ale;
}

int main() {
    distribution_estimation(MEMORY);
    return 0;
}
