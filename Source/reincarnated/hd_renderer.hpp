#pragma once
#include "renderer_switch.hpp"
#include "asset_provider.hpp"
#include "scene_commands.hpp"
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
void EndHdWorldFrame();
void SaveHdCursorBackground(int x, int y, int width, int height);
void RestoreHdCursorBackground();
SDL_Surface *ComposeHdFrame(SDL_Surface *classic);
#endif
#endif
} // namespace reincarnated
