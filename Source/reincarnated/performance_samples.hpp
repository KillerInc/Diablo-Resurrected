#pragma once
#include <algorithm>
#include <array>
#include <cstddef>
namespace reincarnated {
// Fixed storage: no per-frame allocation; the latest 4096 intervals define percentiles.
struct FrameSamples {
    std::array<double, 4096> values {};
    size_t stored = 0, frames = 0, over33 = 0, over50 = 0;
    double total = 0, maximum = 0, compose = 0, present = 0;
    void add(double interval, double composeMs, double presentMs) {
        values[frames % values.size()] = interval;
        stored = std::min(stored + 1, values.size()); ++frames;
        total += interval; maximum = std::max(maximum, interval);
        compose += composeMs; present += presentMs;
        over33 += interval > 33.333333; over50 += interval > 50;
    }
    double p95() const {
        if (!stored) return 0;
        auto sorted = values;
        std::sort(sorted.begin(), sorted.begin() + stored);
        return sorted[(stored * 95 + 99) / 100 - 1];
    }
};
}
