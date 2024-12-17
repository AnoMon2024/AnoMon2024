#ifndef _Ano_H_
#define _Ano_H_

#include "HeavyPart.h"
#include "Util.h"
#include "coldsampler.h"

template<int bucket_num, int tot_memory_in_bytes>
class AnoSketch
{
    static constexpr int heavy_mem = bucket_num * sizeof(Bucket);
    static constexpr int light_mem = (tot_memory_in_bytes - heavy_mem);  // total
    static constexpr bool all_light = false;

public:
    HeavyPart<bucket_num> heavy_part;
    ColdSampler *light_part[INTERVAL_CNT];
    int light_memory[INTERVAL_CNT];

    AnoSketch() {
        for (int i = 0; i < INTERVAL_CNT; i++) {
            light_part[i] = NULL;
        }
    }
    
    ~AnoSketch(){
        for (int i = 0; i < INTERVAL_CNT; i++) {
            delete light_part[i];
        }
    }

    void memory_init(const vector<double> &proportion) {
        double sum = accumulate(proportion.begin(), proportion.end(), 0.0);
        for (int i = 0; i < INTERVAL_CNT; i++) {
            light_memory[i] = light_mem * proportion[i] / sum;
            light_part[i] = new ColdSampler(light_memory[i]);
        }
    }

    void clear() {
        heavy_part.clear();
        for (int i = 0; i < INTERVAL_CNT; i++) {
            light_part[i]->clear();
        }
    }

    void insert(TUPLES key, int val) {
        int interval_id;
        for (interval_id = 0; interval_id < INTERVAL_CNT - 1; interval_id++) {
            if (val <= RANGE[interval_id])
                break;
        }

        if (all_light) {
            light_part[interval_id]->insert(key, 1);
            return;
        }

        TUPLES swap_key;
        vector<uint32_t> swap_val;
        int result = heavy_part.insert(key, swap_key, swap_val, interval_id);
        switch(result)
        {
            case 0: return;
            case 1:{
                for (int i = 0; i < INTERVAL_CNT; i++)
                    light_part[i]->insert(swap_key, swap_val[i]);
                return;
            }
            case 2: light_part[interval_id]->insert(key, 1);  return;
            default:
                printf("error return value !\n");
                exit(1);
        }
    }

    vector<uint32_t> query(TUPLES key) {
        vector<uint32_t> result = heavy_part.query(key);
        for (int i = 0; i < INTERVAL_CNT; i++) {
            result[i] += light_part[i]->query(key);
        }
        return result;
    }

    int get_bucket_num() { return heavy_part.get_bucket_num(); }

    void *operator new(size_t sz) {
        constexpr uint32_t alignment = 64;
        size_t alloc_size = (2 * alignment + sz) / alignment * alignment;
        void *ptr = ::operator new(alloc_size);
        void *old_ptr = ptr;
        void *new_ptr = ((char*)std::align(alignment, sz, ptr, alloc_size) + alignment);
        ((void **)new_ptr)[-1] = old_ptr;

        return new_ptr;
    }

    void operator delete(void *p) {
        ::operator delete(((void**)p)[-1]);
    }

    VecHashMap query_all() {
        VecHashMap mp = heavy_part.query_all();
        for (int i = 0; i < INTERVAL_CNT; i++) {
            HashMap result = light_part[i]->query_all();
            for (auto it = result.begin(); it != result.end(); it++) {
                if (!mp.count(it->first)) {
                    mp[it->first] = vector<uint32_t>(INTERVAL_CNT, 0);
                }
                mp[it->first][i] += it->second;
            }
        }
        return mp;
    }

    vector<uint32_t> query_partial_key(TUPLES key, KeyType type, uint32_t mask=0xffffffff) {
        if (type == five_tuples)
            return query(key);
        VecHashMap mp = query_all();
        vector<uint32_t> ans(INTERVAL_CNT, 0);
        for (auto it = mp.begin(); it != mp.end(); it++) {
            if (
                type == srcIP_dstIP   && key.srcIP() == it->first.srcIP() && key.dstIP()   == it->first.dstIP()   ||
                type == srcIP_srcPort && key.srcIP() == it->first.srcIP() && key.srcPort() == it->first.srcPort() ||
                type == dstIP_dstPort && key.dstIP() == it->first.dstIP() && key.dstPort() == it->first.dstPort() ||
                type == srcIP         && (key.srcIP() & mask) == (it->first.srcIP() & mask) ||
                type == dstIP         && (key.dstIP() & mask) == (it->first.dstIP() & mask)
            ) {
                for (int i = 0; i < INTERVAL_CNT; i++) {
                    ans[i] += it->second[i];
                }
            }
        }
        return ans;
    }

    vector<int> get_light_packet_num() {
        vector<int> res;
        // cout << "light packet num: ";
        for (int i = 0; i < INTERVAL_CNT; i++) {
            res.push_back(light_part[i]->packet_num);
            // cout << res[i] << ", ";
        }
        // cout << endl;
        return res;
    }

    vector<int> get_conflict_num() {
        vector<int> res;
        // cout << "conflict num: ";
        for (int i = 0; i < INTERVAL_CNT; i++) {
            res.push_back(light_part[i]->conflict_num);
            // cout << res[i] << ", ";
        }
        // cout << endl;
        return res;
    }

    vector<double> get_used_counter_ratio() {
        vector<double> res;
        // cout << "used counter ratio: ";
        for (int i = 0; i < INTERVAL_CNT; i++) {
            res.push_back(light_part[i]->used_counter_ratio());
            // cout << res[i] << ", ";
        }
        // cout << endl;
        return res;
    }

    vector<int> get_light_memory() {
        return vector<int>(light_memory, light_memory+INTERVAL_CNT);
    }
};

#endif
