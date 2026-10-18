#include "renderer_switch.hpp"
#include "sprite_layout.hpp"

#include <cassert>
#include <cmath>
using namespace reincarnated;
static bool near(float a, float b) { return std::abs(a - b) <= 0.001f; }

int main()
{
    RendererSwitch renderer;
    assert(renderer.mode() == RenderMode::Classic);
    assert(renderer.onF10KeyDown(false));
    assert(renderer.usesHdRenderer());
    assert(!renderer.onF10KeyDown(true));
    assert(renderer.usesHdRenderer());
    assert(renderer.onF10KeyDown(false));
    assert(renderer.mode() == RenderMode::Classic);

    const Camera2D camera {{0, 0}, {1920, 1080}, 1.0f};
    const SpriteLayout classic {96, 128, {96, 128}, {48, 128}};
    const SpriteLayout hd {384, 512, {96, 128}, {48, 128}};
    const auto a = projectSprite(classic, {0, 0}, camera);
    const auto b = projectSprite(hd, {0, 0}, camera);
    assert(a && b);
    assert(near(a->x, 912) && near(a->y, 412));
    assert(near(a->width, 96) && near(a->height, 128));
    assert(near(a->x, b->x) && near(a->y, b->y));
    assert(near(a->width, b->width) && near(a->height, b->height));

    const SpriteLayout wall {1024, 2048, {128, 256}, {64, 256}};
    const auto wallQuad = projectSprite(wall, {0, 0}, camera);
    assert(wallQuad && near(wallQuad->width, 128) && near(wallQuad->height, 256));

    const Camera2D zoomCamera {{0, 0}, {1920, 1080}, 1.75f};
    const auto zoomQuad = projectSprite(hd, {0, 0}, zoomCamera);
    assert(zoomQuad && near(zoomQuad->width, 168) && near(zoomQuad->height, 224));
    assert(near(zoomQuad->x + 48 * 1.75f, 960));
    assert(near(zoomQuad->y + 128 * 1.75f, 540));

    assert(!projectSprite({0, 128, {96, 128}, {48, 128}}, {0, 0}, camera));
    assert(!projectSprite(hd, {0, 0}, {{0, 0}, {1920, 1080}, 0}));
}
