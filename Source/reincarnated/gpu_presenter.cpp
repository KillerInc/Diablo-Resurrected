#include "gpu_presenter.hpp"
#include "gpu_sprites.hpp"
#ifdef USE_SDL3
#include <algorithm>
#include <cmath>
#include <cstring>
#include <string>
#include <SDL3_image/SDL_image.h>
#include "game_mode.hpp"
#include "gmenu.h"
#include "hd_renderer.hpp"
#include <SDL3/SDL_gpu.h>
#include <SDL3/SDL_surface.h>
#include <SDL3/SDL_video.h>
#include "options.h"
#include "utils/display.h"
#include "utils/log.hpp"
#include "utils/sdl_wrap.h"
namespace reincarnated {
namespace {
SDL_GPUDevice *device;
SDL_Window *window;
SDL_GPUTexture *frame;
SDL_GPUTexture *scene;
int sceneWidth=0,sceneHeight=0;
SDL_GPUTransferBuffer *upload;
int frameWidth, frameHeight;
SDL_GPUPresentMode presentMode = SDL_GPU_PRESENTMODE_VSYNC;
struct View { int x, y, w, h; };
View Viewport(int width, int height)
{
    float scale = std::min(float(width) / devilution::gnScreenWidth, float(height) / devilution::gnScreenHeight);
    if (*devilution::GetOptions().Graphics.integerScaling && scale >= 1) scale = std::floor(scale);
    const int w = std::max(1, int(devilution::gnScreenWidth * scale));
    const int h = std::max(1, int(devilution::gnScreenHeight * scale));
    return { (width - w) / 2, (height - h) / 2, w, h };
}
void ReleaseFrame()
{
    if (scene) SDL_ReleaseGPUTexture(device,scene);
    scene=nullptr;sceneWidth=sceneHeight=0;
    if (frame) SDL_ReleaseGPUTexture(device, frame);
    if (upload) SDL_ReleaseGPUTransferBuffer(device, upload);
    frame = nullptr; upload = nullptr;
}
}
bool HasGpuPresenter() { return device != nullptr; }
void InitializeGpuPresenter(SDL_Window *target)
{
    if (device) return;
    // A window has exactly one presentation owner. No SDL_Renderer is created
    // on this window, even in Classic mode or on F10 transitions.
    device = SDL_CreateGPUDevice(SDL_GPU_SHADERFORMAT_SPIRV | SDL_GPU_SHADERFORMAT_DXIL | SDL_GPU_SHADERFORMAT_DXBC, false, nullptr);
    if (!device) devilution::ErrSdl();
    if (!SDL_ClaimWindowForGPUDevice(device, target)) devilution::ErrSdl();
    window = target;
    InitializeGpuSprites(device);
    devilution::Log("SDL_GPU shared presenter: {}", SDL_GetGPUDeviceDriver(device));
}
void DestroyGpuPresenter()
{
    if (!device) return;
    SDL_WaitForGPUIdle(device);
    ReleaseFrame();
    DestroyGpuSprites();
    SDL_ReleaseWindowFromGPUDevice(device, window);
    SDL_DestroyGPUDevice(device);
    device = nullptr; window = nullptr;
}
void GpuWindowToLogical(float &x, float &y, bool inverse)
{
    int w, h, pw, ph;
    if (!SDL_GetWindowSize(window, &w, &h) || !SDL_GetWindowSizeInPixels(window, &pw, &ph)) devilution::ErrSdl();
    const View v = Viewport(pw, ph);
    if (inverse) {
        x = (x * v.w / devilution::gnScreenWidth + v.x) * w / pw;
        y = (y * v.h / devilution::gnScreenHeight + v.y) * h / ph;
    } else {
        x = (x * pw / w - v.x) * devilution::gnScreenWidth / v.w;
        y = (y * ph / h - v.y) * devilution::gnScreenHeight / v.h;
    }
}
void PresentGpuFrame(SDL_Surface *surface)
{
    if (!frame || frameWidth != surface->w || frameHeight != surface->h) {
        ReleaseFrame();
        frameWidth = surface->w; frameHeight = surface->h;
        SDL_GPUTextureCreateInfo info {};
        info.type = SDL_GPU_TEXTURETYPE_2D;
        info.format = SDL_GPU_TEXTUREFORMAT_R8G8B8A8_UNORM;
        info.usage = SDL_GPU_TEXTUREUSAGE_SAMPLER;
        info.width = frameWidth; info.height = frameHeight;
        info.layer_count_or_depth = 1; info.num_levels = 1;
        frame = SDL_CreateGPUTexture(device, &info);
        SDL_GPUTransferBufferCreateInfo transfer {};
        transfer.usage = SDL_GPU_TRANSFERBUFFERUSAGE_UPLOAD;
        transfer.size = frameWidth * frameHeight * 4;
        upload = SDL_CreateGPUTransferBuffer(device, &transfer);
        if (!frame || !upload) devilution::ErrSdl();
    }
    const auto mode = *devilution::GetOptions().Graphics.frameRateControl == devilution::FrameRateControl::VerticalSync
        ? SDL_GPU_PRESENTMODE_VSYNC : SDL_GPU_PRESENTMODE_IMMEDIATE;
    if (mode != presentMode && SDL_WindowSupportsGPUPresentMode(device, window, mode)) {
        if (!SDL_SetGPUSwapchainParameters(device, window, SDL_GPU_SWAPCHAINCOMPOSITION_SDR, mode)) devilution::ErrSdl();
        presentMode = mode;
    }
    auto *mapped = static_cast<uint8_t *>(SDL_MapGPUTransferBuffer(device, upload, true));
    if (!mapped) devilution::ErrSdl();
    if (!SDL_ConvertPixels(surface->w, surface->h, surface->format, surface->pixels, surface->pitch,
            SDL_PIXELFORMAT_RGBA32, mapped, frameWidth * 4)) devilution::ErrSdl();
    SDL_UnmapGPUTransferBuffer(device, upload);
    SDL_GPUCommandBuffer *cmd = SDL_AcquireGPUCommandBuffer(device);
    if (!cmd) devilution::ErrSdl();
    SDL_GPUTexture *swapchain;
    Uint32 w, h;
    if (!SDL_WaitAndAcquireGPUSwapchainTexture(cmd, window, &swapchain, &w, &h)) devilution::ErrSdl();
    SDL_GPUTransferBuffer *readback = nullptr;
    static unsigned captureFrame = 0;
    const char *captureDirectory = SDL_getenv("D1R_FRAME_DUMP");
    const bool capture = captureDirectory && devilution::gbRunGame && (++captureFrame % 100 == 50);
    if (swapchain) {
        auto *copy = SDL_BeginGPUCopyPass(cmd);
        SDL_GPUTextureTransferInfo src {};
        src.transfer_buffer = upload;
        SDL_GPUTextureRegion dst {};
        dst.texture = frame; dst.w = frameWidth; dst.h = frameHeight; dst.d = 1;
        SDL_UploadToGPUTexture(copy, &src, &dst, true);
        SDL_EndGPUCopyPass(copy);
        const View v = Viewport(w, h);
        SDL_GPUTexture *display=frame;
        int displayW=frameWidth,displayH=frameHeight;
        if(GpuSpriteFrameReady()) {
            if(!scene || sceneWidth!=v.w || sceneHeight!=v.h) {
                if(scene)SDL_ReleaseGPUTexture(device,scene);
                SDL_GPUTextureCreateInfo info{};info.type=SDL_GPU_TEXTURETYPE_2D;info.format=SDL_GPU_TEXTUREFORMAT_R8G8B8A8_UNORM;
                info.usage=SDL_GPU_TEXTUREUSAGE_SAMPLER|SDL_GPU_TEXTUREUSAGE_COLOR_TARGET;info.width=v.w;info.height=v.h;info.layer_count_or_depth=1;info.num_levels=1;
                scene=SDL_CreateGPUTexture(device,&info);sceneWidth=v.w;sceneHeight=v.h;
                if(!scene)devilution::ErrSdl();
            }
            SDL_GPUBlitInfo base{};base.source.texture=frame;base.source.w=frameWidth;base.source.h=frameHeight;
            base.destination.texture=scene;base.destination.w=sceneWidth;base.destination.h=sceneHeight;
            base.load_op=SDL_GPU_LOADOP_DONT_CARE;base.filter=SDL_GPU_FILTER_NEAREST;SDL_BlitGPUTexture(cmd,&base);
            RenderGpuSprites(cmd,scene,frameWidth,frameHeight,sceneWidth,sceneHeight);
            display=scene;displayW=sceneWidth;displayH=sceneHeight;
        }
        if(capture) {
            SDL_GPUTransferBufferCreateInfo readInfo{};readInfo.usage=SDL_GPU_TRANSFERBUFFERUSAGE_DOWNLOAD;readInfo.size=displayW*displayH*4;
            readback=SDL_CreateGPUTransferBuffer(device,&readInfo);if(!readback)devilution::ErrSdl();
            auto *readCopy=SDL_BeginGPUCopyPass(cmd);SDL_GPUTextureRegion from{};from.texture=display;from.w=displayW;from.h=displayH;from.d=1;
            SDL_GPUTextureTransferInfo to{};to.transfer_buffer=readback;SDL_DownloadFromGPUTexture(readCopy,&from,&to);SDL_EndGPUCopyPass(readCopy);
        }
        SDL_GPUBlitInfo blit {};
        blit.source.texture = display; blit.source.w = displayW; blit.source.h = displayH;
        blit.destination.texture = swapchain;
        blit.destination.x = v.x; blit.destination.y = v.y; blit.destination.w = v.w; blit.destination.h = v.h;
        blit.load_op = SDL_GPU_LOADOP_CLEAR;
        blit.clear_color = { 0, 0, 0, 1 };
        blit.filter = *devilution::GetOptions().Graphics.scaleQuality == devilution::ScalingQuality::NearestPixel
            ? SDL_GPU_FILTER_NEAREST : SDL_GPU_FILTER_LINEAR;
        SDL_BlitGPUTexture(cmd, &blit);
    }
    if (readback) {
        auto *fence = SDL_SubmitGPUCommandBufferAndAcquireFence(cmd);
        if (!fence || !SDL_WaitForGPUFences(device, true, &fence, 1)) devilution::ErrSdl();
        void *pixels = SDL_MapGPUTransferBuffer(device, readback, false);
        if (!pixels) devilution::ErrSdl();
        const bool high=GpuSpriteFrameReady();
        const int dw=high?sceneWidth:frameWidth,dh=high?sceneHeight:frameHeight;
        auto *dump = SDL_CreateSurfaceFrom(dw, dh, SDL_PIXELFORMAT_RGBA32, pixels, dw * 4);
        if (!dump) devilution::ErrSdl();
        const std::string name = std::string(captureDirectory) + "/gpu-" + std::to_string(captureFrame)
            + (GetRendererSwitch().usesHdRenderer() ? "-HD" : "-Classic")
            + (devilution::gmenu_is_active() ? "-menu" : "") + ".png";
        if (!IMG_SavePNG(dump, name.c_str())) devilution::ErrSdl();
        SDL_DestroySurface(dump);
        SDL_UnmapGPUTransferBuffer(device, readback);
        SDL_ReleaseGPUFence(device, fence);
        SDL_ReleaseGPUTransferBuffer(device, readback);
    } else if (!SDL_SubmitGPUCommandBuffer(cmd)) devilution::ErrSdl();
}
}
#endif
