#include "scene_commands.hpp"
#include <cassert>
#include <cmath>

using namespace reincarnated;
static bool near(float a,float b) { return std::abs(a-b) < 0.001f; }

int main()
{
    // Escape/options menus have to own the foreground draw layer.
    assert(!ShouldDrawHdWorld(false, false));
    assert(!ShouldDrawHdWorld(false, true));
    assert(ShouldDrawHdWorld(true, false));
    assert(!ShouldDrawHdWorld(true, true));

    HdSceneCommands q;
    // Sprite source resolution does not affect its logical draw rectangle.
    assert(q.append(10, {912,412,96,128}, 540, SceneRole::Actor, {}));
    assert(q.items().size() == 1 && near(q.items()[0].destination.x, 912));
    assert(near(q.items()[0].destination.height, 128));
    HdSceneCommands z;
    // Existing 2x Zoom() maps the source to a left-panel-offset destination.
    assert(z.append(20, {120,60,128,256}, 316, SceneRole::Terrain, {2,320,0}));
    assert(near(z.items()[0].destination.x, 560));
    assert(near(z.items()[0].destination.y, 120));
    assert(near(z.items()[0].destination.height, 512));
    assert(near(z.items()[0].groundDepthY, 632));

    q.clear();
    assert(q.empty());
    assert(q.append(1, {0,0,64,128}, 300, SceneRole::Actor, {}));
    assert(q.append(2, {0,0,64,64}, 100, SceneRole::Actor, {}));
    assert(q.append(3, {0,0,64,64}, 300, SceneRole::Terrain, {}));
    assert(q.append(4, {0,0,64,64}, 300, SceneRole::Foreground, {}));
    assert(q.append(5, {0,0,64,64}, 300, SceneRole::Actor, {}));
    q.sortForPresentation();
    const auto &v = q.items();
    assert(v.size() == 5);
    assert(v[0].textureIndex == 2 && v[1].textureIndex == 3);
    assert(v[2].textureIndex == 1 && v[3].textureIndex == 5);
    assert(v[4].textureIndex == 4);

    assert(!q.append(7, {0,0,-2,20}, 10, SceneRole::Actor, {}));
    assert(!q.append(7, {0,0,20,20}, 10, SceneRole::Actor, {0,0,0}));
    assert(!q.append(7, {0,0,20,20}, NAN, SceneRole::Actor, {}));
    assert(q.items().size() == 5);
}
