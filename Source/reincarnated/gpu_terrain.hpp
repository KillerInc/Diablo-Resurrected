#pragma once
#ifdef USE_SDL3
#include "engine/render/dun_render.hpp"
#include <SDL3/SDL_gpu.h>
#include <SDL3/SDL_surface.h>
#include <cstddef>
#include <cstdint>
#include <span>
#include <utility>
namespace devilution {
struct DunFrameInfo;
}
namespace reincarnated {
void InitializeGpuTerrain(SDL_GPUDevice *device);
void DestroyGpuTerrain();
void ReleaseGpuTerrainLevel();
void WarmGpuTerrain();
void RegisterGpuTerrain(const std::byte *cells, std::span<const std::pair<uint16_t, devilution::DunFrameInfo>> frames);
bool BeginGpuTerrainFrame(int zoom, int offset, int clipX, int clipWidth, int clipHeight);
void EndGpuTerrainFrame();
void ResetGpuTerrainFrame();
bool GpuTerrainActive();
bool GpuTerrainReady();
bool GpuTerrainUsesIndexedPresent();
bool GpuTerrainNeedsCpuCanvas();
bool GpuTerrainSkipsNativePainting();
bool IsGpuRc2RockCell(int x, int z, unsigned piece);
void SetGpuRc2RockGround(int left, int bottom);
bool HasGpuRc2RockGround();
void QueueGpuRc2RockShadow();
void QueueGpuRc2RockProp(int left, int bottom);
void SetGpuTerrainCell(int x, int z, unsigned piece);
class GpuTerrainCellScope {
public:
	GpuTerrainCellScope(int x, int z, unsigned piece) { SetGpuTerrainCell(x, z, piece); }
	GpuTerrainCellScope(const GpuTerrainCellScope &) = delete;
	GpuTerrainCellScope &operator=(const GpuTerrainCellScope &) = delete;
	~GpuTerrainCellScope() { SetGpuTerrainCell(-1, -1, 0); }
};
bool QueueGpuTerrainTile(const devilution::Surface &out, devilution::MaskType mask, const uint8_t *table);
bool SetGpuTerrainNativeCapture(bool value);
bool GpuTerrainNativeCaptureActive();
class GpuTerrainNativeCaptureScope {
	bool previous;

public:
	GpuTerrainNativeCaptureScope()
	    : previous(SetGpuTerrainNativeCapture(true))
	{
	}
	~GpuTerrainNativeCaptureScope() { SetGpuTerrainNativeCapture(previous); }
};
void CaptureGpuTerrainOpaque(int x, int y, const uint8_t *pixels, unsigned length);
void CaptureGpuTerrainBlend(int x, int y, const uint8_t *indices, unsigned length);
SDL_Color GpuTerrainBackground(int x, int y);
void RenderGpuTerrain(SDL_GPUCommandBuffer *cmd, SDL_GPUTexture *target, SDL_Surface *ui, SDL_Surface *classic, int width, int height, int pixelWidth, int pixelHeight);
uint16_t EnterGpuTerrainTile(const uint8_t *source, int x, int bottom, devilution::TileType type, int height, const devilution::Lightmap &lightmap, const uint8_t *table);
void LeaveGpuTerrainTile(uint16_t previous);
class GpuTerrainTileScope {
	uint16_t previous;

public:
	GpuTerrainTileScope(const uint8_t *source, int x, int bottom, devilution::TileType type, int height, const devilution::Lightmap &lightmap, const uint8_t *table)
	    : previous(EnterGpuTerrainTile(source, x, bottom, type, height, lightmap, table))
	{
	}
	GpuTerrainTileScope(const GpuTerrainTileScope &) = delete;
	GpuTerrainTileScope &operator=(const GpuTerrainTileScope &) = delete;
	~GpuTerrainTileScope() { LeaveGpuTerrainTile(previous); }
};
} // namespace reincarnated
#endif
