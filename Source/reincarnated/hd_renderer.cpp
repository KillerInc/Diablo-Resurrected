#include "hd_renderer.hpp"
#include <cmath>
#include <fstream>
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
#endif

namespace reincarnated {
RendererSwitch &GetRendererSwitch() noexcept
{
    static RendererSwitch state;
    return state;
}

#ifndef USE_SDL1
namespace {
struct Asset {
    SDL_Texture *texture = nullptr;
    float w = 0, h = 0, pivotX = 0, pivotY = 0;
    bool customLayout = false;
};
struct DrawCommand {
    SDL_Texture *texture;
    float x, y, w, h;
};
std::unordered_map<std::string, Asset> assets;
std::vector<DrawCommand> commands;
SDL_Renderer *owner = nullptr;

Asset *LoadAsset(const std::string &name)
{
    const auto it = assets.find(name);
    if (it != assets.end())
        return it->second.texture == nullptr ? nullptr : &it->second;

    Asset asset;
    SDL_Surface *surface = IMG_Load(name.c_str());
    if (surface != nullptr) {
        if (surface->w > 0 && surface->h > 0) {
            asset.texture = SDL_CreateTextureFromSurface(owner, surface);
            if (asset.texture != nullptr) {
                SDL_SetTextureBlendMode(asset.texture, SDL_BLENDMODE_BLEND);
                std::ifstream layout(name + ".layout");
                if (layout >> asset.w >> asset.h >> asset.pivotX >> asset.pivotY) {
                    asset.customLayout = std::isfinite(asset.w) && std::isfinite(asset.h)
                        && std::isfinite(asset.pivotX) && std::isfinite(asset.pivotY)
                        && asset.w > 0 && asset.h > 0;
                }
            }
        }
#ifdef USE_SDL3
        SDL_DestroySurface(surface);
#else
        SDL_FreeSurface(surface);
#endif
    }
    auto inserted = assets.emplace(name, asset).first;
    return inserted->second.texture == nullptr ? nullptr : &inserted->second;
}

bool Queue(const std::string &path, int left, int bottom, int nominalW, int nominalH, int zoom)
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
    commands.push_back({
        image->texture, (groundX - px) * zoom, (bottom - py) * zoom, w * zoom, h * zoom});
    return true;
}
} // namespace

bool QueueHdPlayer(int heroClass, int direction, int frame,
    int left, int bottom, int width, int height, int zoom)
{
    if (!GetRendererSwitch().usesHdRenderer())
        return false;
    const std::string base = "hd/players/" + std::to_string(heroClass);
    const std::string animated = base + "/" + std::to_string(direction)
        + "_" + std::to_string(frame) + ".png";
    return Queue(animated, left, bottom, width, height, zoom)
        || Queue(base + ".png", left, bottom, width, height, zoom);
}

bool QueueHdTile(int dungeonType, unsigned pieceId,
    int left, int bottom, int width, int height, int zoom)
{
    if (!GetRendererSwitch().usesHdRenderer())
        return false;
    return Queue("hd/tiles/" + std::to_string(dungeonType) + "/"
            + std::to_string(pieceId) + ".png",
            left, bottom, width, height, zoom);
}

void PresentHdOverlay(SDL_Renderer *target)
{
    if (target == nullptr) {
        commands.clear();
        return;
    }
    if (GetRendererSwitch().usesHdRenderer()) {
        for (const DrawCommand &command : commands) {
            const SDL_FRect dst { command.x, command.y, command.w, command.h };
#ifdef USE_SDL3
            SDL_RenderTexture(target, command.texture, nullptr, &dst);
#else
            SDL_RenderCopyF(target, command.texture, nullptr, &dst);
#endif
        }
        SDL_SetRenderDrawColor(target, 45, 182, 140, 255);
        const SDL_FRect marker { 4, 4, 5, 22 };
#ifdef USE_SDL3
        SDL_RenderFillRect(target, &marker);
#else
        SDL_RenderFillRectF(target, &marker);
#endif
    }
    commands.clear();
}

void ResetHdAssets()
{
    commands.clear();
    for (auto &entry : assets)
        if (entry.second.texture != nullptr)
            SDL_DestroyTexture(entry.second.texture);
    assets.clear();
    owner = nullptr;
}
#else
bool QueueHdPlayer(int, int, int, int, int, int, int, int) { return false; }
bool QueueHdTile(int, unsigned, int, int, int, int, int, int) { return false; }
#endif
} // namespace reincarnated
