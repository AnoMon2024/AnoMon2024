#include "anosketch.h"
#include "trace.h"
#include <bits/stdc++.h>

using namespace std;

const bool UNIFORM = false;
const int MEMORY = 400000;
const int BUCKET_CNT = MEMORY / 1000;

vector<pair<TUPLES, uint32_t>> get_interval(const vector<pair<TUPLES, uint32_t>> &data) {
    unordered_map<TUPLES, uint32_t> last_time;
    vector<pair<TUPLES, uint32_t>> res;
    for (auto [key, tm]: data) {
        if (last_time.count(key)) {
            res.push_back(make_pair(key, tm - last_time[key]));
        }
        last_time[key] = tm;
    }
    return res;
}

int get_interval_id(uint32_t interval) {
    int interval_id;
    for (interval_id = 0; interval_id < INTERVAL_CNT - 1; interval_id++) {
        if (interval <= RANGE[interval_id])
            break;
    }
    return interval_id;
}

VecHashMap calc_distribution(const VecHashMap &mp, int key_type) {
    VecHashMap dist_map;
    for (auto [key, cnt]: mp) {
        TUPLES t = key;
        for (int i = 0; i < 5; i++) {
            if (key_mask[key_type][i] == 0)
                t.set(i, 0);
        }
        if (!dist_map.count(t)) {
            dist_map[t] = vector<uint32_t>(4, 0);
        }
        for (int i = 0; i < 4; i++)
            dist_map[t][i] += cnt[i];
    }
    return dist_map;
}

pair<double, vector<double>>
interval_distribution(const vector<pair<TUPLES, uint32_t>> &interval_data, 
                      const vector<double> &proportion) {
    AnoSketch<BUCKET_CNT, MEMORY> anosketch;
    anosketch.memory_init(proportion);

    VecHashMap gt;
    for (auto [key, tm]: interval_data) {
        int interval_id = get_interval_id(tm);
        if (!gt.count(key)) {
            gt[key] = vector<uint32_t>(4, 0);
        }
        gt[key][interval_id]++;
    }

    int threshold = interval_data.size() / 2000;
    
    VecHashMap res;
    for (auto [key, interval]: interval_data) {
        anosketch.insert(key, interval);
    }

    res = anosketch.query_all();

    int pkt_cnt[4] = {0};
    int tot = 0;
    double wmre_tot = 0;
    double wmre[6];
    for (int i = 0; i < 6; i++) {
        auto real_map = calc_distribution(gt, i);
        auto est_map = calc_distribution(res, i);
        for (auto [key, cnt]: est_map) {
            if (!real_map.count(key))
                continue;
            int est_sum = 0, real_sum = 0;
            for (auto x: cnt)
                est_sum += x;
            for (auto x: real_map[key])
                real_sum += x;
            for (int j = 0; j < 4; j++)
                pkt_cnt[j] += real_map[key][j];
            if (est_sum < threshold || real_sum == 0)
                continue;
            tot++;
            int err_tot = 0;
            for (int j = 0; j < 4; j++) {
                int tmp = cnt[j] - real_map[key][j];
                if (tmp < 0)
                    tmp = -tmp;
                err_tot += tmp;
            }
            wmre_tot += (double)err_tot * 2 / (est_sum + real_sum);
        }
        wmre[i] = wmre_tot / tot;
    }

    vector<int> light_packet_num = anosketch.get_light_packet_num();
    vector<int> conflict_num = anosketch.get_conflict_num();
    vector<double> used_counter_ratio = anosketch.get_used_counter_ratio();
    vector<int> light_memory = anosketch.get_light_memory();
    vector<double> next_proportion;
    for (int i = 0; i < INTERVAL_CNT; i++) {
        // next_proportion.push_back(light_memory[i] * used_counter_ratio[i]);
        next_proportion.push_back(light_packet_num[i]);
    }
    // next_proportion = used_counter_ratio;
    return make_pair(wmre[5], next_proportion);
}

double interval_dynamic_memory(const vector<pair<TUPLES, uint32_t>> &interval_data) {
    int window_num = 100;
    int window_size = 60 * 10000000 / window_num;
    vector<double> next_proportion({1, 1, 1, 1});
    double total_wmre = 0;
    int start = 0, end = 0;
    for (int i = 0; i < window_num; i++) {
        start = end;
        if (i == window_num - 1) {
            end = interval_data.size();
        } else {
            while (end < interval_data.size() && 
                   interval_data[end].second < window_size * (i+1))
                end++;
        }
        vector<pair<TUPLES, uint32_t>> window_data(interval_data.begin() + start, 
                                                   interval_data.begin() + end);
        if (UNIFORM) {
            for (int j = 0; j < INTERVAL_CNT; j++)
                next_proportion[j] = 1;
        }
        auto res = interval_distribution(window_data, next_proportion);
        double wmre = res.first;
        next_proportion = res.second;
        total_wmre += wmre;
    }
    total_wmre /= window_num;
    return total_wmre;
}

void auto_adjustment() {
    vector<pair<TUPLES, uint32_t>> data = loadCAIDA18();
    vector<pair<TUPLES, uint32_t>> interval_data = get_interval(data);
    int T = 1;
    double total_wmre = 0;
    for (int i = 0; i < T; i++) {
        double wmre = interval_dynamic_memory(interval_data);
        total_wmre += wmre;
    }
    total_wmre /= T;
    ofstream fout("auto_adjustment_result.txt");
    fout << "Memory usage= " << MEMORY << " Bytes" << endl;
    fout << "Auto adjustment: " << (UNIFORM ? "Off" : "On") << endl;
    fout << "WMRE = " << total_wmre << endl;
    cout << "Result in auto_adjustment_result.txt" << endl;
}

int main() {
    auto_adjustment();
    return 0;
}
