#pragma once
#include <charconv>
#include <cstring>
#include <limits>
#include <cstddef>
#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <psapi.h>
#endif

namespace reincarnated {
constexpr size_t MemoryMiB = 1024 * 1024;
inline size_t ProcessPrivateMemoryBytes()
{
#ifdef _WIN32
    PROCESS_MEMORY_COUNTERS_EX memory {};
    memory.cb = sizeof(memory);
    if (K32GetProcessMemoryInfo(GetCurrentProcess(), reinterpret_cast<PROCESS_MEMORY_COUNTERS *>(&memory), sizeof(memory)))
        return memory.PrivateUsage;
#endif
    return 0;
}
// Configuration is a warning/cache target, never permission to reject a PNG.
inline size_t MemoryTarget(const char *value, size_t defaultMiB)
{
    size_t mib = 0;
    if (value != nullptr) {
        const char *end = value + std::strlen(value);
        const auto parsed = std::from_chars(value, end, mib);
        if (parsed.ec == std::errc() && parsed.ptr == end && mib > 0
            && mib <= std::numeric_limits<size_t>::max() / MemoryMiB)
            return mib * MemoryMiB;
    }
    return defaultMiB * MemoryMiB;
}
// Cumulative flags: 75%, 90%, 100%. Subtraction avoids ratio overflow.
inline unsigned MemoryWarningFlags(size_t bytes, size_t target)
{
    if (target == 0) return 0;
    return (bytes >= target - target / 4 ? 1U : 0U)
        | (bytes >= target - target / 10 ? 2U : 0U)
        | (bytes >= target ? 4U : 0U);
}
}
