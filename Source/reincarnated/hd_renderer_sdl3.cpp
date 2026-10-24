#ifdef USE_SDL3
#include "hd_renderer.hpp"
#include "raster_bridge.hpp"
#include <algorithm>
#include <cmath>
#include <charconv>
#include <cstring>
#include <sstream>
#include <unordered_map>
#include <vector>
#include <SDL3/SDL_surface.h>
#include <SDL3_image/SDL_image.h>
#include "engine/render/light_render.hpp"
#include "game_mode.hpp"
#include "dds_decode.hpp"
#include "sheet_png.hpp"
#include "engine/palette.h"
#include "engine/surface.hpp"
#include "utils/display.h"
#include "utils/log.hpp"
#include "utils/paths.h"
#include "utils/sdl_wrap.h"

namespace reincarnated {
bool HdCaptureActive = false;
namespace {
struct Asset {
    devilution::SDLSurfaceUniquePtr surface;
    float w = 0, h = 0, px = 0, py = 0;
    bool layout = false;
};
std::unordered_map<std::string, Asset> assets;
devilution::SDLSurfaceUniquePtr world, ui, composed;
std::vector<uint8_t> beforeUi;
std::vector<uint8_t> cursorBehind;
SDL_Rect cursorRect {};
bool cursorSaved = false;
bool inWorld, ready, suppressed;
int scale = 1, offsetX;
SDL_Rect clip;

struct CachedSheet { SheetImage image; uint64_t used = 0; };
std::unordered_map<std::string, CachedSheet> sheets;
std::unordered_map<uint32_t, uint8_t> nearestColors;
std::array<SDL_Color, 256> matchingPalette {};
size_t sheetBytes = 0;
uint64_t sheetClock = 0;
size_t SheetBudget()
{
    static const size_t bytes = [] {
        unsigned megabytes = 1024;
        if (const char *value = SDL_getenv("D1R_SHEET_CACHE_MB")) {
            unsigned requested = 0;
            const auto end = value + std::strlen(value);
            const auto parsed = std::from_chars(value, end, requested);
            if (parsed.ec == std::errc() && parsed.ptr == end && requested >= 128 && requested <= 4096) megabytes = requested;
        }
        return size_t(megabytes) * 1024 * 1024;
    }();
    return bytes;
}

CachedSheet *LoadSheet(const SheetSource &source)
{
    const std::string key = source.path + ":" + std::to_string(source.columns) + ":" + std::to_string(source.rows) + ":" + std::to_string(source.width);
    auto found = sheets.find(key);
    if (found != sheets.end()) { found->second.used = ++sheetClock; return &found->second; }
    CachedSheet entry;
    AssetBytes bytes, sidecar;
    if (GetHdAssetStore().readWithSidecar(source.path, bytes, sidecar)) {
        SheetLayout layout;
        const bool validLayout = sidecar.empty() || ParseSheetLayout(sidecar, layout);
        if (validLayout && DecodeSheetPng(bytes, source, entry.image, sidecar.empty() ? nullptr : &layout)) {
            while (sheetBytes + entry.image.rgba.size() > SheetBudget()) {
                auto victim = sheets.end();
                for (auto it = sheets.begin(); it != sheets.end(); ++it)
                    if (!it->second.image.rgba.empty() && (victim == sheets.end() || it->second.used < victim->second.used)) victim = it;
                if (victim == sheets.end()) break;
                sheetBytes -= victim->second.image.rgba.size();
                sheets.erase(victim);
            }
            sheetBytes += entry.image.rgba.size();
            devilution::Log("Loaded HD sheet: {} ({}x{}, {} directions, {} frames, {}x retained density)", source.path,
                entry.image.width, entry.image.height, source.columns, source.rows, entry.image.density);
        } else devilution::Log("HD sheet layout/decode rejected; preserving Classic fallback: {}", source.path);
    }
    entry.used = ++sheetClock;
    return &sheets.emplace(key, std::move(entry)).first->second;
}

uint8_t MatchColor(const uint8_t *rgba)
{
    const uint32_t rgb = (uint32_t(rgba[0]) << 16) | (uint32_t(rgba[1]) << 8) | rgba[2];
    const auto found = nearestColors.find(rgb);
    if (found != nearestColors.end()) return found->second;
    unsigned distance = ~0U;
    uint8_t match = 0;
    for (unsigned i = 0; i < 256; ++i) {
        const auto &c = matchingPalette[i];
        const int r = int(rgba[0]) - c.r, g = int(rgba[1]) - c.g, b = int(rgba[2]) - c.b;
        const unsigned d = r * r + g * g + b * b;
        if (d < distance) { distance = d; match = static_cast<uint8_t>(i); }
    }
    // Bound the auxiliary truecolor matching table as well as the image cache.
    if (nearestColors.size() >= 262144) nearestColors.clear();
    nearestColors.emplace(rgb, match);
    return match;
}

void EnsureSurface(devilution::SDLSurfaceUniquePtr &surface)
{
    if (!surface || surface->w != devilution::gnScreenWidth || surface->h != devilution::gnScreenHeight) {
        surface.reset(SDL_CreateSurface(devilution::gnScreenWidth, devilution::gnScreenHeight, SDL_PIXELFORMAT_RGBA32));
        if (!surface) devilution::ErrSdl();
    }
}
bool SourcePosition(const uint8_t *src, int &x, int &y)
{
    auto *pal = devilution::PalSurface;
    if (!HdCaptureActive || suppressed || !pal) return false;
    // Integer address comparison avoids subtracting unrelated allocations:
    // menu caches and sprite decode buffers must not be captured as screen.
    const auto base = reinterpret_cast<uintptr_t>(pal->pixels);
    const auto address = reinterpret_cast<uintptr_t>(src);
    if (address < base || address >= base + size_t(pal->pitch) * pal->h) return false;
    const auto offset = address - base;
    x = offset % pal->pitch; y = offset / pal->pitch;
    return x < pal->w;
}
void Pixel(int x, int y, SDL_Color color, bool blend)
{
    SDL_Surface *target = inWorld ? world.get() : ui.get();
    const int zoom = inWorld ? scale : 1;
    x = x * zoom + (inWorld ? offsetX : 0);
    y *= zoom;
    for (int dy = 0; dy < zoom; ++dy) {
        for (int dx = 0; dx < zoom; ++dx) {
            const int px = x + dx, py = y + dy;
            if (px < 0 || py < 0 || px >= target->w || py >= target->h) continue;
            if (inWorld && (px < clip.x || px >= clip.x + clip.w || py >= clip.h)) continue;
            auto *dst = static_cast<uint8_t *>(target->pixels) + py * target->pitch + px * 4;
            if (blend) {
                // Classic's transparent masks use 50% source blending. Blend
                // against the HD canvas, not against the indexed actor behind it.
                if (!inWorld && dst[3] == 0) {
                    // UI transparency is composited over the independently built world.
                    if (px >= clip.x && px < clip.x + clip.w && py < clip.h) {
                        const auto *background = static_cast<const uint8_t *>(world->pixels) + py * world->pitch + px * 4;
                        for (int c = 0; c < 3; ++c) dst[c] = background[c];
                    } else {
                        const auto index = *(static_cast<const uint8_t *>(devilution::PalSurface->pixels) + py * devilution::PalSurface->pitch + px);
                        const auto background = devilution::Palette->colors[index];
                        dst[0] = background.r; dst[1] = background.g; dst[2] = background.b;
                    }
                }
                dst[0] = (unsigned(dst[0]) + color.r) / 2;
                dst[1] = (unsigned(dst[1]) + color.g) / 2;
                dst[2] = (unsigned(dst[2]) + color.b) / 2;
            } else {
                dst[0] = color.r; dst[1] = color.g; dst[2] = color.b;
            }
            dst[3] = 255;
        }
    }
}
Asset *Load(const std::string &path)
{
    const auto found = assets.find(path);
    if (found != assets.end()) return found->second.surface ? &found->second : nullptr;
    Asset image;
    AssetBytes bytes, sidecar;
    if (GetHdAssetStore().readWithSidecar(path, bytes, sidecar)) {
        if (path.size() >= 4 && path.substr(path.size() - 4) == ".dds") {
            DdsImage decoded;
            if (DecodeDds(bytes, decoded)) {
                image.surface.reset(SDL_CreateSurface(decoded.width, decoded.height, SDL_PIXELFORMAT_RGBA32));
                if (!image.surface) devilution::ErrSdl();
                for (unsigned y = 0; y < decoded.height; ++y)
                    std::memcpy(static_cast<uint8_t *>(image.surface->pixels) + y * image.surface->pitch,
                        decoded.rgba.data() + size_t(y) * decoded.width * 4, decoded.width * 4);
            }
        } else {
            auto *stream = SDL_IOFromConstMem(bytes.data(), bytes.size());
            if (stream) image.surface.reset(IMG_Load_IO(stream, true));
        }
        if (image.surface) {
            SDL_SetSurfaceBlendMode(image.surface.get(), SDL_BLENDMODE_BLEND);
            if (!sidecar.empty()) {
                std::istringstream layout(std::string(sidecar.begin(), sidecar.end()));
                if (layout >> image.w >> image.h >> image.px >> image.py)
                    image.layout = std::isfinite(image.w) && std::isfinite(image.h)
                        && std::isfinite(image.px) && std::isfinite(image.py) && image.w > 0 && image.h > 0;
            }
            devilution::LogVerbose("Loaded HD texture: {} ({}x{})", path, image.surface->w, image.surface->h);
        } else {
            devilution::Log("HD image decode failed, using individual Classic fallback: {}: {}", path, SDL_GetError());
            SDL_ClearError();
        }
    }
    auto it = assets.emplace(path, std::move(image)).first;
    return it->second.surface ? &it->second : nullptr;
}
bool Draw(const std::string &path, int left, int bottom, int nominalW, int nominalH)
{
    if (!HdCaptureActive || !inWorld || nominalW <= 0 || nominalH <= 0) return false;
    Asset *image = Load(path);
    if (!image) return false;
    const float w = image->layout ? image->w : float(nominalW);
    const float h = image->layout ? image->h : float(nominalH);
    const float px = image->layout ? image->px : w / 2;
    const float py = image->layout ? image->py : h;
    SDL_Rect dst { int(std::lround((left + nominalW / 2.0f - px) * scale + offsetX)),
        int(std::lround((bottom - py + 1) * scale)), int(std::lround(w * scale)), int(std::lround(h * scale)) };
    // SDL clips the scaled destination without moving its source pivot.
    if (!SDL_BlitSurfaceScaled(image->surface.get(), nullptr, world.get(), &dst, SDL_SCALEMODE_NEAREST)) devilution::ErrSdl();
    return true;
}
bool DrawVariants(const std::string &base, int direction, int frame, int left, int bottom, int w, int h)
{
    const std::string animation = base + "/" + std::to_string(direction) + "_" + std::to_string(frame);
    return Draw(animation + ".png", left, bottom, w, h) || Draw(animation + ".dds", left, bottom, w, h)
        || Draw(base + ".png", left, bottom, w, h) || Draw(base + ".dds", left, bottom, w, h);
}
}
RendererSwitch &GetRendererSwitch() noexcept { static RendererSwitch state; return state; }
AssetStore &GetHdAssetStore()
{
    static AssetStore store;
    static const bool initialized = [&] {
        store.mountLoose(devilution::paths::AssetsPath());
        store.mountLoose(devilution::paths::ExecutablePath());
        store.mountLoose(devilution::paths::BasePath());
        store.mountLoose(devilution::paths::PrefPath());
        store.mountLoose(".");
        return true;
    }();
    (void)initialized;
    return store;
}
void SetHdCaptureSuppressed(bool value) { suppressed = value; }
void MirrorOpaque(const uint8_t *src, unsigned length)
{
    int x, y;
    if (!SourcePosition(src, x, y)) return;
    length = std::min(length, unsigned(devilution::PalSurface->w - x));
    for (unsigned i = 0; i < length; ++i) Pixel(x + i, y, devilution::Palette->colors[src[i]], false);
}
void MirrorBlend(const uint8_t *dst, unsigned length, const uint8_t *src, uint8_t color,
    const uint8_t *map, const devilution::Lightmap *lightmap)
{
    int x, y;
    if (!SourcePosition(dst, x, y)) return;
    const uint8_t *light = lightmap ? lightmap->getLightingAt(dst) : nullptr;
    length = std::min(length, unsigned(devilution::PalSurface->w - x));
    for (unsigned i = 0; i < length; ++i) {
        uint8_t index = src ? src[i] : color;
        if (map) index = map[index];
        if (lightmap) index = lightmap->adjustColor(index, light[i]);
        Pixel(x + i, y, devilution::Palette->colors[index], true);
    }
}
void BeginHdWorldFrame(int zoom, int xOffset, int clipX, int clipWidth, int clipHeight)
{
    HdCaptureActive = GetRendererSwitch().usesHdRenderer();
    ready = false; suppressed = false; cursorSaved = false;
    if (!HdCaptureActive) return;
    if (std::memcmp(matchingPalette.data(), devilution::logical_palette.data(), sizeof(matchingPalette)) != 0) {
        matchingPalette = devilution::logical_palette;
        nearestColors.clear();
    }
    EnsureSurface(world); EnsureSurface(ui); EnsureSurface(composed);
    scale = zoom; offsetX = xOffset;
    clip = { clipX, 0, clipWidth, clipHeight };
    SDL_SetSurfaceClipRect(world.get(), nullptr);
    SDL_FillSurfaceRect(world.get(), nullptr, SDL_MapSurfaceRGBA(world.get(), 0, 0, 0, 255));
    SDL_SetSurfaceClipRect(world.get(), &clip);
    SDL_FillSurfaceRect(ui.get(), nullptr, 0);
    inWorld = true;
}
void EndHdWorldFrame()
{
    if (!HdCaptureActive) return;
    inWorld = false; ready = true;
    auto *pal = devilution::PalSurface;
    beforeUi.assign(static_cast<uint8_t *>(pal->pixels), static_cast<uint8_t *>(pal->pixels) + size_t(pal->pitch) * pal->h);
}
// Cursor-only redraws reuse the current world/UI scene. Restore the RGBA UI
// background as well as Classic's indexed background, so old cursor coverage
// cannot remain above an HD sprite or erase menu pixels beneath the cursor.
void SaveHdCursorBackground(int x, int y, int width, int height)
{
    cursorSaved = false;
    if (!HdCaptureActive || !ready || !ui) return;
    const SDL_Rect requested { x, y, width, height };
    const SDL_Rect bounds { 0, 0, ui->w, ui->h };
    if (!SDL_GetRectIntersection(&requested, &bounds, &cursorRect)) return;
    cursorBehind.resize(size_t(cursorRect.w) * cursorRect.h * 4);
    for (int row = 0; row < cursorRect.h; ++row)
        std::memcpy(cursorBehind.data() + size_t(row) * cursorRect.w * 4,
            static_cast<const uint8_t *>(ui->pixels) + (cursorRect.y + row) * ui->pitch + cursorRect.x * 4, cursorRect.w * 4);
    cursorSaved = true;
}
void RestoreHdCursorBackground()
{
    if (!cursorSaved || !ui) return;
    for (int row = 0; row < cursorRect.h; ++row)
        std::memcpy(static_cast<uint8_t *>(ui->pixels) + (cursorRect.y + row) * ui->pitch + cursorRect.x * 4,
            cursorBehind.data() + size_t(row) * cursorRect.w * 4, cursorRect.w * 4);
    cursorSaved = false;
}
bool QueueHdPlayer(int type, int direction, int frame, int left, int bottom, int w, int h, int)
{ return DrawVariants("hd/players/" + std::to_string(type), direction, frame, left, bottom, w, h); }
bool QueueHdMonster(int type, int direction, int frame, int left, int bottom, int w, int h, int)
{ return DrawVariants("hd/monsters/" + std::to_string(type), direction, frame, left, bottom, w, h); }

bool HasHdSheet(devilution::ClxSprite sprite)
{
    if (!HdCaptureActive || !inWorld) return false;
    const auto *source = GetSheetSource(sprite);
    return source && !LoadSheet(*source)->image.rgba.empty();
}

bool DrawHdSheet(const devilution::Surface &out, int x, int y, devilution::ClxSprite sprite,
    const uint8_t *translation, const devilution::Lightmap *lightmap, bool blend)
{
    // Menu/cache renders can use the same sprite data; only replace writes to
    // the active world surface. Keep classic indexed pixels for game logic.
    if (!HdCaptureActive || !inWorld || suppressed || out.surface != devilution::PalSurface) return false;
    const auto *source = GetSheetSource(sprite);
    if (!source) return false;
    auto &image = LoadSheet(*source)->image;
    if (image.rgba.empty()) return false;
    const auto *header = sprite.pixelData() - SheetHeaderSize;
    const unsigned group = devilution::LoadLE16(header + 14), frame = devilution::LoadLE16(header + 16);
    if (group >= source->columns || frame >= source->rows || image.cellHeight / image.density < sprite.height()) return false;
    const int logicalHeight = image.cellHeight / image.density;
    const int top = y + 1 - image.anchorY;
    const int left = (x + int(source->width / 2) - image.anchorX + out.region.x) * scale + offsetX;
    const int upper = (top + out.region.y) * scale;
    const int w = image.logicalWidth * scale, h = logicalHeight * scale;
    const auto *bakedTranslation = header + 18;
    // Clip in the caller's local coordinates as well as to the world viewport.
    const int xBegin = std::max({left, clip.x, out.region.x * scale + offsetX, 0});
    const int xEnd = std::min({left + w, clip.x + clip.w, (out.region.x + out.w()) * scale + offsetX, world->w});
    const int yBegin = std::max({upper, out.region.y * scale, 0});
    const int yEnd = std::min({upper + h, clip.h, (out.region.y + out.h()) * scale, world->h});
    for (int py = yBegin; py < yEnd; ++py) {
        const unsigned sy = frame * image.cellHeight + (py - upper) * image.density / scale;
        auto *dst = static_cast<uint8_t *>(world->pixels) + py * world->pitch;
        for (int px = xBegin; px < xEnd; ++px) {
            const unsigned sx = group * image.cellWidth + (px - left) * image.density / scale;
            const auto *src = image.rgba.data() + (size_t(sy) * image.width + sx) * 4;
            unsigned alpha = src[3];
            if (!alpha) continue;
            if (blend) alpha /= 2;
            const uint8_t original = MatchColor(src);
            uint8_t mapped = bakedTranslation[original];
            if (translation) mapped = translation[mapped];
            if (lightmap) {
                const int localX = (px - offsetX) / scale - out.region.x;
                const int localY = py / scale - out.region.y;
                mapped = lightmap->adjustColor(mapped, *lightmap->getLightingAt(out.at(localX, localY)));
            }
            const auto &base = matchingPalette[original];
            const auto &lit = devilution::Palette->colors[mapped];
            const int originalChannels[3] { base.r, base.g, base.b };
            const int litChannels[3] { lit.r, lit.g, lit.b };
            // Preserve the sheet's truecolor smoothing residual around the
            // nearest palette color while following vanilla TRN/light/fade.
            const int intensity = std::min(256, (int(lit.r) + lit.g + lit.b) * 256 / std::max(1, int(base.r) + base.g + base.b));
            for (int c = 0; c < 3; ++c) {
                const int color = std::clamp(litChannels[c] + (int(src[c]) - originalChannels[c]) * intensity / 256, 0, 255);
                dst[px * 4 + c] = (color * alpha + dst[px * 4 + c] * (255 - alpha) + 127) / 255;
            }
            dst[px * 4 + 3] = 255;
        }
    }
    return true;
}
bool QueueHdTile(int type, unsigned piece, int left, int bottom, int w, int h, int)
{
    const auto base = "hd/tiles/" + std::to_string(type) + "/" + std::to_string(piece);
    return Draw(base + ".png", left, bottom, w, h) || Draw(base + ".dds", left, bottom, w, h);
}
SDL_Surface *ComposeHdFrame(SDL_Surface *classic)
{
    if (!devilution::gbRunGame || !HdCaptureActive || !ready || !GetRendererSwitch().usesHdRenderer()) return classic;
    // Preserve persistent HUD/panel pixels, then replace the entire world
    // viewport with the independently assembled canvas. No flattened Classic
    // world is used as an HD background.
    if (!SDL_BlitSurface(classic, nullptr, composed.get(), nullptr)) devilution::ErrSdl();
    if (!SDL_BlitSurface(world.get(), &clip, composed.get(), &clip)) devilution::ErrSdl();
    auto *pal = devilution::PalSurface;
    // Raw UI writers not using raster spans are also retained. Raster coverage
    // handles equal-color writes (which this supplemental pass cannot detect).
    for (int y = 0; y < clip.h; ++y) {
        const auto *src = static_cast<const uint8_t *>(pal->pixels) + y * pal->pitch;
        for (int x = clip.x; x < clip.x + clip.w; ++x)
            if (src[x] != beforeUi[y * pal->pitch + x]) {
                const auto *coverage = static_cast<const uint8_t *>(ui->pixels) + y * ui->pitch + x * 4;
                if (!coverage[3]) Pixel(x, y, devilution::Palette->colors[src[x]], false);
            }
    }
    SDL_SetSurfaceBlendMode(ui.get(), SDL_BLENDMODE_BLEND);
    if (!SDL_BlitSurface(ui.get(), nullptr, composed.get(), nullptr)) devilution::ErrSdl();
    return composed.get();
}
void PresentHdOverlay(SDL_Renderer *) {}
void ResetHdAssets()
{
    HdCaptureActive = false; inWorld = false; ready = false; suppressed = false;
    assets.clear(); world.reset(); ui.reset(); composed.reset(); beforeUi.clear(); cursorBehind.clear(); cursorSaved = false;
    sheets.clear(); sheetBytes = 0; nearestColors.clear();
}
}
#endif
