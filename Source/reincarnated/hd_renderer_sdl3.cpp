#ifdef USE_SDL3
#include "hd_renderer.hpp"
#include "raster_bridge.hpp"
#include "gpu_sprites.hpp"
#include "controls/control_mode.hpp"
#include <algorithm>
#include <cmath>
#include <charconv>
#include <cstring>
#include <sstream>
#include <mutex>
#include <unordered_map>
#include <vector>
#include <SDL3/SDL_surface.h>
#include <SDL3_image/SDL_image.h>
#include "engine/render/light_render.hpp"
#include "game_mode.hpp"
#include "dds_decode.hpp"
#include "sheet_png.hpp"
#include "sheet_memory.hpp"
#include "sheet_diagnostics.hpp"
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

struct CachedSheet { SheetImage image; uint64_t used = 0; bool pinned = false; };
std::unordered_map<std::string, CachedSheet> sheets;
std::mutex sheetMutex;
std::string preloadedPlayerClass;
size_t pinnedSheetBytes = 0;
std::unordered_map<uint32_t, uint8_t> nearestColors;
std::array<SDL_Color, 256> matchingPalette {};
size_t sheetBytes = 0;
uint64_t sheetClock = 0;
HdCacheMetrics cacheMetrics;
unsigned cacheWarningFlags = 0, processWarningFlags = 0;
size_t SheetBudget()
{
    static const size_t bytes = MemoryTarget(SDL_getenv("D1R_SHEET_CACHE_MB"), 4096);
    return bytes;
}
void WarnMemory(const char *kind, size_t bytes, size_t target, unsigned &seen, const std::string &source)
{
    const unsigned flags = MemoryWarningFlags(bytes, target);
    if ((flags & ~seen) == 0) return;
    seen |= flags;
    SheetWarning(
        "HD_MEMORY_WARNING kind={} flags={} used_mib={:.2f} target_mib={:.2f} source={} action=continue",
        kind, flags, double(bytes) / MemoryMiB, double(target) / MemoryMiB, source);
}
void WarnProcessMemory(const std::string &source)
{
    static const size_t target = MemoryTarget(SDL_getenv("D1R_PROCESS_WARN_MB"), 8192);
    WarnMemory("process_private_commit", ProcessPrivateMemoryBytes(), target, processWarningFlags, source);
}

CachedSheet *LoadSheet(const SheetSource &source, bool pin = false)
{
    std::unique_lock<std::mutex> lock(sheetMutex);
    const std::string key = source.path + ":" + std::to_string(source.columns) + ":" + std::to_string(source.rows) + ":" + std::to_string(source.width);
    auto found = sheets.find(key);
    if (found != sheets.end()) {
        ++cacheMetrics.hits;
        if (pin && !found->second.pinned) { found->second.pinned = true; pinnedSheetBytes += found->second.image.rgba.size(); }
        found->second.used = ++sheetClock; return &found->second;
    }
    // Independent PNG decoders run concurrently during the loading screen.
    // MPQ/provenance discovery has already finished on the loading thread.
    ++cacheMetrics.misses;
    const uint64_t decodeStart = SDL_GetTicksNS();
    lock.unlock();
    CachedSheet entry;
    entry.pinned = pin;
    AssetBytes bytes, sidecar;
    bool decoded = false;
    if (GetHdAssetStore().readWithLayout(source.path, bytes, sidecar)) {
        { const std::lock_guard<std::mutex> memoryLock(sheetMutex); WarnProcessMemory(source.path); }
        SheetLayout layout;
        const bool validLayout = sidecar.empty() || ParseSheetLayout(sidecar, layout);
        decoded = validLayout && DecodeSheetPng(bytes, source, entry.image, sidecar.empty() ? nullptr : &layout);
        if (!decoded) devilution::Log("HD sheet layout/decode rejected; preserving Classic fallback: {}", source.path);
    }
    lock.lock();
    cacheMetrics.decodeNs += SDL_GetTicksNS() - decodeStart;
    if (decoded) ++cacheMetrics.decodes; else ++cacheMetrics.failures;
    // A concurrent request may have completed the same key first.
    found = sheets.find(key);
    if (found != sheets.end()) {
        if (pin && !found->second.pinned) { found->second.pinned = true; pinnedSheetBytes += found->second.image.rgba.size(); }
        found->second.used = ++sheetClock; return &found->second;
    }
    if (decoded) {
        const size_t added = entry.image.rgba.size();
        // Hero sheets are session-pinned. Leave at least 512 MiB for scene
        // sprites when the requested hero set exceeds the ordinary LRU target.
        const size_t pinnedAfter = pinnedSheetBytes + (pin ? added : 0);
        const size_t available = SheetBudget() > pinnedAfter ? SheetBudget() - pinnedAfter : 0;
        const size_t budget = pinnedAfter ? std::max(size_t(512 * MemoryMiB), available) : SheetBudget();
        const size_t incoming = pin ? 0 : added;
        while (incoming > budget || sheetBytes - pinnedSheetBytes > budget - incoming) {
            auto victim = sheets.end();
            for (auto it = sheets.begin(); it != sheets.end(); ++it)
                if (!it->second.pinned && !it->second.image.rgba.empty() && (victim == sheets.end() || it->second.used < victim->second.used)) victim = it;
            if (victim == sheets.end()) break;
            sheetBytes -= victim->second.image.rgba.size();
            sheets.erase(victim);
            ++cacheMetrics.evictions;
        }
        sheetBytes += added;
        if (pin) pinnedSheetBytes += added;
        WarnMemory("sheet_cache", sheetBytes, SheetBudget(), cacheWarningFlags, source.path);
        WarnProcessMemory(source.path);
        devilution::Log("Loaded HD sheet: {} ({}x{}, {} directions, {} frames, {}x retained density)", source.path,
            entry.image.width, entry.image.height, source.columns, source.rows, entry.image.density);
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
            MaskGpuSpritePixel(px,py,color.r,color.g,color.b,blend ? 128 : 255);
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
    if (GetHdAssetStore().readWithLayout(path, bytes, sidecar)) {
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
            if(image.surface->format!=SDL_PIXELFORMAT_RGBA32)image.surface.reset(SDL_ConvertSurface(image.surface.get(),SDL_PIXELFORMAT_RGBA32));
            if(!image.surface)devilution::ErrSdl();
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
    if(HasQueuedGpuSprites() && dst.w>0 && dst.h>0) {
        const int x0=std::max({dst.x,clip.x,0}),y0=std::max(dst.y,0);
        const int x1=std::min({dst.x+dst.w,clip.x+clip.w,world->w}),y1=std::min({dst.y+dst.h,clip.h,world->h});
        for(int py=y0;py<y1;++py)for(int px=x0;px<x1;++px) {
            const int sx=int64_t(px-dst.x)*image->surface->w/dst.w,sy=int64_t(py-dst.y)*image->surface->h/dst.h;
            const auto *rgba=static_cast<const uint8_t*>(image->surface->pixels)+sy*image->surface->pitch+sx*4;
            if(rgba[3])MaskGpuSpritePixel(px,py,rgba[0],rgba[1],rgba[2],rgba[3]);
        }
    }
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
    BeginGpuSpriteFrame();
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
    SaveGpuSpriteCursor();
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
    RestoreGpuSpriteCursor();
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
    return source && (LoadGpuPlayerSheet(*source) || !LoadSheet(*source)->image.rgba.empty());
}

bool DrawHdSheet(const devilution::Surface &out, int x, int y, devilution::ClxSprite sprite,
    const uint8_t *translation, const devilution::Lightmap *lightmap, bool blend)
{
    // Menu/cache renders can use the same sprite data; only replace writes to
    // the active world surface. Keep classic indexed pixels for game logic.
    if (!HdCaptureActive || !inWorld || suppressed || out.surface != devilution::PalSurface) return false;
    const auto *source = GetSheetSource(sprite);
    if (!source) return false;
    if(SDL_getenv("D1R_TRACE_PLAYER_SHEETS") && source->path.rfind("hd/plrgfx/",0)==0) {
        static std::unordered_map<std::string,bool> traced;
        if(traced.emplace(source->path,true).second)devilution::Log("HD_PLAYER_DRAW source={}",source->path);
    }
    if (auto gpu = devilution::ControlMode != devilution::ControlTypes::VirtualGamepad ? LoadGpuPlayerSheet(*source) : std::shared_ptr<GpuSheet>{}) {
        const auto *header=sprite.pixelData()-SheetHeaderSize;
        const unsigned group=devilution::LoadLE16(header+14), frame=devilution::LoadLE16(header+16);
        if(group>=gpu->columns || frame>=gpu->rows)return false;
        const auto &packed=gpu->frames[group*gpu->rows+frame];
        if(!packed.w || !packed.h)return true;
        const double fullLeft=(double(x)+source->width/2-gpu->anchorX+out.region.x)*scale+offsetX;
        const double fullTop=(double(y)+1-gpu->anchorY+out.region.y)*scale;
        GpuSpriteDraw draw;draw.sheet=gpu;draw.frame=packed;
        draw.x=fullLeft+double(packed.cropX)*scale/gpu->density;draw.y=fullTop+double(packed.cropY)*scale/gpu->density;
        draw.w=double(packed.w)*scale/gpu->density;draw.h=double(packed.h)*scale/gpu->density;draw.alpha=blend?0.5f:1.0f;
        draw.maskX=std::max({int(std::floor(draw.x)),clip.x,out.region.x*scale+offsetX,0});
        draw.maskY=std::max({int(std::floor(draw.y)),out.region.y*scale,0});
        const int right=std::min({int(std::ceil(draw.x+draw.w)),clip.x+clip.w,(out.region.x+out.w())*scale+offsetX,world->w});
        const int bottom=std::min({int(std::ceil(draw.y+draw.h)),clip.h,(out.region.y+out.h())*scale,world->h});
        draw.maskW=right-draw.maskX;draw.maskH=bottom-draw.maskY;
        if(draw.maskW<=0 || draw.maskH<=0)return true;
        draw.coverage.assign(size_t(draw.maskW)*draw.maskH*4,0);draw.lighting.assign(size_t(draw.maskW)*draw.maskH,0);
        for(int py=0;py<draw.maskH;++py)for(int px=0;px<draw.maskW;++px){
            const size_t i=size_t(py)*draw.maskW+px;draw.coverage[i*4+3]=255;
            if(lightmap){const int lx=(draw.maskX+px-offsetX)/scale-out.region.x,ly=(draw.maskY+py)/scale-out.region.y;
                draw.lighting[i]=std::min<unsigned>(15,*lightmap->getLightingAt(out.at(lx,ly)));}
        }
        draw.palette.resize(256*17*4);
        for(unsigned index=0;index<256;++index){
            const auto &base=matchingPalette[index];auto *dst=draw.palette.data()+index*4;dst[0]=base.r;dst[1]=base.g;dst[2]=base.b;dst[3]=255;
            uint8_t mapped=header[18+index];if(translation)mapped=translation[mapped];
            for(unsigned level=0;level<16;++level){const auto color=devilution::Palette->colors[lightmap?lightmap->adjustColor(mapped,level):mapped];
                auto *row=draw.palette.data()+((level+1)*256+index)*4;row[0]=color.r;row[1]=color.g;row[2]=color.b;row[3]=255;}
        }
        QueueGpuSprite(std::move(draw));return true;
    }
    auto &image = LoadSheet(*source)->image;
    if (image.rgba.empty()) return false;
    const auto *header = sprite.pixelData() - SheetHeaderSize;
    const unsigned group = devilution::LoadLE16(header + 14), frame = devilution::LoadLE16(header + 16);
    if (group >= source->columns || frame >= source->rows || image.cellHeight / image.density < sprite.height()) return false;
    const int logicalHeight = image.cellHeight / image.density;
    const int64_t top = int64_t(y) + 1 - image.anchorY;
    const int64_t left = (int64_t(x) + source->width / 2 - image.anchorX + out.region.x) * scale + offsetX;
    const int64_t upper = (top + out.region.y) * scale;
    const int64_t w = int64_t(image.logicalWidth) * scale, h = int64_t(logicalHeight) * scale;
    const auto *bakedTranslation = header + 18;
    // Clip in the caller's local coordinates as well as to the world viewport.
    const int64_t xBegin = std::max<int64_t>({left, clip.x, out.region.x * scale + offsetX, 0});
    const int64_t xEnd = std::min<int64_t>({left + w, clip.x + clip.w, (out.region.x + out.w()) * scale + offsetX, world->w});
    const int64_t yBegin = std::max<int64_t>({upper, out.region.y * scale, 0});
    const int64_t yEnd = std::min<int64_t>({upper + h, clip.h, (out.region.y + out.h()) * scale, world->h});
    if (xBegin >= xEnd || yBegin >= yEnd) return true;
    // Nonempty clipped bounds are inside the actual screen, even when the
    // source canvas/anchor is too large for 32-bit intermediate arithmetic.
    for (int py = static_cast<int>(yBegin); py < yEnd; ++py) {
        const unsigned sy = frame * image.cellHeight + (py - upper) * image.density / scale;
        auto *dst = static_cast<uint8_t *>(world->pixels) + py * world->pitch;
        for (int px = static_cast<int>(xBegin); px < xEnd; ++px) {
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
                if(c==0) {
                    uint8_t rgb[3];
                    for(int channel=0;channel<3;++channel)rgb[channel]=std::clamp(litChannels[channel]+(int(src[channel])-originalChannels[channel])*intensity/256,0,255);
                    MaskGpuSpritePixel(px,py,rgb[0],rgb[1],rgb[2],alpha);
                }
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
    SetGpuSpriteFrameReady(devilution::gbRunGame && HdCaptureActive && ready && GetRendererSwitch().usesHdRenderer());
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
bool BeginHdPlayerPreload(const std::string &classPath)
{
    const std::lock_guard<std::mutex> lock(sheetMutex);
    if (preloadedPlayerClass == classPath) return false;
    for (auto it = sheets.begin(); it != sheets.end();) {
        if (it->second.pinned) { sheetBytes -= it->second.image.rgba.size(); it = sheets.erase(it); }
        else ++it;
    }
    pinnedSheetBytes = 0;
    preloadedPlayerClass = classPath;
    ReleaseGpuPlayerSheets();
    return true;
}
bool PreloadHdPlayerSheet(const SheetSource &source) { return bool(LoadGpuPlayerSheet(source)) || !LoadSheet(source, true)->image.rgba.empty(); }
HdCacheMetrics GetHdCacheMetrics()
{
    const std::lock_guard<std::mutex> lock(sheetMutex);
    auto result = cacheMetrics;
    result.bytes = sheetBytes;
    for (const auto &entry : sheets) if (!entry.second.image.rgba.empty()) ++result.sheets;
    for (const auto &entry : sheets) if (entry.second.pinned && !entry.second.image.rgba.empty()) ++result.pinned;
    const auto gpu=GetGpuSpriteStats();result.sheets+=gpu.sheets;result.pinned+=gpu.sheets;
    return result;
}
HdPlayerCacheStats GetHdPlayerCacheStats()
{
    const std::lock_guard<std::mutex> lock(sheetMutex);
    size_t count = 0;
    for (const auto &entry : sheets) if (entry.second.pinned && !entry.second.image.rgba.empty()) ++count;
    return {count+GetGpuSpriteStats().sheets, pinnedSheetBytes};
}
void ReleaseHdPlayerSheets()
{
    BeginGpuSpriteFrame();
    ReleaseGpuPlayerSheets();
    {
        const std::lock_guard<std::mutex> lock(sheetMutex);
        preloadedPlayerClass.clear();
        for (auto &entry : sheets) entry.second.pinned = false;
        pinnedSheetBytes = 0;
    }
    ResetHdAssets();
}
void ResetHdAssets()
{
    BeginGpuSpriteFrame();
    const std::lock_guard<std::mutex> lock(sheetMutex);
    HdCaptureActive = false; inWorld = false; ready = false; suppressed = false;
    assets.clear(); world.reset(); ui.reset(); composed.reset(); beforeUi.clear(); cursorBehind.clear(); cursorSaved = false;
    for (auto it = sheets.begin(); it != sheets.end();) {
        if (!it->second.pinned) { sheetBytes -= it->second.image.rgba.size(); it = sheets.erase(it); }
        else ++it;
    }
    nearestColors.clear();
    cacheWarningFlags = 0; processWarningFlags = 0;
}
}
#endif
