#include "performance_samples.hpp"
#include <cassert>
int main() {
    reincarnated::FrameSamples s;
    assert(s.p95() == 0);
    for (int i=1;i<=100;++i) s.add(i, 2, 3);
    assert(s.frames==100 && s.p95()==95 && s.maximum==100 && s.over33==67 && s.over50==50 && s.total==5050 && s.compose==200 && s.present==300);
    s={};
    for(int i=0;i<5000;++i) s.add(16, 1, 2);
    assert(s.stored==4096 && s.frames==5000 && s.p95()==16 && s.over33==0);
}
