#include "renderer_switch.hpp"

namespace reincarnated {
bool RendererSwitch::onF10KeyDown(bool repeated) noexcept
{
    if (repeated)
        return false;
    mode_ = mode_ == RenderMode::Classic ? RenderMode::HighDefinition : RenderMode::Classic;
    return true;
}
} // namespace reincarnated
