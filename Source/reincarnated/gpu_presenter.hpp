#pragma once
#ifdef USE_SDL3
struct SDL_Window;
struct SDL_Surface;
namespace reincarnated {
void InitializeGpuPresenter(SDL_Window *window);
void DestroyGpuPresenter();
bool HasGpuPresenter();
void PresentGpuFrame(SDL_Surface *surface);
void GpuWindowToLogical(float &x, float &y, bool inverse = false);
}
#endif
