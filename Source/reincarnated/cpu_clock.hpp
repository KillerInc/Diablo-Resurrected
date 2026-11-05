#pragma once
#include <cstdint>
namespace reincarnated {
struct ThreadWorkClock { uint64_t ns = 0, cycles = 0; };
ThreadWorkClock ReadThreadWorkClock();
}
