#pragma once
#include "renderer_switch.hpp"
#ifndef USE_SDL1
struct SDL_Renderer;
#endif
namespace reincarnated {
RendererSwitch &GetRendererSwitch() noexcept;
// Position is the classic sprite's left edge and bottom baseline (pre-zoom).
bool QueueHdPlayer(int heroClass, int direction, int frame,
    int left, int bottom, int width, int height, int zoom);
bool QueueHdTile(int dungeonType, unsigned pieceId,
    int left, int bottom, int width, int height, int zoom);
#ifndef USE_SDL1
void PresentHdOverlay(SDL_Renderer *renderer);
void ResetHdAssets();
#endif
} // namespace reincarnated
