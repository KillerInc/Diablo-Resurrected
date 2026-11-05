#pragma once
#ifdef USE_SDL3
#include <array>
#include <memory>
#include <SDL3/SDL_pixels.h>
#include "engine/clx_sprite.hpp"
#include "sheet_source.hpp"
namespace reincarnated {
struct GpuSheet;
bool UsesNativeWorldIndices(const SheetSource &source);
const std::array<SDL_Color, 256> *WorldSourcePalette();
std::shared_ptr<GpuSheet> WorldSpriteIndices(devilution::ClxSprite sprite);
void ClearWorldSpriteIndices();
}
#endif
