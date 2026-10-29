#pragma once
#ifdef USE_SDL3
#include <SDL3/SDL_timer.h>
#include <array>
#include <cstdio>
#include <cstdint>
#include <string>
#include "performance_samples.hpp"
#include "hd_renderer.hpp"
#include "sheet_memory.hpp"
#include "utils/file_util.h"
#include "utils/paths.h"
#include "utils/log.hpp"
namespace reincarnated {
struct PerformanceMonitor {
    bool visible = false, loading = false;
    uint64_t previous = 0, windowStart = 0;
    FrameSamples samples;
    double drawMs = 0, drawTotal = 0;
    HdCacheMetrics lastCache {};
    std::array<std::string, 4> lines { "Performance: collecting...", "", "", "" };
    FILE *file = nullptr;
    bool opened = false;
    ~PerformanceMonitor() { if (file) std::fclose(file); }
    void resetWindow() { previous = windowStart = 0; samples = {}; drawMs = drawTotal = 0; }
    void record(uint64_t start, double composeMs, double presentMs, bool active) {
        if (!active || loading) { resetWindow(); return; }
        if (!previous) { previous = windowStart = start; lastCache = GetHdCacheMetrics(); return; }
        drawTotal += drawMs; drawMs = 0;
        samples.add(double(start - previous) / 1000000, composeMs, presentMs);
        previous = start;
        if (start - windowStart < 1000000000) return;
        const auto cache = GetHdCacheMetrics();
        const size_t privateBytes = ProcessPrivateMemoryBytes();
        const double ram = double(privateBytes) / (1024 * 1024 * 1024);
        const double p95 = samples.p95();
        const double avg = samples.total / samples.frames;
        const char *mode = GetRendererSwitch().usesHdRenderer() ? "HD" : "Classic";
        lines[0] = devilution::detail::format("{} | {:.1f} FPS | avg {:.1f} / p95 {:.1f} / max {:.1f} ms", mode, 1000 / avg, avg, p95, samples.maximum);
        lines[1] = devilution::detail::format("CPU draw {:.2f} compose {:.2f} present {:.2f} ms | >33ms {} >50ms {}", drawTotal / samples.frames, samples.compose / samples.frames, samples.present / samples.frames, samples.over33, samples.over50);
        lines[2] = devilution::detail::format("RAM private {:.2f} GiB | sheets {} / {:.2f} GiB | pinned {}", ram, cache.sheets, double(cache.bytes) / (1024 * 1024 * 1024), cache.pinned);
        lines[3] = devilution::detail::format("Cache hits {} misses {} decodes {} failed {} evictions {} (last interval)", cache.hits-lastCache.hits, cache.misses-lastCache.misses, cache.decodes-lastCache.decodes, cache.failures-lastCache.failures, cache.evictions-lastCache.evictions);
        if (!opened) {
            opened = true;
            const char *overridePath = SDL_getenv("D1R_PERF_LOG");
            const std::string path = overridePath ? overridePath : devilution::paths::ConfigPath() + "performance.csv";
            file = devilution::OpenFile(path.c_str(), "ab");
            if (file) { std::fprintf(file, "# session: CPU-side wall timings (present includes waiting); private RAM and decoded CPU sheet buffers; no GPU timing or VRAM measurement\nseconds,mode,frames,avg_ms,p95_ms,max_ms,over33,over50,draw_cpu_ms,compose_cpu_ms,present_cpu_ms,private_bytes,sheets,sheet_bytes,pinned,hits,misses,decodes,failures,evictions,decode_ms\n"); }
            else SDL_LogWarn(SDL_LOG_CATEGORY_APPLICATION, "Cannot open performance log: %s", path.c_str());
        }
        if (file) {
            std::fprintf(file, "%.3f,%s,%zu,%.4f,%.4f,%.4f,%zu,%zu,%.4f,%.4f,%.4f,%zu,%zu,%zu,%zu,%llu,%llu,%llu,%llu,%llu,%.4f\n", double(start)/1e9, mode, samples.frames, avg, p95, samples.maximum, samples.over33, samples.over50, drawTotal/samples.frames, samples.compose/samples.frames, samples.present/samples.frames, privateBytes, cache.sheets, cache.bytes, cache.pinned, (unsigned long long)(cache.hits-lastCache.hits), (unsigned long long)(cache.misses-lastCache.misses), (unsigned long long)(cache.decodes-lastCache.decodes), (unsigned long long)(cache.failures-lastCache.failures), (unsigned long long)(cache.evictions-lastCache.evictions), double(cache.decodeNs-lastCache.decodeNs)/1e6);
            std::fflush(file);
        }
        lastCache = cache; samples = {}; drawTotal = 0; windowStart = start;
    }
};
inline PerformanceMonitor &GetPerformanceMonitor() { static PerformanceMonitor monitor; return monitor; }
}
#endif
