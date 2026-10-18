#pragma once
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <vector>
#include "sprite_layout.hpp"

namespace reincarnated {

// Maps original pre-zoom world drawing coordinates to final display coordinates.
struct PresentationTransform {
    float scale = 1.0f;
    float offsetX = 0.0f;
    float offsetY = 0.0f;
};

// A secondary tie-breaker after ground depth. Stable submission order handles
// identical depth and role. This is an HD-only first pass at scene ordering.
enum class SceneRole : uint8_t { Terrain = 0, Actor = 1, Foreground = 2 };

struct HdDrawCommand {
    size_t textureIndex = 0;
    Rect destination {};
    float groundDepthY = 0;
    SceneRole role = SceneRole::Terrain;
};

class HdSceneCommands {
public:
    bool append(size_t textureIndex, Rect logicalBounds, float groundY,
        SceneRole role, PresentationTransform transform)
    {
        if (!(logicalBounds.width > 0 && logicalBounds.height > 0 && transform.scale > 0)
            || !std::isfinite(logicalBounds.x) || !std::isfinite(logicalBounds.y)
            || !std::isfinite(logicalBounds.width) || !std::isfinite(logicalBounds.height)
            || !std::isfinite(groundY) || !std::isfinite(transform.scale)
            || !std::isfinite(transform.offsetX) || !std::isfinite(transform.offsetY))
            return false;
        HdDrawCommand command {
            textureIndex,
            { logicalBounds.x * transform.scale + transform.offsetX,
                logicalBounds.y * transform.scale + transform.offsetY,
                logicalBounds.width * transform.scale,
                logicalBounds.height * transform.scale },
            groundY * transform.scale + transform.offsetY,
            role
        };
        if (!std::isfinite(command.destination.x) || !std::isfinite(command.destination.y)
            || !std::isfinite(command.destination.width) || !std::isfinite(command.destination.height)
            || !std::isfinite(command.groundDepthY))
            return false;
        commands_.push_back(command);
        return true;
    }

    void sortForPresentation()
    {
        std::stable_sort(commands_.begin(), commands_.end(),
            [](const HdDrawCommand &a, const HdDrawCommand &b) {
                if (a.groundDepthY != b.groundDepthY)
                    return a.groundDepthY < b.groundDepthY;
                return a.role < b.role;
            });
    }

    void clear() noexcept { commands_.clear(); }
    [[nodiscard]] bool empty() const noexcept { return commands_.empty(); }
    [[nodiscard]] const std::vector<HdDrawCommand> &items() const noexcept { return commands_; }

private:
    std::vector<HdDrawCommand> commands_;
};
} // namespace reincarnated
