#include "hd_renderer.hpp"
#include <cmath>
#include <limits>
#include <sstream>
#include <string>
#include <unordered_map>
#include <vector>

#ifndef USE_SDL1
#ifdef USE_SDL3
#include <SDL3/SDL_render.h>
#include <SDL3/SDL_surface.h>
#include <SDL3_image/SDL_image.h>
#else
#include <SDL.h>
#include <SDL_image.h>
#endif
#include "utils/display.h"
#include "utils/paths.h"
#endif

namespace reincarnated {
RendererSwitch &GetRendererSwitch() noexcept
{
    static RendererSwitch state;
    return state;
}

#ifndef USE_SDL1
AssetStore &GetHdAssetStore()
{
    static AssetStore store;
    static const bool initialized = [&]() {
        // Later mounts win. Loose project-working-dir art overrides per-user,
        // executable-adjacent and installed assets (no extraction needed).
        store.mountLoose(devilution::paths::AssetsPath());
        store.mountLoose(devilution::paths::BasePath());
        store.mountLoose(devilution::paths::PrefPath());
        store.mountLoose(".");
        return true;
    }();
    (void)initialized;
    return store;
}

namespace {
struct Asset {
    SDL_Texture *texture = nullptr;
    float w = 0, h = 0, pivotX = 0, pivotY = 0;
    bool customLayout = false;
};
std::unordered_map<std::string, Asset> assets;
HdSceneCommands commands;
std::vector<SDL_Texture *> frameTextures;
PresentationTransform transform;
SDL_Rect sceneClip { 0, 0, 0, 0 };
SDL_Renderer *owner = nullptr;

Asset *LoadAsset(const std::string &name)
{
    const auto it = assets.find(name);
    if (it != assets.end())
        return it->second.texture == nullptr ? nullptr : &it->second;

    Asset asset;
    AssetBytes imageBytes;
    // The renderer reads a virtual asset ID, never a physical filename.
    // A future archive provider supplies the same compressed image bytes.
    if (GetHdAssetStore().read(name, imageBytes)) {
        SDL_Surface *surface = nullptr;
#ifdef USE_SDL3
        SDL_IOStream *stream = SDL_IOFromConstMem(imageBytes.data(), imageBytes.size());
        if (stream != nullptr)
            surface = IMG_Load_IO(stream, true);
#else
        if (imageBytes.size() <= static_cast<size_t>(std::numeric_limits<int>::max())) {
            SDL_RWops *stream = SDL_RWFromConstMem(imageBytes.data(), static_cast<int>(imageBytes.size()));
            if (stream != nullptr)
                surface = IMG_Load_RW(stream, 1);
        }
#endif
        if (surface != nullptr) {
            if (surface->w > 0 && surface->h > 0) {
                asset.texture = SDL_CreateTextureFromSurface(owner, surface);
                if (asset.texture != nullptr) {
                    SDL_SetTextureBlendMode(asset.texture, SDL_BLENDMODE_BLEND);
                    AssetBytes layoutBytes;
                    if (GetHdAssetStore().read(name + ".layout", layoutBytes)) {
                        const std::string layoutText(layoutBytes.begin(), layoutBytes.end());
                        std::istringstream layout(layoutText);
                        if (layout >> asset.w >> asset.h >> asset.pivotX >> asset.pivotY) {
                            asset.customLayout = std::isfinite(asset.w) && std::isfinite(asset.h)
                                && std::isfinite(asset.pivotX) && std::isfinite(asset.pivotY)
                                && asset.w > 0 && asset.h > 0;
                        }
                    }
                }
            }
#ifdef USE_SDL3
            SDL_DestroySurface(surface);
#else
            SDL_FreeSurface(surface);
#endif
        }
    }
    auto inserted = assets.emplace(name, asset).first;
    return inserted->second.texture == nullptr ? nullptr : &inserted->second;
}

bool Queue(const std::string &path, int left, int bottom, int nominalW, int nominalH, int zoom, SceneRole role)
{
    if (!GetRendererSwitch().usesHdRenderer() || devilution::renderer == nullptr
        || nominalW <= 0 || nominalH <= 0 || zoom <= 0)
        return false;
    if (owner != devilution::renderer) {
        ResetHdAssets();
        owner = devilution::renderer;
    }
    Asset *image = LoadAsset(path);
    if (image == nullptr)
        return false;
    const float w = image->customLayout ? image->w : static_cast<float>(nominalW);
    const float h = image->customLayout ? image->h : static_cast<float>(nominalH);
    const float px = image->customLayout ? image->pivotX : w * 0.5f;
    const float py = image->customLayout ? image->pivotY : h;
    const float groundX = left + nominalW * 0.5f;
    frameTextures.push_back(image->texture);
    const bool accepted = commands.append(frameTextures.size() - 1,
        { groundX - px, static_cast<float>(bottom) - py, w, h },
        static_cast<float>(bottom), role, transform);
    if (!accepted)
        frameTextures.pop_back();
    return accepted;
}
} // namespace

void BeginHdWorldFrame(int zoom, int offsetX, int clipX, int clipWidth, int clipHeight)
{
    commands.clear();
    frameTextures.clear();
    transform = { static_cast<float>(zoom), static_cast<float>(offsetX), 0.0f };
    sceneClip = { clipX, 0, clipWidth, clipHeight };
}

bool QueueHdPlayer(int heroClass, int direction, int frame,
    int left, int bottom, int width, int height, int zoom)
{
    if (!GetRendererSwitch().usesHdRenderer())
        return false;
    const std::string base = "hd/players/" + std::to_string(heroClass);
    const std::string animated = base + "/" + std::to_string(direction)
        + "_" + std::to_string(frame) + ".png";
    return Queue(animated, left, bottom, width, height, zoom, SceneRole::Actor)
        || Queue(base + ".png", left, bottom, width, height, zoom, SceneRole::Actor);
}

bool QueueHdMonster(int monsterType, int direction, int frame,
    int left, int bottom, int width, int height, int zoom)
{
    if (!GetRendererSwitch().usesHdRenderer())
        return false;
    const std::string base = "hd/monsters/" + std::to_string(monsterType);
    return Queue(base + "/" + std::to_string(direction) + "_"
            + std::to_string(frame) + ".png",
            left, bottom, width, height, zoom, SceneRole::Actor)
        || Queue(base + ".png", left, bottom, width, height, zoom, SceneRole::Actor);
}

bool QueueHdTile(int dungeonType, unsigned pieceId,
    int left, int bottom, int width, int height, int zoom)
{
    if (!GetRendererSwitch().usesHdRenderer())
        return false;
    return Queue("hd/tiles/" + std::to_string(dungeonType) + "/"
            + std::to_string(pieceId) + ".png",
            left, bottom, width, height, zoom, SceneRole::Terrain);
}

void PresentHdOverlay(SDL_Renderer *target)
{
    if (target == nullptr) {
        commands.clear();
        frameTextures.clear();
        return;
    }
    if (GetRendererSwitch().usesHdRenderer()) {
        commands.sortForPresentation();
        if (sceneClip.w > 0 && sceneClip.h > 0) {
#ifdef USE_SDL3
            SDL_SetRenderClipRect(target, &sceneClip);
#else
            SDL_RenderSetClipRect(target, &sceneClip);
#endif
        }
        for (const HdDrawCommand &command : commands.items()) {
            if (command.textureIndex >= frameTextures.size())
                continue;
            const Rect &bounds = command.destination;
            const SDL_FRect dst { bounds.x, bounds.y, bounds.width, bounds.height };
#ifdef USE_SDL3
            SDL_RenderTexture(target, frameTextures[command.textureIndex], nullptr, &dst);
#else
            SDL_RenderCopyF(target, frameTextures[command.textureIndex], nullptr, &dst);
#endif
        }
        if (sceneClip.w > 0 && sceneClip.h > 0) {
#ifdef USE_SDL3
            SDL_SetRenderClipRect(target, nullptr);
#else
            SDL_RenderSetClipRect(target, nullptr);
#endif
        }
        // Temporary mode indicator: a visible green stripe in HD mode.
        SDL_SetRenderDrawColor(target, 45, 182, 140, 255);
        const SDL_FRect marker { 4, 4, 5, 22 };
#ifdef USE_SDL3
        SDL_RenderFillRect(target, &marker);
#else
        SDL_RenderFillRectF(target, &marker);
#endif
    }
    commands.clear();
    frameTextures.clear();
}

void ResetHdAssets()
{
    commands.clear();
    frameTextures.clear();
    for (auto &entry : assets)
        if (entry.second.texture != nullptr)
            SDL_DestroyTexture(entry.second.texture);
    assets.clear();
    owner = nullptr;
}
#else
void BeginHdWorldFrame(int, int, int, int, int) {}
bool QueueHdPlayer(int, int, int, int, int, int, int, int) { return false; }
bool QueueHdMonster(int, int, int, int, int, int, int, int) { return false; }
bool QueueHdTile(int, unsigned, int, int, int, int, int) { return false; }
#endif
} // namespace reincarnated
