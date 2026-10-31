#pragma once
#ifdef USE_SDL3
#include <SDL3/SDL_gpu.h>
#include <array>
#include <memory>
#include <vector>
#include "sheet_source.hpp"
namespace reincarnated {
struct GpuPage { SDL_GPUTexture *texture=nullptr; unsigned width=0,height=0; };
struct GpuFrame { unsigned page=0,x=0,y=0,w=0,h=0,cropX=0,cropY=0; };
struct GpuSheet {
    SDL_GPUDevice *owner=nullptr;
    unsigned density=0,columns=0,rows=0,width=0,height=0;
    int anchorX=0,anchorY=0;
    size_t bytes=0;
    std::vector<GpuPage> pages;
    std::vector<GpuFrame> frames;
    ~GpuSheet();
};
struct GpuSpriteDraw {
    std::shared_ptr<GpuSheet> sheet;
    GpuFrame frame;
    float x=0,y=0,w=0,h=0,alpha=1;
    int maskX=0,maskY=0,maskW=0,maskH=0;
    std::vector<unsigned char> coverage,lighting,palette,cursorCoverage;
};
struct GpuSpriteStats { size_t sheets=0,bytes=0,cpuMaskBytes=0; uint64_t uploads=0,draws=0; };
void InitializeGpuSprites(SDL_GPUDevice *device);
void DestroyGpuSprites();
std::shared_ptr<GpuSheet> LoadGpuPlayerSheet(const SheetSource &source);
void ReleaseGpuPlayerSheets();
GpuSpriteStats GetGpuSpriteStats();
void BeginGpuSpriteFrame();
void QueueGpuSprite(GpuSpriteDraw draw);
void MaskGpuSpritePixel(int x,int y,unsigned char r,unsigned char g,unsigned char b,unsigned alpha);
void SaveGpuSpriteCursor();
void RestoreGpuSpriteCursor();
bool HasQueuedGpuSprites();
bool GpuSpriteFrameReady();
void SetGpuSpriteFrameReady(bool ready);
void WarmGpuSpritePalette(const SDL_Color *palette);
void RenderGpuSprites(SDL_GPUCommandBuffer *command,SDL_GPUTexture *target,int logicalWidth,int logicalHeight,int pixelWidth,int pixelHeight);
}
#endif
