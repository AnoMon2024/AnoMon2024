#include "common/Util.h"
#include "dleft/dleft.h"
#include "hotfilter/HotFilter.h"
#include <bits/stdc++.h>
using namespace std;


void test0() {
    TUPLES a[1];
    memset(a, 0, sizeof a);
    // memset(b, 0, sizeof b);
    
    for (int i = 0; i < 13; i++) {
        cout << '(' << (int)a[0].data[i] << ')' << endl;
    }
}

void test_dleft() {
    DLeft d(3, 1000);
    TUPLES t(1, 2, 3, 4, 5);
    cout << t.srcIP() << ' ' << t.dstIP() << ' ' << t.srcPort() << ' ' << t.dstPort() << ' ' << t.proto() << endl;
    d.insert(t);
    d.insert(t);
    cout << d.query(t) << endl;
}

void print(vector<uint32_t> v) {
    cout << '[';
    for (uint32_t x: v) {
        cout << x << ", ";
    }
    cout << ']' << endl;
}

void test_ec1() {
    HotFilter<10, 100000> hotfilter;
    TUPLES a(1, 1, 1, 1, 1), b(1, 2, 2, 2, 2);
    hotfilter.insert(a, 15);
    hotfilter.insert(a, 150);
    hotfilter.insert(b, 1500);
    hotfilter.insert(b, 15000);
    auto res = hotfilter.query(a);
    print(res);
    auto mp = hotfilter.query_all();
    for (auto [key, vec]: mp) {
        cout << key.srcIP() << ": ";
        print(vec);
    }
    auto res2 = hotfilter.query_partial_key(TUPLES(1, 0, 0, 0, 0), srcIP);
    print(res2);
}

void test_ec2() {
    srand(3);
    const int n = 500, m = 500;
    HotFilter<10, 10000> hotfilter;
    int gt[m][4] = {0};
    for (int i = 1; i <= n; i++) {
        int pos = rand() % 4;
        int delay = pow(10, pos + 1) + 1;
        int id = rand() % m;
        hotfilter.insert(TUPLES(id, rand() % 2, 1, 1, 1), delay);
        gt[id][pos]++;
    }
    auto mp = hotfilter.query_all();
    auto mp2 = hotfilter.heavy_part.query_all();
    for (int i = 0; i < m; i++) {
        cout << i << ' ';
        for (int j = 0; j < 4; j++)
            cout << gt[i][j] << ' ';
        TUPLES t(i, 1, 1, 1, 1);
        if (mp.count(t)) {
            print(mp[t]);
            for (int j = 0; j < 4; j++)
                if (gt[i][j] != mp[t][j])
                    cout << "not equal" << endl;
        }
        else
            cout << "null" << endl;
        if (mp2.count(t)) {
            printf("heavy: ");
            print(mp2[t]);
        }
    }
    auto res2 = hotfilter.query_partial_key(TUPLES(0, 1, 0, 0, 0), dstIP);
    print(res2);
    auto res3 = hotfilter.query_partial_key(TUPLES(0, 0, 0, 0, 0), dstIP);
    print(res3);
    int sum2 = 0, sum3 = 0;
    for (auto x: res2)
        sum2 += x;
    for (auto x: res3)
        sum3 += x;
    cout << sum2 << ' ' << sum3 << endl;
    // for (auto [key, vec]: mp) {
    //     cout << key.srcIP() << ": ";
    //     print(vec);
    // }
}

int main() {
    // test_dleft();
    // test_ec1();
    test_ec2();
    return 0;
}
