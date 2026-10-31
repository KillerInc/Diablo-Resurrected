#pragma once
#include <cstdint>
namespace devilution { class Lightmap; class ClxSprite; struct Surface; }
namespace reincarnated {
// Raster spans are emitted in the original traversal order, including writes
// whose palette index equals the previous pixel. No framebuffer differencing.
#ifdef USE_SDL3
extern bool HdCaptureActive;
void MirrorOpaque(const uint8_t *pixels, unsigned length);
void MirrorBlend(const uint8_t *dst, unsigned length, const uint8_t *src,
    uint8_t color, const uint8_t *map = nullptr, const devilution::Lightmap *lightmap = nullptr);
void SetHdCaptureSuppressed(bool value);
bool DrawHdSheet(const devilution::Surface &out, int x, int y, devilution::ClxSprite sprite,
    const uint8_t *translation = nullptr, const devilution::Lightmap *lightmap = nullptr, bool blend = false);
bool HasHdSheet(devilution::ClxSprite sprite);
class ClassicSpriteScope {
    bool suppressed;
public:
    explicit ClassicSpriteScope(bool value) : suppressed(value) { if (value) SetHdCaptureSuppressed(true); }
    ~ClassicSpriteScope() { if (suppressed) SetHdCaptureSuppressed(false); }
};
#else
inline constexpr bool HdCaptureActive = false;
inline void MirrorOpaque(const uint8_t *, unsigned) {}
inline void MirrorBlend(const uint8_t *, unsigned, const uint8_t *, uint8_t, const uint8_t * = nullptr, const devilution::Lightmap * = nullptr) {}
class ClassicSpriteScope { public: explicit ClassicSpriteScope(bool) {} };
#endif
}
