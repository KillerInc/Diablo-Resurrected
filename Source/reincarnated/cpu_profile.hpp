#pragma once
#ifdef USE_SDL3
#include <SDL3/SDL_stdinc.h>
#include <SDL3/SDL_timer.h>
#include <array>
#include <cstdio>
#include <string>
#include "utils/file_util.h"

namespace reincarnated {
enum class CpuStage { WorldSetup, Lighting, Floor, TileContent, WorldFinish,
    ViewUi, HudAndCursor, ClassicCopy, WorldCopy, RawUiScan, UiComposite,
    FrameUpload, SwapchainWait, SpriteCommands, GpuSubmit, Count };
struct CpuProfile {
    static constexpr std::array<const char *, size_t(CpuStage::Count)> Names {
        "world_setup", "lighting", "floor", "tile_content", "world_finish",
        "view_ui", "hud_cursor", "classic_copy", "world_copy", "raw_ui_scan", "ui_composite",
        "frame_upload", "swapchain_wait", "sprite_commands", "gpu_submit" };
    std::array<uint64_t, size_t(CpuStage::Count)> ns {}, calls {};
    std::string path;
    FILE *file = nullptr;
    CpuProfile() { if (const auto *p = SDL_getenv("D1R_CPU_PROFILE_LOG")) path = p; }
    ~CpuProfile() { if (file) std::fclose(file); }
    bool enabled() const { return !path.empty(); }
    void reset() { ns.fill(0); calls.fill(0); }
    void flush(uint64_t timestamp, size_t frames) {
        if (!enabled() || !frames) return;
        if (!file) {
            file = devilution::OpenFile(path.c_str(), "ab");
            if (!file) { path.clear(); return; }
            std::fputs("seconds,stage,frames,calls,total_cpu_ms,per_frame_ms,per_call_us\n", file);
        }
        for (size_t i=0; i<Names.size(); ++i)
            std::fprintf(file, "%.3f,%s,%zu,%llu,%.6f,%.6f,%.6f\n", double(timestamp)/1e9,
                Names[i], frames, (unsigned long long)calls[i], double(ns[i])/1e6,
                double(ns[i])/1e6/frames, calls[i] ? double(ns[i])/1e3/calls[i] : 0);
        std::fflush(file);
        reset();
    }
};
inline CpuProfile &GetCpuProfile() { static CpuProfile profile; return profile; }
class CpuStageScope {
    CpuStage stage;
    uint64_t started;
public:
    explicit CpuStageScope(CpuStage value) : stage(value),
        started(GetCpuProfile().enabled() ? SDL_GetTicksNS() : 0) {}
    CpuStageScope(const CpuStageScope &) = delete;
    CpuStageScope &operator=(const CpuStageScope &) = delete;
    void finish() {
        if (!started) return;
        auto &profile=GetCpuProfile();const auto index=size_t(stage);
        profile.ns[index]+=SDL_GetTicksNS()-started;++profile.calls[index];started=0;
    }
    ~CpuStageScope() { finish(); }
};
}
#endif
