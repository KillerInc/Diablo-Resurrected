#pragma once

namespace reincarnated {
enum class RenderMode { Classic, HighDefinition };

class RendererSwitch {
public:
    [[nodiscard]] RenderMode mode() const noexcept { return mode_; }
    [[nodiscard]] bool usesHdRenderer() const noexcept { return mode_ == RenderMode::HighDefinition; }
    bool onF10KeyDown(bool repeated) noexcept;
    void setMode(RenderMode mode) noexcept { mode_ = mode; }
private:
    RenderMode mode_ = RenderMode::Classic;
};
} // namespace reincarnated
