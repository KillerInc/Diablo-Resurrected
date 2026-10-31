#pragma once

#include <cstdint>
#include <string>
#include "engine/clx_sprite.hpp"

namespace reincarnated {
// Provenance travels inside the in-memory CLX header, so clones, direction
// changes and allocation reuse cannot attach an actor to a stale asset pointer.
inline constexpr uint16_t SheetHeaderSize = 274;
inline constexpr uint32_t SheetHeaderMagic = 0x31534844;
struct SheetSource {
    std::string path;
    unsigned columns, rows, width;
};
#ifdef USE_SDL3
devilution::OwnedClxSpriteListOrSheet AnnotateSheetSource(
    devilution::OwnedClxSpriteListOrSheet data, const char *path);
const SheetSource *GetSheetSource(devilution::ClxSprite sprite);
void ApplySheetTranslation(devilution::ClxSprite sprite, const uint8_t *translation);
#else
inline devilution::OwnedClxSpriteListOrSheet AnnotateSheetSource(devilution::OwnedClxSpriteListOrSheet data, const char *) { return data; }
inline const SheetSource *GetSheetSource(devilution::ClxSprite) { return nullptr; }
inline void ApplySheetTranslation(devilution::ClxSprite, const uint8_t *) {}
#endif
} // namespace reincarnated
