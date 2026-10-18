#include "sprite_layout.hpp"
#include <cmath>

namespace reincarnated {
std::optional<Rect> projectSprite(
    const SpriteLayout &sprite, Vec2 projectedContactPoint, const Camera2D &camera) noexcept
{
    if (sprite.sourceWidth == 0 || sprite.sourceHeight == 0
        || !std::isfinite(sprite.logicalSize.x) || !std::isfinite(sprite.logicalSize.y)
        || sprite.logicalSize.x <= 0 || sprite.logicalSize.y <= 0
        || !std::isfinite(sprite.logicalPivot.x) || !std::isfinite(sprite.logicalPivot.y)
        || !std::isfinite(projectedContactPoint.x) || !std::isfinite(projectedContactPoint.y)
        || !std::isfinite(camera.projectedCenter.x) || !std::isfinite(camera.projectedCenter.y)
        || !std::isfinite(camera.viewportPixels.x) || !std::isfinite(camera.viewportPixels.y)
        || camera.viewportPixels.x <= 0 || camera.viewportPixels.y <= 0
        || !std::isfinite(camera.zoom) || camera.zoom <= 0)
        return std::nullopt;

    const Vec2 contact {
        camera.viewportPixels.x * 0.5f + (projectedContactPoint.x - camera.projectedCenter.x) * camera.zoom,
        camera.viewportPixels.y * 0.5f + (projectedContactPoint.y - camera.projectedCenter.y) * camera.zoom,
    };
    return Rect {
        contact.x - sprite.logicalPivot.x * camera.zoom,
        contact.y - sprite.logicalPivot.y * camera.zoom,
        sprite.logicalSize.x * camera.zoom,
        sprite.logicalSize.y * camera.zoom,
    };
}
} // namespace reincarnated
