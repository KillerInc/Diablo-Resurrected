#ifdef USE_SDL3
#include "hd_renderer.hpp"
#include "raster_bridge.hpp"
#include "gpu_sprites.hpp"
#include "gpu_ui.hpp"
#include "world_sprite_indices.hpp"
#include "gpu_terrain.hpp"
#include "cpu_profile.hpp"
#include "controls/control_mode.hpp"
#include <algorithm>
#include <bit>
#include <cmath>
#include <filesystem>
#include <charconv>
#include <cstring>
#include <sstream>
#include <mutex>
#include <unordered_map>
#include <vector>
#include <SDL3/SDL_surface.h>
#include <SDL3/SDL_timer.h>
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
static bool standaloneUi = false, standalonePresented = true;
static bool uiRasterDirty = false, uiWasTerrain = false;
namespace {
struct Asset {
    devilution::SDLSurfaceUniquePtr surface;
    float w = 0, h = 0, px = 0, py = 0;
    bool layout = false;
};
std::unordered_map<std::string, Asset> assets;
devilution::SDLSurfaceUniquePtr world, ui, composed;
devilution::SDLSurfaceUniquePtr hudIndexed, hudRgba;
SDL_Rect hudRect {};
std::array<SDL_Color, 256> hudPalette {};
bool hudValid = false;
std::vector<uint8_t> beforeUi;
std::vector<uint8_t> cursorBehind;
SDL_Rect cursorRect {};
bool cursorSaved = false;
bool inWorld, ready, suppressed;
int scale = 1, offsetX;
SDL_Rect clip;

std::mutex sheetMutex;
std::string preloadedPlayerClass;
std::array<SDL_Color, 256> matchingPalette {};
struct DrawProfile { uint64_t opaqueSpans=0,opaquePixels=0,blendSpans=0,blendPixels=0,gpuPrepareNs=0,sprites=0; };
DrawProfile drawProfile;
bool profileFrame=false;
std::vector<uint32_t> blendedColors;
std::vector<uint8_t> terrainBlend;


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
    if(!inWorld)uiRasterDirty=true;
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
                if (!inWorld && !GpuTerrainActive() && dst[3] == 0) {
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
            dst[3] = GpuTerrainActive() && !inWorld ? (blend ? dst[3]/2 : 0) : 255;
        }
    }
}
Asset *Load(const std::string &path)
{
    if (path.ends_with(".png")) return nullptr; // HD world assets are compiled offline.
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
    if (!HdCaptureActive || !inWorld || GpuTerrainActive() || nominalW <= 0 || nominalH <= 0) return false;
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
        const int x1=std::min({dst.x+dst.w,clip.x+clip.w,world->w}),y1=std::min({dst.y+dst.h,clip.h,int(devilution::gnScreenHeight)});
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
        // Keep the last occurrence at its original priority when executable,
        // data and current directories identify the same physical pack.
        const std::string roots[] { devilution::paths::AssetsPath(),
            devilution::paths::ExecutablePath(), devilution::paths::BasePath(),
            devilution::paths::PrefPath(), "." };
        std::vector<std::filesystem::path> mounted;
        std::vector<std::string> unique;
        for (size_t i = 5; i > 0; --i) {
            const auto &root = roots[i - 1];
            std::error_code error;
            const auto path = std::filesystem::weakly_canonical(root, error);
            if (!error && std::find(mounted.begin(), mounted.end(), path) != mounted.end()) continue;
            unique.push_back(root);
            if (!error) mounted.push_back(path);
        }
        for (auto it = unique.rbegin(); it != unique.rend(); ++it) store.mountLoose(*it);
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
    if(!inWorld)uiRasterDirty=true;
    length = std::min(length, unsigned(devilution::PalSurface->w - x));
    if(profileFrame){++drawProfile.opaqueSpans;drawProfile.opaquePixels+=length;}
    if(inWorld&&GpuTerrainActive()){CaptureGpuTerrainOpaque(x,y,src,length);return;}
    SDL_Surface *target = inWorld ? world.get() : ui.get();
    const int zoom = inWorld ? scale : 1;
    if (zoom != 1 && zoom != 2) {
        for (unsigned i=0;i<length;++i) Pixel(x+i,y,devilution::Palette->colors[src[i]],false);
        return;
    }
    const int rawLeft=x*zoom+(inWorld?offsetX:0), top=y*zoom;
    const int left=std::max(rawLeft,inWorld?std::max(0,clip.x):0);
    const int right=std::min(rawLeft+int(length)*zoom,inWorld?std::min(target->w,clip.x+clip.w):target->w);
    const int bottom=std::min(top+zoom,inWorld?std::min(target->h,clip.h):target->h);
    if(left>=right||top<0||top>=bottom)return;
    auto *first=static_cast<uint8_t*>(target->pixels)+top*target->pitch+left*4;
    auto *dst=reinterpret_cast<uint32_t*>(first);
    const auto color=[&](unsigned index){
        auto c=devilution::Palette->colors[src[index]];c.a=GpuTerrainActive()&&!inWorld?0:255;
        return std::bit_cast<uint32_t>(c);
    };
    int px=left;
    if(zoom==2){
        if((px-rawLeft)&1){*dst++=color((px-rawLeft)/2);++px;}
        for(;px+1<right;px+=2){const auto c=color((px-rawLeft)/2);*dst++=c;*dst++=c;}
        if(px<right)*dst=color((px-rawLeft)/2);
    }else{
        for(;px<right;++px)*dst++=color(px-rawLeft);
    }
    for(int row=top;row<bottom;++row){
        if(row!=top)std::memcpy(static_cast<uint8_t*>(target->pixels)+row*target->pitch+left*4,first,size_t(right-left)*4);
        MaskGpuSpriteOpaqueSpan(left,row,unsigned(right-left));
    }
}
void MirrorBlend(const uint8_t *dst, unsigned length, const uint8_t *src, uint8_t color,
    const uint8_t *map, const devilution::Lightmap *lightmap)
{
    int x, y;
    if (!SourcePosition(dst, x, y)) return;
    if(!inWorld)uiRasterDirty=true;
    const uint8_t *light = lightmap ? lightmap->getLightingAt(dst) : nullptr;
    length = std::min(length, unsigned(devilution::PalSurface->w - x));
    if(profileFrame){++drawProfile.blendSpans;drawProfile.blendPixels+=length;}
    if(inWorld&&GpuTerrainActive()){
        terrainBlend.resize(length);
        for(unsigned i=0;i<length;++i){uint8_t index=src?src[i]:color;if(map)index=map[index];if(lightmap)index=lightmap->adjustColor(index,light[i]);terrainBlend[i]=index;}
        CaptureGpuTerrainBlend(x,y,terrainBlend.data(),length);return;
    }
    SDL_Surface *target=inWorld?world.get():ui.get();
    const int zoom=inWorld?scale:1;
    if(zoom!=1&&zoom!=2){
        for(unsigned i=0;i<length;++i){uint8_t index=src?src[i]:color;if(map)index=map[index];if(lightmap)index=lightmap->adjustColor(index,light[i]);Pixel(x+i,y,devilution::Palette->colors[index],true);}
        return;
    }
    const int rawLeft=x*zoom+(inWorld?offsetX:0),top=y*zoom;
    const int left=std::max(rawLeft,inWorld?std::max(0,clip.x):0);
    const int right=std::min(rawLeft+int(length)*zoom,inWorld?std::min(target->w,clip.x+clip.w):target->w);
    const int bottom=std::min(top+zoom,inWorld?std::min(target->h,clip.h):target->h);
    if(left>=right||top<0||top>=bottom)return;
    const unsigned count=unsigned(right-left);
    if(blendedColors.size()<count)blendedColors.resize(count);
    const auto packedColor=[&](unsigned i){uint8_t index=src?src[i]:color;if(map)index=map[index];if(lightmap)index=lightmap->adjustColor(index,light[i]);auto c=devilution::Palette->colors[index];c.a=255;return std::bit_cast<uint32_t>(c);};
    if(!src&&!lightmap){std::fill_n(blendedColors.data(),count,packedColor(0));}
    else if(zoom==2){
        int px=left;auto *dst=blendedColors.data();
        if((px-rawLeft)&1){*dst++=packedColor((px-rawLeft)/2);++px;}
        for(;px+1<right;px+=2){const auto c=packedColor((px-rawLeft)/2);*dst++=c;*dst++=c;}
        if(px<right)*dst=packedColor((px-rawLeft)/2);
    }else for(int px=left;px<right;++px)blendedColors[px-left]=packedColor(px-rawLeft);
    const uint32_t alpha=std::bit_cast<uint32_t>(SDL_Color{0,0,0,255});
    for(int py=top;py<bottom;++py){
        auto *dst=reinterpret_cast<uint32_t*>(static_cast<uint8_t*>(target->pixels)+py*target->pitch)+left;
        for(int px=left;px<right;++px){
            uint32_t old=dst[px-left];
            if(!inWorld&&!GpuTerrainActive()&&(old&alpha)==0){
                if(px>=clip.x&&px<clip.x+clip.w&&py<clip.h)
                    std::memcpy(&old,static_cast<const uint8_t*>(world->pixels)+py*world->pitch+px*4,4);
                else{const auto index=*(static_cast<const uint8_t*>(devilution::PalSurface->pixels)+py*devilution::PalSurface->pitch+px);auto c=devilution::Palette->colors[index];c.a=255;old=std::bit_cast<uint32_t>(c);}
            }
            const uint32_t incoming=blendedColors[px-left];
            // Per-byte floor((old+incoming)/2), without carries across channels.
            const uint32_t average=(old&incoming)+(((old^incoming)&0xFEFEFEFEU)>>1);
            if(!inWorld&&GpuTerrainActive()){
                auto result=std::bit_cast<SDL_Color>(average);result.a=std::bit_cast<SDL_Color>(old).a/2;dst[px-left]=std::bit_cast<uint32_t>(result);
            }else dst[px-left]=average|alpha;
        }
        MaskGpuSpriteBlendedSpan(left,py,blendedColors.data(),count);
    }
}
void BeginHdWorldFrame(int zoom, int xOffset, int clipX, int clipWidth, int clipHeight)
{
    BeginGpuSpriteFrame();
    standaloneUi = false; ForgetGpuUiScene(); BeginGpuUiFrame(false);
    static const bool profileEnabled=SDL_getenv("D1R_PROFILE_HD")!=nullptr;
    profileFrame=profileEnabled;drawProfile={};
    HdCaptureActive = GetRendererSwitch().usesHdRenderer();
    ready = false; suppressed = false; cursorSaved = false;
    if (!HdCaptureActive){ResetGpuTerrainFrame();return;}
    if (std::memcmp(matchingPalette.data(), devilution::logical_palette.data(), sizeof(matchingPalette)) != 0) {
        matchingPalette = devilution::logical_palette;
    }
    const bool uiNeedsClear=!ui || ui->w!=devilution::gnScreenWidth || ui->h!=devilution::gnScreenHeight || uiRasterDirty;
    EnsureSurface(ui);
    scale = zoom; offsetX = xOffset;
    clip = { clipX, 0, clipWidth, clipHeight };
    const bool gpuTerrain=BeginGpuTerrainFrame(zoom,xOffset,clipX,clipWidth,clipHeight);
    if(GpuTerrainNeedsCpuCanvas())EnsureSurface(composed);else composed.reset();
    if(gpuTerrain)world.reset();
    else{
        EnsureSurface(world);
        SDL_SetSurfaceClipRect(world.get(), nullptr);
        SDL_FillSurfaceRect(world.get(), nullptr, SDL_MapSurfaceRGBA(world.get(), 0, 0, 0, 255));
        SDL_SetSurfaceClipRect(world.get(), &clip);
    }
    if(uiNeedsClear || gpuTerrain!=uiWasTerrain || !GpuUiEnabled())SDL_FillSurfaceRect(ui.get(), nullptr, gpuTerrain?SDL_MapSurfaceRGBA(ui.get(),0,0,0,255):0);
    uiWasTerrain=gpuTerrain;uiRasterDirty=false;
    inWorld = true;
}
void EndHdWorldFrame()
{
    if (!HdCaptureActive) return;
    inWorld = false; ready = true;
    EnterGpuUiPhase();
    EndGpuTerrainFrame();
    auto *pal = devilution::PalSurface;
    beforeUi.assign(static_cast<uint8_t *>(pal->pixels), static_cast<uint8_t *>(pal->pixels) + size_t(pal->pitch) * pal->h);
}
void MarkHdUiPresented(){standalonePresented=true;}
void BeginHdUiFrame(bool force)
{
    if(!force && standaloneUi && !standalonePresented)return;
    standalonePresented=false;ForgetGpuUiScene();
    BeginGpuSpriteFrame(); ResetGpuTerrainFrame();
    uiRasterDirty=true;
    standaloneUi = true; inWorld = false; suppressed = false; cursorSaved = false;
    HdCaptureActive = GpuUiEnabled(); ready = HdCaptureActive;
    BeginGpuUiFrame(true);
    if (!HdCaptureActive) return;
    EnsureSurface(ui); SDL_FillSurfaceRect(ui.get(), nullptr, 0);
    clip = { 0, 0, int(devilution::gnScreenWidth), 0 };
}
bool PrepareHdHudLayer(int x, int y, int width, int height)
{
    if (!GetRendererSwitch().usesHdRenderer()) return false;
    const SDL_Rect requested { x, y, width, height };
    if (!hudIndexed || hudIndexed->w != devilution::gnScreenWidth || hudIndexed->h != devilution::gnScreenHeight) {
        hudIndexed.reset(SDL_CreateSurface(devilution::gnScreenWidth, devilution::gnScreenHeight, SDL_PIXELFORMAT_INDEX8));
        if (!hudIndexed) devilution::ErrSdl();
        EnsureSurface(hudRgba);
        hudValid = false;
    }
    if (!SDL_SetSurfacePalette(hudIndexed.get(), devilution::Palette.get())) devilution::ErrSdl();
    if (!SDL_RectsEqual(&hudRect, &requested)
        || std::memcmp(hudPalette.data(), devilution::Palette->colors, sizeof(hudPalette)) != 0) {
        hudRect = requested;
        std::memcpy(hudPalette.data(), devilution::Palette->colors, sizeof(hudPalette));
        hudValid = false;
    }
    return hudValid;
}
devilution::Surface HdHudLayerTarget(const devilution::Surface &fallback)
{
    if (!HdCaptureActive || !hudIndexed) return fallback;
    return devilution::Surface(hudIndexed.get());
}
void CommitHdHudLayer(bool changed)
{
    uiRasterDirty=true;
    if (!HdCaptureActive || !ready || !hudIndexed) return;
    const SDL_Rect bounds { 0, 0, hudIndexed->w, hudIndexed->h };
    SDL_Rect area;
    if (!SDL_GetRectIntersection(&hudRect, &bounds, &area)) return;
    if (changed || !hudValid) {
        // Convert only when a component changes. Raw indexed UI writers are
        // included here, without relying on raster-span interception.
        for (int y = area.y; y < area.y + area.h; ++y) {
            const auto *src = static_cast<const uint8_t *>(hudIndexed->pixels) + y * hudIndexed->pitch;
            auto *dst = reinterpret_cast<SDL_Color *>(static_cast<uint8_t *>(hudRgba->pixels) + y * hudRgba->pitch);
            for (int x = area.x; x < area.x + area.w; ++x) {
                dst[x] = devilution::Palette->colors[src[x]];
                dst[x].a = 255;
            }
        }
        hudValid = true;
    }
    for (int y = area.y; y < area.y + area.h; ++y) {
        std::memcpy(static_cast<uint8_t *>(devilution::PalSurface->pixels) + y * devilution::PalSurface->pitch + area.x,
            static_cast<const uint8_t *>(hudIndexed->pixels) + y * hudIndexed->pitch + area.x, area.w);
        std::memcpy(static_cast<uint8_t *>(ui->pixels) + y * ui->pitch + area.x * 4,
            static_cast<const uint8_t *>(hudRgba->pixels) + y * hudRgba->pitch + area.x * 4, size_t(area.w) * 4);
        if(GpuTerrainActive()){
            auto *pixels=reinterpret_cast<SDL_Color*>(static_cast<uint8_t*>(ui->pixels)+y*ui->pitch);
            for(int x=area.x;x<area.x+area.w;++x)pixels[x].a=0;
        }
        MaskGpuSpriteOpaqueSpan(area.x, y, area.w);
    }
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
    return source && bool(LoadGpuSheet(*source));
}

bool DrawHdSheet(const devilution::Surface &out, int x, int y, devilution::ClxSprite sprite,
    const uint8_t *translation, const devilution::Lightmap *lightmap, bool blend, int outline)
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
    if (auto gpu = devilution::ControlMode != devilution::ControlTypes::VirtualGamepad ? LoadGpuSheet(*source) : std::shared_ptr<GpuSheet>{}) {
        // Unmodified art and Classic keep their native outline/occupancy rules.
        if (outline >= 0 && !gpu->authoredTowner) return false;
        const uint64_t profileStarted=profileFrame?SDL_GetTicksNS():0;
        const auto *header=sprite.pixelData()-SheetHeaderSize;
        const unsigned group=devilution::LoadLE16(header+14), frame=devilution::LoadLE16(header+16);
        if(group>=gpu->columns || frame>=gpu->rows)return false;
        const auto &packed=gpu->frames[group*gpu->rows+frame];
        if(!packed.w || !packed.h)return true;
        const double fullLeft=(double(x)+source->width/2-gpu->anchorX+out.region.x)*scale+offsetX;
        const double fullTop=(double(y)+1-gpu->anchorY+out.region.y)*scale;
        GpuSpriteDraw draw;draw.sheet=gpu;draw.frame=packed;
        const bool nativeIndices=UsesNativeWorldIndices(*source)&&!gpu->authoredTowner;
        const auto *sourcePalette=nativeIndices?WorldSourcePalette():nullptr;
        if(nativeIndices){
            if(!sourcePalette)return false;
            draw.uiIndices=WorldSpriteIndices(sprite);if(!draw.uiIndices)return false;
            draw.uiX=float((x+out.region.x)*scale+offsetX);draw.uiY=float((y+1-sprite.height()+out.region.y)*scale);
            draw.uiScaleX=draw.uiScaleY=1.0f/scale;
        }
        draw.x=fullLeft+double(packed.cropX)*scale/gpu->density;draw.y=fullTop+double(packed.cropY)*scale/gpu->density;
        draw.w=double(packed.w)*scale/gpu->density;draw.h=double(packed.h)*scale/gpu->density;draw.alpha=blend?0.5f:1.0f;
        if (outline >= 0) {
            draw.outlineRadius = gpu->density;
            const auto color = devilution::Palette->colors[outline];
            draw.outlineColor = { color.r / 255.0f, color.g / 255.0f, color.b / 255.0f, 1.0f };
            draw.x -= scale; draw.y -= scale;
            draw.w += 2 * scale; draw.h += 2 * scale;
        }
        draw.maskX=std::max({int(std::floor(draw.x)),clip.x,out.region.x*scale+offsetX,0});
        draw.maskY=std::max({int(std::floor(draw.y)),out.region.y*scale,0});
        const int right=std::min({int(std::ceil(draw.x+draw.w)),clip.x+clip.w,(out.region.x+out.w())*scale+offsetX,int(devilution::gnScreenWidth)});
        const int bottom=std::min({int(std::ceil(draw.y+draw.h)),clip.h,(out.region.y+out.h())*scale,int(devilution::gnScreenHeight)});
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
            const auto &base=nativeIndices?(*sourcePalette)[index]:matchingPalette[index];auto *dst=draw.palette.data()+index*4;dst[0]=base.r;dst[1]=base.g;dst[2]=base.b;dst[3]=255;
            uint8_t mapped=nativeIndices?uint8_t(index):header[18+index];if(translation)mapped=translation[mapped];
            for(unsigned level=0;level<16;++level){const auto color=devilution::Palette->colors[lightmap?lightmap->adjustColor(mapped,level):mapped];
                auto *row=draw.palette.data()+((level+1)*256+index)*4;row[0]=color.r;row[1]=color.g;row[2]=color.b;row[3]=255;}
        }
        if((nativeIndices||gpu->authoredTowner) && SDL_getenv("D1R_TRACE_WORLD_SHEETS")) {
            static std::unordered_map<std::string,bool> traced;
            if(traced.emplace(source->path,true).second)devilution::Log("HD_WORLD_DRAW source={} native_indices={} frames={}",source->path,nativeIndices?1:0,gpu->rows);
        }
        QueueGpuSprite(std::move(draw));
        if(profileFrame){++drawProfile.sprites;drawProfile.gpuPrepareNs+=SDL_GetTicksNS()-profileStarted;}
        return true;
    }
    return false; // Compiled resource unavailable: retain Classic pixels, never decode PNG.
}

bool DrawHdTownerWithOutline(const devilution::Surface &out, int x, int y, devilution::ClxSprite sprite, uint8_t color)
{
    if (!HdCaptureActive || !inWorld || suppressed || out.surface != devilution::PalSurface
        || devilution::ControlMode == devilution::ControlTypes::VirtualGamepad) return false;
    const auto *source = GetSheetSource(sprite);
    if (!source) return false;
    const auto sheet = LoadGpuSheet(*source);
    if (!sheet || !sheet->authoredTowner) return false;
    if (!DrawHdSheet(out, x, y, sprite)) return false;
    DrawHdSheet(out, x, y, sprite, nullptr, nullptr, false, color);
    return true;
}

bool QueueHdTile(int type, unsigned piece, int left, int bottom, int w, int h, int)
{
    const auto base = "hd/tiles/" + std::to_string(type) + "/" + std::to_string(piece);
    return Draw(base + ".png", left, bottom, w, h) || Draw(base + ".dds", left, bottom, w, h);
}
bool HasHdUiRaster(){return uiRasterDirty;}
SDL_Surface *GetHdUiSurface(){return ui.get();}
SDL_Surface *ComposeHdFrame(SDL_Surface *classic)
{
    SetGpuSpriteFrameReady((devilution::gbRunGame || standaloneUi) && HdCaptureActive && ready && GetRendererSwitch().usesHdRenderer());
    if (standaloneUi) return classic;
    if (!devilution::gbRunGame || !HdCaptureActive || !ready || !GetRendererSwitch().usesHdRenderer()) return classic;
    static unsigned profileFrames=0;
    if(profileFrame&&++profileFrames%100==0)devilution::Log("HD_DRAW_PROFILE sprites={} gpu_prepare_us={} opaque_spans={} opaque_pixels={} blend_spans={} blend_pixels={}",drawProfile.sprites,drawProfile.gpuPrepareNs/1000,drawProfile.opaqueSpans,drawProfile.opaquePixels,drawProfile.blendSpans,drawProfile.blendPixels);
    // Preserve persistent HUD/panel pixels, then replace the entire world
    // viewport with the independently assembled canvas. No flattened Classic
    // world is used as an HD background.
    { CpuStageScope profile(CpuStage::ClassicCopy);
      if (!GpuTerrainUsesIndexedPresent() && !SDL_BlitSurface(classic, nullptr, composed.get(), nullptr)) devilution::ErrSdl(); }
    { CpuStageScope profile(CpuStage::WorldCopy);
      if (!GpuTerrainReady() && !SDL_BlitSurface(world.get(), &clip, composed.get(), &clip)) devilution::ErrSdl(); }
    auto *pal = devilution::PalSurface;
    // Raw UI writers not using raster spans are also retained. Raster coverage
    // handles equal-color writes (which this supplemental pass cannot detect).
    CpuStageScope scanProfile(CpuStage::RawUiScan);
    for (int y = 0; y < clip.h; ++y) {
        const auto *src = static_cast<const uint8_t *>(pal->pixels) + y * pal->pitch;
        const auto *previous = beforeUi.data() + y * pal->pitch;
        // Most world rows receive no UI writes. The library comparison skips
        // those rows in bulk; changed rows retain the exact per-pixel fallback.
        if (std::memcmp(src + clip.x, previous + clip.x, clip.w) == 0) continue;
        // Automap strokes can touch most rows while leaving most pixels alone.
        // Bound the scalar fallback to changed blocks, including a short tail.
        for (int block = clip.x; block < clip.x + clip.w; block += 64) {
            const int end = std::min(block + 64, clip.x + clip.w);
            if (std::memcmp(src + block, previous + block, end - block) == 0) continue;
            for (int x = block; x < end; ++x)
                if (src[x] != previous[x]) {
                    const auto *coverage = static_cast<const uint8_t *>(ui->pixels) + y * ui->pitch + x * 4;
                    if (GpuTerrainReady()?coverage[3]==255:coverage[3]==0) Pixel(x, y, devilution::Palette->colors[src[x]], false);
                }
        }
    }
    scanProfile.finish();
    CpuStageScope compositeProfile(CpuStage::UiComposite);
    if(GpuTerrainReady())return GpuTerrainUsesIndexedPresent()?devilution::PalSurface:composed.get();
    SDL_SetSurfaceBlendMode(ui.get(), SDL_BLENDMODE_BLEND);
    if (!SDL_BlitSurface(ui.get(), nullptr, composed.get(), nullptr)) devilution::ErrSdl();
    return composed.get();
}
void PresentHdOverlay(SDL_Renderer *) {}
bool BeginHdPlayerPreload(const std::string &classPath)
{
    const std::lock_guard<std::mutex> lock(sheetMutex);
    if (preloadedPlayerClass == classPath) return false;
    preloadedPlayerClass = classPath;
    ReleaseGpuPlayerSheets();
    return true;
}
bool PreloadHdPlayerSheet(const SheetSource &source) { return bool(LoadGpuSheet(source)); }
HdCacheMetrics GetHdCacheMetrics()
{
    const auto gpu = GetGpuSpriteStats();
    HdCacheMetrics result;
    result.sheets = gpu.sheets;
    result.pinned = gpu.playerSheets;
    return result; // No decoded CPU sheet buffers or PNG cache.
}
HdPlayerCacheStats GetHdPlayerCacheStats()
{
    return {GetGpuSpriteStats().playerSheets, 0};
}
void ReleaseHdPlayerSheets()
{
    BeginGpuSpriteFrame();
    ReleaseGpuTerrainLevel();
    ReleaseGpuPlayerSheets();
    {
        const std::lock_guard<std::mutex> lock(sheetMutex);
        preloadedPlayerClass.clear();
    }
    ResetHdAssets();
}
void ResetHdAssets()
{
    ResetGpuTerrainFrame();
    BeginGpuSpriteFrame();
    HdCaptureActive = false; inWorld = false; ready = false; suppressed = false;
    standaloneUi = false; standalonePresented=true; ForgetGpuUiScene(); ResetGpuUiFrame();
    uiRasterDirty=true;uiWasTerrain=false;
    assets.clear(); world.reset(); ui.reset(); composed.reset(); beforeUi.clear(); cursorBehind.clear(); cursorSaved = false;
    hudIndexed.reset(); hudRgba.reset(); hudValid = false;
}
}
#endif
