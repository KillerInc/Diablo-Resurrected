#pragma once
#include "renderer_switch.hpp"
#include "asset_provider.hpp"
#include "scene_commands.hpp"
namespace devilution { struct Surface; }
#ifndef USE_SDL1
struct SDL_Renderer;
struct SDL_Surface;
#endif
namespace reincarnated {
RendererSwitch &GetRendererSwitch() noexcept;
// Future archive packs can be mounted at a lower priority than loose folders.
#ifndef USE_SDL1
AssetStore &GetHdAssetStore();
#endif
// Position is the classic sprite's left edge and bottom baseline (pre-zoom).
// Called before the world traversal; configures the classic source-to-output mapping.
void BeginHdWorldFrame(int zoom, int offsetX, int clipX, int clipWidth, int clipHeight);
bool QueueHdPlayer(int heroClass, int direction, int frame,
    int left, int bottom, int width, int height, int zoom);
bool QueueHdMonster(int monsterType, int direction, int frame,
    int left, int bottom, int width, int height, int zoom);
bool QueueHdTile(int dungeonType, unsigned pieceId,
    int left, int bottom, int width, int height, int zoom);
#ifndef USE_SDL1
void PresentHdOverlay(SDL_Renderer *renderer);
void ResetHdAssets();
#ifdef USE_SDL3
struct SheetSource;
struct HdCacheMetrics { size_t sheets = 0, bytes = 0, pinned = 0; uint64_t hits = 0, misses = 0, decodes = 0, failures = 0, evictions = 0, decodeNs = 0; };
HdCacheMetrics GetHdCacheMetrics();
struct HdPlayerCacheStats { size_t sheets; size_t bytes; };
bool BeginHdPlayerPreload(const std::string &classPath);
bool PreloadHdPlayerSheet(const SheetSource &source);
HdPlayerCacheStats GetHdPlayerCacheStats();
void ReleaseHdPlayerSheets();
void EndHdWorldFrame();
void BeginHdUiFrame(bool force = false);
void MarkHdUiPresented();
// The persistent HUD sits below transient UI (menus, messages and cursor).
// Its indexed backing keeps the existing dirty-component drawing routines.
bool PrepareHdHudLayer(int x, int y, int width, int height);
devilution::Surface HdHudLayerTarget(const devilution::Surface &fallback);
void CommitHdHudLayer(bool changed);
void SaveHdCursorBackground(int x, int y, int width, int height);
void RestoreHdCursorBackground();
SDL_Surface *ComposeHdFrame(SDL_Surface *classic);
SDL_Surface *GetHdUiSurface();
bool HasHdUiRaster();
#endif
#endif
} // namespace reincarnated
