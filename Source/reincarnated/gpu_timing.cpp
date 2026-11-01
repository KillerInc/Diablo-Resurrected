#include "gpu_timing.hpp"
#include "cpu_clock.hpp"
#ifdef USE_SDL3
#include "hd_renderer.hpp"
#include "utils/file_util.h"
#include "utils/log.hpp"
#include <SDL3/SDL_timer.h>
#include <array>
#include <cstdio>
#include <string_view>
#if defined(_WIN32) && defined(D1R_SDL_D3D12_BRIDGE)
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <d3d12.h>
#include <windows.h>
extern "C" void D1R_GetD3D12TimingPointers(SDL_GPUCommandBuffer *, void **, void **, void **);
#endif
namespace reincarnated {
namespace {
constexpr unsigned SlotCount = 32;
struct Sample {
	SDL_GPUFence *fence = nullptr;
	uint64_t frame = 0, activeNs = 0, cpuTotalNs = 0, cyclesTotal = 0;
	bool hd = false;
};
std::array<Sample, SlotCount> samples;
FILE *file = nullptr;
uint64_t sequence = 0, activeStart = 0;
unsigned dropped = 0;
bool failed = false;
#if defined(_WIN32) && defined(D1R_SDL_D3D12_BRIDGE)
ID3D12QueryHeap *queries = nullptr;
ID3D12Resource *readback = nullptr;
uint64_t frequency = 0;
ID3D12GraphicsCommandList *Native(SDL_GPUCommandBuffer *cmd, ID3D12Device **device = nullptr, ID3D12CommandQueue **queue = nullptr)
{
	void *d, *q, *l;
	D1R_GetD3D12TimingPointers(cmd, &d, &q, &l);
	if (device) *device = static_cast<ID3D12Device *>(d);
	if (queue) *queue = static_cast<ID3D12CommandQueue *>(q);
	return static_cast<ID3D12GraphicsCommandList *>(l);
}
bool Initialize(SDL_GPUCommandBuffer *cmd)
{
	if (readback) readback->Release();
	if (queries) queries->Release();
	readback = nullptr;
	queries = nullptr;
	ID3D12Device *device;
	ID3D12CommandQueue *queue;
	Native(cmd, &device, &queue);
	D3D12_QUERY_HEAP_DESC desc {};
	desc.Type = D3D12_QUERY_HEAP_TYPE_TIMESTAMP;
	desc.Count = SlotCount * 2;
	if (FAILED(queue->GetTimestampFrequency(&frequency)) || !frequency || FAILED(device->CreateQueryHeap(&desc, IID_PPV_ARGS(&queries)))) return false;
	D3D12_HEAP_PROPERTIES heap {};
	heap.Type = D3D12_HEAP_TYPE_READBACK;
	D3D12_RESOURCE_DESC buffer {};
	buffer.Dimension = D3D12_RESOURCE_DIMENSION_BUFFER;
	buffer.Width = SlotCount * 2 * sizeof(uint64_t);
	buffer.Height = 1;
	buffer.DepthOrArraySize = 1;
	buffer.MipLevels = 1;
	buffer.SampleDesc.Count = 1;
	buffer.Layout = D3D12_TEXTURE_LAYOUT_ROW_MAJOR;
	if (FAILED(device->CreateCommittedResource(&heap, D3D12_HEAP_FLAG_NONE, &buffer, D3D12_RESOURCE_STATE_COPY_DEST, nullptr, IID_PPV_ARGS(&readback)))) {
		queries->Release();
		queries = nullptr;
		return false;
	}
	return true;
}
void Collect(SDL_GPUDevice *device)
{
	for (unsigned i = 0; i < SlotCount; ++i) {
		auto &s = samples[i];
		if (!s.fence || !SDL_QueryGPUFence(device, s.fence)) continue;
		uint64_t *values = nullptr;
		const D3D12_RANGE range { i * 2 * sizeof(uint64_t), (i * 2 + 2) * sizeof(uint64_t) };
		if (SUCCEEDED(readback->Map(0, &range, reinterpret_cast<void **>(&values)))) {
			const uint64_t start = values[i * 2], end = values[i * 2 + 1];
			if (end >= start) std::fprintf(file, "%llu,%.3f,%s,%.6f,%llu,%u,%llu,%llu\n", static_cast<unsigned long long>(s.frame), double(s.activeNs) / 1e6, s.hd ? "HD" : "Classic", double(end - start) * 1000 / frequency, static_cast<unsigned long long>(frequency), dropped, static_cast<unsigned long long>(s.cpuTotalNs), static_cast<unsigned long long>(s.cyclesTotal));
			const D3D12_RANGE written { 0, 0 };
			readback->Unmap(0, &written);
		}
		SDL_ReleaseGPUFence(device, s.fence);
		s.fence = nullptr;
	}
}
#endif
} // namespace
int BeginGpuTiming(SDL_GPUDevice *device, SDL_GPUCommandBuffer *cmd, bool active)
{
	const char *path = SDL_getenv("D1R_GPU_PROFILE_LOG");
	if (!path || failed) return -1;
#if defined(_WIN32) && defined(D1R_SDL_D3D12_BRIDGE)
	if (std::string_view(SDL_GetGPUDeviceDriver(device)) != "direct3d12") return -1;
	if (file) Collect(device);
	if (!active) {
		activeStart = 0;
		return -1;
	}
	if (!file) {
		if (!Initialize(cmd)) {
			failed = true;
			devilution::Log("GPU_TIMING unavailable: D3D12 timestamp initialization failed");
			return -1;
		}
		file = devilution::OpenFile(path, "wb");
		if (!file) {
			failed = true;
			devilution::Log("GPU_TIMING unavailable: cannot open profile output");
			return -1;
		}
		std::fputs("frame,active_ms,mode,gpu_elapsed_ms,timestamp_hz,dropped,thread_cpu_total_ns,thread_cycles_total\n", file);
		devilution::Log("GPU_TIMING hardware_timestamps=1 async_ring={} timestamp_hz={} excludes_present_wait=1", SlotCount, frequency);
	}
	if (!activeStart) activeStart = SDL_GetTicksNS();
	for (unsigned i = 0; i < SlotCount; ++i)
		if (!samples[i].fence) {
			auto &s = samples[i];
			s.frame = ++sequence;
			s.activeNs = SDL_GetTicksNS() - activeStart;
			s.hd = GetRendererSwitch().usesHdRenderer();
			const auto cpu = ReadThreadWorkClock();
			s.cpuTotalNs = cpu.ns;
			s.cyclesTotal = cpu.cycles;
			Native(cmd)->EndQuery(queries, D3D12_QUERY_TYPE_TIMESTAMP, i * 2);
			return int(i);
		}
	++dropped;
#else
	static bool reported = false;
	if (!reported) {
		devilution::Log("GPU_TIMING unavailable: native timestamp bridge not built");
		reported = true;
	}
#endif
	return -1;
}
void EndGpuTiming(SDL_GPUCommandBuffer *cmd, int slot)
{
#if defined(_WIN32) && defined(D1R_SDL_D3D12_BRIDGE)
	if (slot < 0) return;
	auto *list = Native(cmd);
	list->EndQuery(queries, D3D12_QUERY_TYPE_TIMESTAMP, slot * 2 + 1);
	list->ResolveQueryData(queries, D3D12_QUERY_TYPE_TIMESTAMP, slot * 2, 2, readback, slot * 2 * sizeof(uint64_t));
#endif
}
void SubmitGpuTiming(SDL_GPUDevice *, int slot, SDL_GPUFence *fence)
{
	if (slot >= 0) samples[slot].fence = fence;
}
void DestroyGpuTiming(SDL_GPUDevice *device)
{
#if defined(_WIN32) && defined(D1R_SDL_D3D12_BRIDGE)
	// Presenter already waited for idle during shutdown; never wait in sampling.
	if (file) Collect(device);
	if (readback) readback->Release();
	if (queries) queries->Release();
	readback = nullptr;
	queries = nullptr;
#endif
	for (auto &s : samples) {
		if (s.fence) SDL_ReleaseGPUFence(device, s.fence);
		s = {};
	}
	if (file) std::fclose(file);
	file = nullptr;
	activeStart = sequence = 0;
	dropped = 0;
	failed = false;
}
} // namespace reincarnated
#endif
