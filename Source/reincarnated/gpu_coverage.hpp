#pragma once
#include <cstdint>
namespace reincarnated {
// Later raster writes apply m*S+b to each ordered GPU source colour.
inline void ApplyGpuCoverage(uint8_t *p,uint8_t r,uint8_t g,uint8_t b,unsigned alpha) {
    const unsigned inverse=255-alpha;
    p[0]=(p[0]*inverse+r*alpha+127)/255;p[1]=(p[1]*inverse+g*alpha+127)/255;
    p[2]=(p[2]*inverse+b*alpha+127)/255;p[3]=(p[3]*inverse+127)/255;
}
}
