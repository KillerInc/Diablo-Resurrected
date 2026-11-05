#pragma once
#ifdef USE_SDL3
#include <SDL3/SDL_gpu.h>
namespace reincarnated {
int BeginGpuTiming(SDL_GPUDevice *device, SDL_GPUCommandBuffer *cmd, bool active);
void EndGpuTiming(SDL_GPUCommandBuffer *cmd, int slot);
void SubmitGpuTiming(SDL_GPUDevice *device, int slot, SDL_GPUFence *fence);
void DestroyGpuTiming(SDL_GPUDevice *device);
}
#endif
