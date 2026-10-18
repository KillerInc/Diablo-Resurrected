#pragma once
#include <optional>

namespace reincarnated {
struct Vec2 { float x = 0; float y = 0; };
struct Rect { float x = 0; float y = 0; float width = 0; float height = 0; };

// Source dimensions are physical texels; size/pivot are logical world-render units.
struct SpriteLayout {
    unsigned sourceWidth = 0;
    unsigned sourceHeight = 0;
    Vec2 logicalSize {};
    Vec2 logicalPivot {};
};
struct Camera2D {
    Vec2 projectedCenter {};
    Vec2 viewportPixels {};
    float zoom = 1.0f;
};
[[nodiscard]] std::optional<Rect> projectSprite(
    const SpriteLayout &sprite, Vec2 projectedContactPoint, const Camera2D &camera) noexcept;
} // namespace reincarnated
