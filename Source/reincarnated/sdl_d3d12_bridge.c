/* Compile the pinned SDL backend with a narrow, borrowed-pointer bridge.
 * No SDL private layout is duplicated in the game or guessed at runtime. */
#include "SDL_gpu_d3d12.c"

void D1R_GetD3D12TimingPointers(SDL_GPUCommandBuffer *buffer, void **device, void **queue, void **list)
{
    D3D12CommandBuffer *cmd = (D3D12CommandBuffer *)buffer;
    *device = cmd->renderer->device;
    *queue = cmd->renderer->commandQueue;
    *list = cmd->graphicsCommandList;
}
