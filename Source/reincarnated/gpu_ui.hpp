#pragma once
#ifdef USE_SDL3
#include "engine/point.hpp"
#include <SDL3/SDL_rect.h>
#include <cstddef>
#include <cstdint>
namespace devilution {
struct Surface;
class ClxSprite;
} // namespace devilution
namespace reincarnated {
struct GpuUiStats {
	uint64_t draws, hdDraws, uploads;
	size_t textures, bytes;
};
GpuUiStats GetGpuUiStats();
bool PrepareGpuUiHudLayer(int x, int y, int w, int h);
bool BeginGpuUiHudComponent(unsigned component, bool changed);
void EndGpuUiHudComponent(unsigned component);
void InvalidateGpuUiHud();
void SaveGpuUiScene();
void RestoreGpuUiScene();
void ForgetGpuUiScene();
bool TranslateGpuUiRect(const devilution::Surface &out, SDL_Rect rect, const uint8_t *trn);
bool TranslateGpuUiDraws(SDL_Rect rect, const uint8_t *trn);
bool DrawGpuUiRect(const devilution::Surface &out, int x, int y, int w, int h, uint8_t color, bool blend = false);
bool GpuUiEnabled();
bool GpuUiPhase();
void BeginGpuUiFrame(bool standalone);
void EnterGpuUiPhase();
void ResetGpuUiFrame();
void ClearGpuUiAssets();
bool DrawGpuUiSprite(const devilution::Surface &out, int x, int bottom, devilution::ClxSprite sprite, const uint8_t *trn = nullptr, bool blend = false, int outline = -1, bool skipZero = false);
void MarkGpuUiSurfaceDirty(const devilution::Surface &out);
void RememberGpuUiSurface(const devilution::Surface &out, int x, int bottom, devilution::ClxSprite sprite);
bool DrawGpuUiSurface(const devilution::Surface &out, const devilution::Surface &src, SDL_Rect rect, devilution::Point position, bool skipZero);
} // namespace reincarnated
#endif
