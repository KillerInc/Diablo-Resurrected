#include "gpu_terrain.hpp"
#ifdef USE_SDL3
#include "controls/control_mode.hpp"
#include "engine/light_tables.hpp"
#include "engine/load_file.hpp"
#include "engine/render/dun_render.hpp"
#include "gpu_sprites.hpp"
#include "hd_renderer.hpp"
#include "levels/gendung.h"
#include "levels/reencode_dun_cels.hpp"
#include "options.h"
#include "utils/display.h"
#include "utils/log.hpp"
#include <algorithm>
#include <array>
#include <bit>
#include <cstring>
#include <map>
#include <sstream>
#include <tuple>
#include <unordered_map>
#include <vector>
#ifdef _WIN32
#include "shaders/sprite_comp.hpp"
#include "shaders/sprite_vert.hpp"
#include "shaders/terrain_frag.hpp"
#endif
namespace reincarnated {
namespace {
SDL_GPUDevice *device = nullptr;
SDL_GPUGraphicsPipeline *pipeline = nullptr;
SDL_GPUComputePipeline *nearestPipeline = nullptr;
SDL_GPUSampler *sampler = nullptr;
SDL_GPUTexture *ownerTexture = nullptr, *indexTexture = nullptr, *headTexture = nullptr, *paletteTexture = nullptr, *uiTexture = nullptr, *classicTexture = nullptr;
SDL_GPUBuffer *nearest = nullptr, *commandBuffer = nullptr, *nodeBuffer = nullptr;
SDL_GPUBuffer *spanBuffer = nullptr, *linkBuffer = nullptr, *byteBuffer = nullptr;
unsigned spanCapacity = 0, linkCapacity = 0, byteCapacity = 0, headWidth = 0;
SDL_GPUTransferBuffer *staging = nullptr;
unsigned stagingCapacity = 0, commandCapacity = 0, nodeCapacity = 0, textureW = 0, textureH = 0, uiW = 0, uiH = 0;
struct Source {
	unsigned frame;
	int offset;
};
std::unordered_map<const uint8_t *, Source> sources;
std::shared_ptr<GpuSheet> material;
std::string materialPath, palettePath;
std::array<SDL_Color, 256> originalPalette {};
std::vector<uint16_t> ownerPixels;
std::vector<uint32_t> indexPixels;
struct TileRun {
	uint8_t x, length;
};
struct DecodedTile {
	std::vector<uint8_t> indices, mask;
	std::vector<std::vector<TileRun>> rows;
};
struct Context {
	const DecodedTile *tile;
	const devilution::Lightmap *lightmap;
	int x, top, height, level;
	bool directSupported;
};
std::vector<Context> contexts;
std::map<std::tuple<const uint8_t *, int, int>, DecodedTile> originals;
bool decoding = false, nativeCapture = false, directTiles = false, indexedPresent = false, gpuSpans = false;
bool SetGpuTerrainNativeCaptureInternal(bool value)
{
	const bool old = nativeCapture;
	nativeCapture = value;
	return old;
}
std::vector<uint32_t> headPixels;
// One record per opaque native row run, not per covered pixel. Bin links are
// newest-first and preserve the original traversal order without atomics.
struct RasterSpan {
	uint32_t x, length, owner, flags, indices, original, lights, level;
};
struct SpanLink {
	uint32_t previous, span;
};
static_assert(sizeof(RasterSpan) == 32 && sizeof(SpanLink) == 8);
std::vector<RasterSpan> rasterSpans;
std::vector<SpanLink> spanLinks;
std::vector<uint8_t> spanBytes;

// Three uint4 records, read with ByteAddressBuffer.Load4. SDL D3D12
// storage SRVs are raw buffers, not StructuredBuffer descriptors.
struct Command {
	uint32_t x, y, px, py, cx, cy, w, h, page, density, pw, ph;
};
struct Node {
	uint32_t previous, owner, index, unused;
};
static_assert(sizeof(Command) == 48 && sizeof(Node) == 16);
std::vector<Command> commands;
std::vector<Node> nodes;
std::vector<uint32_t> maskColors;
int nativeW = 0, nativeH = 0, zoom = 1, offsetX = 0;
SDL_Rect clip {};
uint16_t current = 0;
uint32_t directTileCount = 0;
bool active = false, ready = false, warmed = false, nativeOnly = false;
unsigned SpanColumns() { return (nativeW + 31) / 32; }
uint32_t AppendSpanBytes(const uint8_t *data, unsigned length)
{
	if (!data) return 0;
	const uint32_t offset = uint32_t(spanBytes.size());
	spanBytes.resize((offset + length + 3) & ~3U);
	std::memcpy(spanBytes.data() + offset, data, length);
	return offset;
}
void AppendRasterSpan(int x, int y, unsigned length, uint16_t owner, bool blend,
    bool derive, const uint8_t *indices, const uint8_t *original, const uint8_t *lights, unsigned level)
{
	if (!length) return;
	const uint32_t index = uint32_t(rasterSpans.size());
	rasterSpans.push_back({ uint32_t(x), length, owner, uint32_t(blend) | (uint32_t(derive) << 1),
	    AppendSpanBytes(indices, length), AppendSpanBytes(original, length), AppendSpanBytes(lights, length),
	    lights ? 256U : level });
	const unsigned columns = SpanColumns();
	for (unsigned bin = unsigned(x) / 32; bin <= (unsigned(x) + length - 1) / 32; ++bin) {
		auto &head = headPixels[size_t(y) * columns + bin];
		spanLinks.push_back({ head, index });
		head = uint32_t(spanLinks.size() - 1);
	}
}

bool Requested()
{
	const char *value = SDL_getenv("D1R_GPU_TERRAIN");
	return !value || std::strcmp(value, "0") != 0;
}
SDL_GPUTexture *Texture(unsigned w, unsigned h, SDL_GPUTextureFormat format)
{
	SDL_GPUTextureCreateInfo info {};
	info.type = SDL_GPU_TEXTURETYPE_2D;
	info.format = format;
	info.usage = SDL_GPU_TEXTUREUSAGE_SAMPLER;
	info.width = w;
	info.height = h;
	info.layer_count_or_depth = info.num_levels = 1;
	return SDL_CreateGPUTexture(device, &info);
}
void *Map(unsigned size)
{
	if (!staging || stagingCapacity < size) {
		if (staging) SDL_ReleaseGPUTransferBuffer(device, staging);
		SDL_GPUTransferBufferCreateInfo info {};
		info.usage = SDL_GPU_TRANSFERBUFFERUSAGE_UPLOAD;
		info.size = std::bit_ceil(std::max(65536U, size));
		staging = SDL_CreateGPUTransferBuffer(device, &info);
		stagingCapacity = info.size;
	}
	if (!staging) devilution::ErrSdl();
	auto *mapped = SDL_MapGPUTransferBuffer(device, staging, true);
	if (!mapped) devilution::ErrSdl();
	return mapped;
}
void UploadTexture(SDL_GPUCommandBuffer *cmd, SDL_GPUTexture *texture, const void *data, unsigned w, unsigned h, unsigned bytes, unsigned sourcePitch = 0)
{
	const unsigned pitch = (w * bytes + 255) & ~255U;
	auto *mapped = static_cast<uint8_t *>(Map(pitch * h));
	if (!sourcePitch) sourcePitch = w * bytes;
	for (unsigned y = 0; y < h; ++y)
		std::memcpy(mapped + y * pitch, static_cast<const uint8_t *>(data) + y * sourcePitch, w * bytes);
	SDL_UnmapGPUTransferBuffer(device, staging);
	auto *pass = SDL_BeginGPUCopyPass(cmd);
	SDL_GPUTextureTransferInfo src {};
	src.transfer_buffer = staging;
	src.pixels_per_row = pitch / bytes;
	src.rows_per_layer = h;
	SDL_GPUTextureRegion dst {};
	dst.texture = texture;
	dst.w = w;
	dst.h = h;
	dst.d = 1;
	SDL_UploadToGPUTexture(pass, &src, &dst, true);
	SDL_EndGPUCopyPass(pass);
}
void EnsureBuffer(SDL_GPUBuffer *&buffer, unsigned &capacity, unsigned size)
{
	size = std::max(16U, size);
	if (!buffer || capacity < size) {
		if (buffer) SDL_ReleaseGPUBuffer(device, buffer);
		SDL_GPUBufferCreateInfo info {};
		info.usage = SDL_GPU_BUFFERUSAGE_GRAPHICS_STORAGE_READ;
		info.size = std::bit_ceil(std::max(65536U, size));
		buffer = SDL_CreateGPUBuffer(device, &info);
		capacity = info.size;
	}
	if (!buffer) devilution::ErrSdl();
}
bool Warm()
{
	if (warmed) return bool(material);
	warmed = true;
	if (!pipeline || materialPath.empty()) return false;
	AssetBytes bytes, layout;
	if (!GetHdAssetStore().readGpuWithLayout(materialPath, bytes, layout)) return false;
	std::istringstream in(std::string(bytes.begin(), bytes.end()));
	std::string magic;
	unsigned density, cols, rows, w, h, count;
	if (!(in >> magic >> density >> cols >> rows >> w >> h >> count) || w != 32 || h != 32 || count > 8) {
		devilution::Log("GPU_TERRAIN_FALLBACK source={} unsupported tile metadata; native background retained", materialPath);
		return false;
	}
	material = LoadGpuSheet({ materialPath, cols, rows, w });
	if (!material) return false;
	std::array<uint8_t, 768> raw {};
	if (!devilution::LoadOptionalFileInMem(palettePath.c_str(), raw.data(), raw.size())) {
		material.reset();
		return false;
	}
	for (unsigned i = 0; i < 256; ++i)
		originalPalette[i] = { raw[i * 3], raw[i * 3 + 1], raw[i * 3 + 2], 255 };
	if (nearest) SDL_ReleaseGPUBuffer(device, nearest);
	SDL_GPUBufferCreateInfo info {};
	info.usage = SDL_GPU_BUFFERUSAGE_COMPUTE_STORAGE_WRITE | SDL_GPU_BUFFERUSAGE_GRAPHICS_STORAGE_READ;
	info.size = 67108864;
	nearest = SDL_CreateGPUBuffer(device, &info);
	auto *pal = Texture(256, 1, SDL_GPU_TEXTUREFORMAT_R8G8B8A8_UNORM);
	if (!nearest || !pal) devilution::ErrSdl();
	auto *cmd = SDL_AcquireGPUCommandBuffer(device);
	if (!cmd) devilution::ErrSdl();
	UploadTexture(cmd, pal, originalPalette.data(), 256, 1, 4);
	SDL_GPUStorageBufferReadWriteBinding output {};
	output.buffer = nearest;
	auto *pass = SDL_BeginGPUComputePass(cmd, nullptr, 0, &output, 1);
	SDL_BindGPUComputePipeline(pass, nearestPipeline);
	SDL_GPUTextureSamplerBinding input { pal, sampler };
	SDL_BindGPUComputeSamplers(pass, 0, &input, 1);
	SDL_DispatchGPUCompute(pass, 256, 256, 1);
	SDL_EndGPUComputePass(pass);
	auto *fence = SDL_SubmitGPUCommandBufferAndAcquireFence(cmd);
	if (!fence || !SDL_WaitForGPUFences(device, true, &fence, 1)) devilution::ErrSdl();
	SDL_ReleaseGPUFence(device, fence);
	SDL_ReleaseGPUTexture(device, pal);
	devilution::Log("GPU_TERRAIN_READY source={} pages={} cpu_world_paint=0", materialPath, material->pages.size());
	return true;
}
void MaskOpaque(int x, int y, unsigned length)
{
	const int left = std::max(x * zoom + offsetX, clip.x), right = std::min((x + int(length)) * zoom + offsetX, clip.x + clip.w);
	if (left >= right) return;
	for (int py = y * zoom; py < std::min((y + 1) * zoom, clip.h); ++py)
		MaskGpuSpriteOpaqueSpan(left, py, right - left);
}
} // namespace
void InitializeGpuTerrain(SDL_GPUDevice *target)
{
	device = target;
	if (!Requested()) return;
#ifdef _WIN32
	if (std::strcmp(SDL_GetGPUDeviceDriver(device), "direct3d12") != 0) return;
	SDL_GPUShaderCreateInfo sh {};
	sh.entrypoint = "main";
	sh.format = SDL_GPU_SHADERFORMAT_DXBC;
	sh.stage = SDL_GPU_SHADERSTAGE_VERTEX;
	sh.code = SpriteVert;
	sh.code_size = sizeof(SpriteVert);
	sh.num_uniform_buffers = 1;
	auto *vert = SDL_CreateGPUShader(device, &sh);
	sh.stage = SDL_GPU_SHADERSTAGE_FRAGMENT;
	sh.code = TerrainFrag;
	sh.code_size = sizeof(TerrainFrag);
	sh.num_samplers = 14;
	sh.num_storage_buffers = 6;
	auto *frag = SDL_CreateGPUShader(device, &sh);
	if (vert && frag) {
		SDL_GPUColorTargetDescription color {};
		color.format = SDL_GPU_TEXTUREFORMAT_R8G8B8A8_UNORM;
		SDL_GPUGraphicsPipelineCreateInfo p {};
		p.vertex_shader = vert;
		p.fragment_shader = frag;
		p.primitive_type = SDL_GPU_PRIMITIVETYPE_TRIANGLELIST;
		p.target_info.color_target_descriptions = &color;
		p.target_info.num_color_targets = 1;
		pipeline = SDL_CreateGPUGraphicsPipeline(device, &p);
	}
	if (vert) SDL_ReleaseGPUShader(device, vert);
	if (frag) SDL_ReleaseGPUShader(device, frag);
	SDL_GPUComputePipelineCreateInfo c {};
	c.code = SpriteComp;
	c.code_size = sizeof(SpriteComp);
	c.entrypoint = "main";
	c.format = SDL_GPU_SHADERFORMAT_DXBC;
	c.num_samplers = 1;
	c.num_readwrite_storage_buffers = 1;
	c.threadcount_x = 256;
	c.threadcount_y = c.threadcount_z = 1;
	nearestPipeline = SDL_CreateGPUComputePipeline(device, &c);
	SDL_GPUSamplerCreateInfo s {};
	s.min_filter = s.mag_filter = SDL_GPU_FILTER_NEAREST;
	s.mipmap_mode = SDL_GPU_SAMPLERMIPMAPMODE_NEAREST;
	s.address_mode_u = s.address_mode_v = s.address_mode_w = SDL_GPU_SAMPLERADDRESSMODE_CLAMP_TO_EDGE;
	sampler = SDL_CreateGPUSampler(device, &s);
#endif
}
void ReleaseGpuTerrainLevel()
{
	material.reset();
	sources.clear();
	originals.clear();
	materialPath.clear();
	warmed = false;
	ResetGpuTerrainFrame();
}
void DestroyGpuTerrain()
{
	ReleaseGpuTerrainLevel();
	for (auto *texture : { ownerTexture, indexTexture, headTexture, paletteTexture, uiTexture, classicTexture })
		if (texture) SDL_ReleaseGPUTexture(device, texture);
	for (auto *buffer : { nearest, commandBuffer, nodeBuffer, spanBuffer, linkBuffer, byteBuffer })
		if (buffer) SDL_ReleaseGPUBuffer(device, buffer);
	if (staging) SDL_ReleaseGPUTransferBuffer(device, staging);
	if (pipeline) SDL_ReleaseGPUGraphicsPipeline(device, pipeline);
	if (nearestPipeline) SDL_ReleaseGPUComputePipeline(device, nearestPipeline);
	if (sampler) SDL_ReleaseGPUSampler(device, sampler);
	ownerTexture = indexTexture = headTexture = paletteTexture = uiTexture = classicTexture = nullptr;
	nearest = commandBuffer = nodeBuffer = spanBuffer = linkBuffer = byteBuffer = nullptr;
	staging = nullptr;
	pipeline = nullptr;
	nearestPipeline = nullptr;
	sampler = nullptr;
	stagingCapacity = commandCapacity = nodeCapacity = spanCapacity = linkCapacity = byteCapacity = headWidth = textureW = textureH = uiW = uiH = 0;
	warmed = false;
	device = nullptr;
}
void RegisterGpuTerrain(const std::byte *cells, std::span<const std::pair<uint16_t, devilution::DunFrameInfo>> frames)
{
	using namespace devilution;
	sources.clear();
	originals.clear();
	material.reset();
	warmed = false;
	materialPath.clear();
	ResetGpuTerrainFrame();
	const char *stem = nullptr;
	switch (leveltype) {
	case DTYPE_TOWN: stem = "towndata/town"; break;
	case DTYPE_CATHEDRAL: stem = "l1data/l1"; break;
	case DTYPE_CATACOMBS: stem = "l2data/l2"; break;
	case DTYPE_CAVES: stem = "l3data/l3"; break;
	case DTYPE_HELL: stem = "l4data/l4"; break;
	default: return;
	}
	materialPath = std::string("hd/levels/") + stem + ".png";
	palettePath = std::string("levels/") + stem + (leveltype == DTYPE_HELL ? "_1.pal" : ".pal");
	for (size_t i = 0; i < frames.size(); ++i) {
		const auto *source = GetDunFrame(cells, uint32_t(i + 1));
		const auto &[original, info] = frames[i];
		sources.emplace(source, Source { unsigned(original - 1), 0 });
		if (info.type == TileType::TransparentSquare && info.isFloor()) sources.emplace(source + ReencodedTriangleFrameSize, Source { unsigned(original - 1), 16 });
	}
}
void WarmGpuTerrain()
{
	if (Requested()) Warm();
}
bool BeginGpuTerrainFrame(int scale, int offset, int clipX, int clipWidth, int clipHeight)
{
	ResetGpuTerrainFrame();
	if (devilution::ControlMode == devilution::ControlTypes::VirtualGamepad || scale < 1 || scale > 2 || clipWidth <= 0 || clipHeight <= 0 || !Requested() || !GetRendererSwitch().usesHdRenderer() || !Warm()) return false;
	nativeOnly = SDL_getenv("D1R_GPU_TERRAIN_NATIVE") != nullptr;
	const char *direct = SDL_getenv("D1R_GPU_TILE_COMMANDS");
	directTiles = !direct || std::strcmp(direct, "0") != 0;
	const char *indexed = SDL_getenv("D1R_GPU_INDEXED_PRESENT");
	indexedPresent = !indexed || std::strcmp(indexed, "0") != 0;
	const char *spans = SDL_getenv("D1R_GPU_TERRAIN_SPANS");
	gpuSpans = !spans || std::strcmp(spans, "0") != 0;
	directTileCount = 0;
	static int previousPath = -1;
	const int path = int(directTiles) + int(indexedPresent) * 2 + int(gpuSpans) * 4;
	if (path != previousPath) {
		previousPath = path;
		devilution::Log("GPU_TERRAIN_PATH direct_tiles={} indexed_present={} gpu_spans={}", directTiles, indexedPresent, gpuSpans);
	}

	zoom = scale;
	offsetX = offset;
	clip = { clipX, 0, clipWidth, clipHeight };
	nativeW = (devilution::gnScreenWidth + zoom - 1) / zoom;
	nativeH = (clipHeight + zoom - 1) / zoom;
	const size_t size = size_t(nativeW) * nativeH;
	if (!gpuSpans) {
		ownerPixels.assign(size, 0);
		indexPixels.assign(size, 0);
	}
	headPixels.assign(gpuSpans ? size_t(SpanColumns()) * nativeH : size, 0);
	spanBytes.assign(4, 0);
	spanLinks.push_back({ 0, 0 });
	nodes.push_back({ 0, 0, 0, 0 });
	active = true;
	return true;
}
void EndGpuTerrainFrame() { ready = active; }
void ResetGpuTerrainFrame()
{
	active = ready = false;
	current = 0;
	commands.clear();
	contexts.clear();
	rasterSpans.clear();
	spanLinks.clear();
	spanBytes.clear();
	nodes.clear();
}
bool GpuTerrainActive() { return active; }
bool GpuTerrainReady() { return ready && active; }
bool GpuTerrainUsesIndexedPresent() { return GpuTerrainReady() && indexedPresent; }
bool GpuTerrainNeedsCpuCanvas() { return !active || !indexedPresent; }
bool GpuTerrainSkipsNativePainting() { return active && directTiles && !nativeCapture; }
uint16_t EnterGpuTerrainTile(const uint8_t *source, int x, int bottom, devilution::TileType type, int height, const devilution::Lightmap &lightmap, const uint8_t *table)
{
	const auto previous = current;
	current = 0;
	if (!active || decoding || nativeOnly) return previous;
	const auto found = sources.find(source);
	if (found == sources.end()) return previous;
	const auto &info = found->second;
	if (info.frame >= material->frames.size() || commands.size() >= 65535) return previous;
	const auto &frame = material->frames[info.frame];
	const auto &page = material->pages[frame.page];
	commands.push_back({ uint32_t(x), uint32_t(bottom + info.offset - 31), frame.x, frame.y, frame.cropX, frame.cropY, frame.w, frame.h, frame.page, material->density, page.width, page.height });
	const auto key = std::make_tuple(source, int(type), height);
	auto [it, inserted] = originals.try_emplace(key);
	if (inserted) {
		// Cache native indices, not RGBA. Use the engine decoder, including its
		// split-floor shapes, so palette aliases and lighting stay exact.
		auto *surface = SDL_CreateSurface(32, height, SDL_PIXELFORMAT_INDEX8);
		if (!surface) devilution::ErrSdl();
		std::array<std::array<uint8_t, devilution::LightTableSize>, devilution::NumLightingLevels> tables {};
		for (auto &row : tables)
			for (unsigned i = 0; i < 256; ++i)
				row[i] = uint8_t(i);
		std::vector<uint8_t> lights(size_t(surface->pitch) * height, 0);
		devilution::Lightmap unlit(static_cast<const uint8_t *>(surface->pixels), lights, surface->pitch, tables, tables[0].data(), tables.back().data());
		it->second.indices.resize(32 * height);
		it->second.mask.resize(32 * height);
		decoding = true;
		for (unsigned pass = 0; pass < 2; ++pass) {
			SDL_FillSurfaceRect(surface, nullptr, pass ? 252 : 251);
			devilution::RenderTileFrame(devilution::Surface(surface), unlit, { 0, height - 1 }, type, source, height, devilution::MaskType::Solid, tables[0].data());
			for (int row = 0; row < height; ++row) {
				const auto *src = static_cast<const uint8_t *>(surface->pixels) + row * surface->pitch;
				for (unsigned x = 0; x < 32; ++x) {
					const size_t i = row * 32 + x;
					if (pass == 0)
						it->second.indices[i] = src[x];
					else
						it->second.mask[i] = it->second.indices[i] == src[x];
				}
			}
		}
		decoding = false;
		it->second.rows.resize(height);
		for (int row = 0; row < height; ++row) {
			int x = 0;
			while (x < 32) {
				if (!it->second.mask[row * 32 + x]) {
					++x;
					continue;
				}
				const int left = x;
				while (x < 32 && it->second.mask[row * 32 + x])
					++x;
				it->second.rows[row].push_back({ uint8_t(left), uint8_t(x - left) });
			}
		}

		SDL_DestroySurface(surface);
	}
	int level = 0;
	bool supported = *devilution::GetOptions().Graphics.perPixelLighting || lightmap.isFullyDarkLightTable(table) || lightmap.isFullyLitLightTable(table);
	if (!*devilution::GetOptions().Graphics.perPixelLighting) {
		if (lightmap.isFullyDarkLightTable(table))
			level = 15;
		else if (!lightmap.isFullyLitLightTable(table))
			for (int i = 0; i < 16; ++i)
				if (table == devilution::LightTables[i].data()) {
					supported = true;
					level = i;
					break;
				}
	} else
		level = -1;
	contexts.push_back({ &it->second, &lightmap, x, bottom - height + 1, height, level, supported && lightmap.getLightTable(0) == devilution::LightTables[0].data() });
	current = uint16_t(commands.size());
	return previous;
}
void LeaveGpuTerrainTile(uint16_t previous) { current = previous; }
struct IndexSpan {
	const uint8_t *original = nullptr, *light = nullptr;
	unsigned level = 0;
	uint32_t pack(unsigned i, uint8_t lit) const { return original ? lit | (uint32_t(original[i]) << 8) | (uint32_t(light ? std::min<unsigned>(15, light[i]) : level) << 16) : lit; }
};
IndexSpan GetIndexSpan(int x, int y)
{
	if (!current) return {};
	const auto &context = contexts[current - 1];
	const int localX = x - context.x, localY = y - context.top;
	if (localX < 0 || localX >= 32 || localY < 0 || localY >= context.height) return {};
	IndexSpan result;
	result.original = context.tile->indices.data() + localY * 32 + localX;
	if (context.level < 0) {
		const auto *pixel = static_cast<const uint8_t *>(devilution::PalSurface->pixels) + y * devilution::PalSurface->pitch + x;
		result.light = context.lightmap->getLightingAt(pixel);
	} else
		result.level = context.level;
	return result;
}
void CaptureGpuTerrainOpaque(int x, int y, const uint8_t *pixels, unsigned length)
{
	if (!active || x < 0 || x >= nativeW || y < 0 || y >= nativeH) return;
	length = std::min<unsigned>(length, nativeW - x);
	const size_t at = size_t(y) * nativeW + x;
	const auto span = GetIndexSpan(x, y);
	if (gpuSpans) {
		AppendRasterSpan(x, y, length, current, false, false, pixels, span.original, span.light, span.level);
		MaskOpaque(x, y, length);
		return;
	}
	for (unsigned i = 0; i < length; ++i)
		indexPixels[at + i] = span.pack(i, pixels[i]);
	std::fill_n(ownerPixels.data() + at, length, current);
	std::fill_n(headPixels.data() + at, length, 0);
	MaskOpaque(x, y, length);
}
void CaptureGpuTerrainBlend(int x, int y, const uint8_t *indices, unsigned length)
{
	if (!active || x < 0 || x >= nativeW || y < 0 || y >= nativeH) return;
	length = std::min<unsigned>(length, nativeW - x);
	const size_t at = size_t(y) * nativeW + x;
	const auto span = GetIndexSpan(x, y);
	const bool masks = HasQueuedGpuSprites();
	if (masks) maskColors.resize(length * zoom);
	if (gpuSpans) AppendRasterSpan(x, y, length, current, true, false, indices, span.original, span.light, span.level);
	for (unsigned i = 0; i < (gpuSpans && !masks ? 0 : length); ++i) {
		if (!gpuSpans) {
			nodes.push_back({ headPixels[at + i], current, span.pack(i, indices[i]), 0 });
			headPixels[at + i] = uint32_t(nodes.size() - 1);
		}
		if (!masks) continue;
		auto color = devilution::Palette->colors[indices[i]];
		color.a = 255;
		uint32_t packed;
		std::memcpy(&packed, &color, 4);
		for (int dx = 0; dx < zoom; ++dx)
			maskColors[i * zoom + dx] = packed;
	}
	const int rawLeft = x * zoom + offsetX, left = std::max(rawLeft, clip.x), right = std::min(rawLeft + int(length) * zoom, clip.x + clip.w);
	if (masks && left < right)
		for (int py = y * zoom; py < std::min((y + 1) * zoom, clip.h); ++py)
			MaskGpuSpriteBlendedSpan(left, py, maskColors.data() + left - rawLeft, right - left);
}
bool GpuTerrainNativeCaptureActive() { return nativeCapture; }
bool SetGpuTerrainNativeCapture(bool value) { return SetGpuTerrainNativeCaptureInternal(value); }
bool QueueGpuTerrainTile(const devilution::Surface &out, devilution::MaskType mask, const uint8_t *table)
{
	if (!active || !directTiles || nativeCapture || decoding || !current || out.surface != devilution::PalSurface) return false;
	const auto &context = contexts[current - 1];
	if (!context.directSupported) return false;
	const int y0 = std::max({ context.top, out.region.y, 0 }), y1 = std::min({ context.top + context.height, out.region.y + out.region.h, nativeH });
	const int x0 = std::max({ context.x, out.region.x, 0 }), x1 = std::min({ context.x + 32, out.region.x + out.region.w, nativeW });
	const bool masks = HasQueuedGpuSprites();
	for (int y = y0; y < y1; ++y) {
		const int row = y - context.top, fromBottom = context.height - 1 - row;
		const int prefix = mask == devilution::MaskType::Left ? -32 + fromBottom * 2 : 64 - fromBottom * 2;
		const auto transparent = [&](int x) { return mask == devilution::MaskType::Transparent || (mask == devilution::MaskType::Left && x - context.x < prefix) || (mask == devilution::MaskType::Right && x - context.x >= prefix); };
		for (const auto run : context.tile->rows[row]) {
			int x = std::max(x0, context.x + int(run.x));
			const int end = std::min(x1, context.x + int(run.x) + int(run.length));
			while (x < end) {
				const int left = x;
				const bool blend = transparent(x);
				x = end;
				const int split = context.x + prefix;
				if ((mask == devilution::MaskType::Left || mask == devilution::MaskType::Right) && split > left && split < end) x = split;
				const unsigned length = x - left;
				const size_t at = size_t(y) * nativeW + left;
				const auto span = GetIndexSpan(left, y);
				if (gpuSpans) AppendRasterSpan(left, y, length, current, blend, true, nullptr, span.original, span.light, span.level);
				if (blend) {
					if (masks) maskColors.resize(length * zoom);
					for (unsigned i = 0; i < (gpuSpans && !masks ? 0 : length); ++i) {
						if (!gpuSpans) {
							const uint32_t packed = span.pack(i, 0) | 0x01000000U;
							nodes.push_back({ headPixels[at + i], current, packed, 0 });
							headPixels[at + i] = uint32_t(nodes.size() - 1);
						}
						if (masks) {
							const unsigned light = span.light ? std::min<unsigned>(15, span.light[i]) : span.level;
							const uint8_t index = span.light ? context.lightmap->adjustColor(span.original[i], light) : table[span.original[i]];
							auto color = devilution::Palette->colors[index];
							color.a = 255;
							uint32_t rgb;
							std::memcpy(&rgb, &color, 4);
							for (int dx = 0; dx < zoom; ++dx)
								maskColors[i * zoom + dx] = rgb;
						}
					}
					const int rawLeft = left * zoom + offsetX, l = std::max(rawLeft, clip.x), r = std::min(rawLeft + int(length) * zoom, clip.x + clip.w);
					if (masks && l < r)
						for (int py = y * zoom; py < std::min((y + 1) * zoom, clip.h); ++py)
							MaskGpuSpriteBlendedSpan(l, py, maskColors.data() + l - rawLeft, r - l);
				} else {
					if (!gpuSpans) {
						for (unsigned i = 0; i < length; ++i)
							indexPixels[at + i] = span.pack(i, 0) | 0x01000000U;
						std::fill_n(ownerPixels.data() + at, length, current);
						std::fill_n(headPixels.data() + at, length, 0);
					}
					MaskOpaque(left, y, length);
				}
			}
		}
	}
	++directTileCount;
	return true;
}
SDL_Color NativePackedColor(uint32_t packed)
{
	const unsigned index = (packed >> 24) ? devilution::LightTables[(packed >> 16) & 15][(packed >> 8) & 255] : packed & 255;
	return devilution::Palette->colors[index];
}
SDL_Color GpuTerrainBackground(int x, int y)
{
	x = (x - offsetX) / zoom;
	y /= zoom;
	if (x < 0 || y < 0 || x >= nativeW || y >= nativeH) return { 0, 0, 0, 255 };
	if (gpuSpans) {
		std::vector<std::pair<uint32_t, bool>> colors;
		for (auto link = headPixels[size_t(y) * SpanColumns() + x / 32]; link; link = spanLinks[link].previous) {
			const auto &span = rasterSpans[spanLinks[link].span];
			if (unsigned(x) < span.x || unsigned(x) >= span.x + span.length) continue;
			const unsigned i = unsigned(x) - span.x;
			const unsigned level = span.level == 256 ? std::min<unsigned>(15, spanBytes[span.lights + i]) : span.level;
			const uint32_t packed = (span.flags & 2 ? 0x01000000U : spanBytes[span.indices + i])
			    | (uint32_t(span.original ? spanBytes[span.original + i] : 0) << 8) | (level << 16);
			colors.push_back({ packed, (span.flags & 1) != 0 });
			if (!(span.flags & 1)) break;
		}
		SDL_Color result = NativePackedColor(0);
		for (auto it = colors.rbegin(); it != colors.rend(); ++it) {
			const auto c = NativePackedColor(it->first);
			if (!it->second)
				result = c;
			else {
				result.r = (unsigned(result.r) + c.r) / 2;
				result.g = (unsigned(result.g) + c.g) / 2;
				result.b = (unsigned(result.b) + c.b) / 2;
			}
		}
		return result;
	}
	const size_t at = size_t(y) * nativeW + x;
	SDL_Color result = NativePackedColor(indexPixels[at]);
	std::vector<uint32_t> chain;
	for (auto node = headPixels[at]; node; node = nodes[node].previous)
		chain.push_back(node);
	for (auto it = chain.rbegin(); it != chain.rend(); ++it) {
		const auto c = NativePackedColor(nodes[*it].index);
		result.r = (unsigned(result.r) + c.r) / 2;
		result.g = (unsigned(result.g) + c.g) / 2;
		result.b = (unsigned(result.b) + c.b) / 2;
	}
	result.a = 255;
	return result;
}
void RenderGpuTerrain(SDL_GPUCommandBuffer *cmd, SDL_GPUTexture *target, SDL_Surface *ui, SDL_Surface *classic, int width, int height, int pixelWidth, int pixelHeight)
{
	if (!GpuTerrainReady()) return;
	if (textureW != unsigned(nativeW) || textureH != unsigned(nativeH) || headWidth != (gpuSpans ? SpanColumns() : unsigned(nativeW))) {
		for (auto *t : { ownerTexture, indexTexture, headTexture })
			if (t) SDL_ReleaseGPUTexture(device, t);
		textureW = nativeW;
		textureH = nativeH;
		ownerTexture = Texture(nativeW, nativeH, SDL_GPU_TEXTUREFORMAT_R16_UINT);
		indexTexture = Texture(nativeW, nativeH, SDL_GPU_TEXTUREFORMAT_R8G8B8A8_UNORM);
		headWidth = gpuSpans ? SpanColumns() : unsigned(nativeW);
		headTexture = Texture(headWidth, nativeH, SDL_GPU_TEXTUREFORMAT_R32_UINT);
	}
	if (uiW != unsigned(width) || uiH != unsigned(height)) {
		if (uiTexture) SDL_ReleaseGPUTexture(device, uiTexture);
		if (classicTexture) SDL_ReleaseGPUTexture(device, classicTexture);
		classicTexture = nullptr;
		uiW = width;
		uiH = height;
		uiTexture = Texture(width, height, SDL_GPU_TEXTUREFORMAT_R8G8B8A8_UNORM);
	}
	if (indexedPresent && !classicTexture) classicTexture = Texture(width, height, SDL_GPU_TEXTUREFORMAT_R8_UNORM);
	if (!paletteTexture) paletteTexture = Texture(256, 18, SDL_GPU_TEXTUREFORMAT_R8G8B8A8_UNORM);
	if (!ownerTexture || !indexTexture || !headTexture || !uiTexture || !paletteTexture || (indexedPresent && !classicTexture)) devilution::ErrSdl();
	std::array<SDL_Color, 256 * 18> palettes;
	std::copy(originalPalette.begin(), originalPalette.end(), palettes.begin());
	for (unsigned level = 0; level < 16; ++level)
		for (unsigned i = 0; i < 256; ++i)
			palettes[(level + 1) * 256 + i] = devilution::Palette->colors[devilution::LightTables[level][i]];
	std::copy_n(devilution::Palette->colors, 256, palettes.begin() + 17 * 256);
	Command empty {};
	const unsigned commandBytes = unsigned(std::max<size_t>(1, commands.size()) * sizeof(Command)), nodeBytes = unsigned(nodes.size() * sizeof(Node));
	EnsureBuffer(commandBuffer, commandCapacity, commandBytes);
	EnsureBuffer(nodeBuffer, nodeCapacity, nodeBytes);
	const unsigned spanSize = unsigned(std::max<size_t>(1, rasterSpans.size()) * sizeof(RasterSpan));
	const unsigned linkSize = unsigned(std::max<size_t>(1, spanLinks.size()) * sizeof(SpanLink));
	const unsigned byteSize = unsigned(std::max<size_t>(4, spanBytes.size()));
	EnsureBuffer(spanBuffer, spanCapacity, spanSize);
	EnsureBuffer(linkBuffer, linkCapacity, linkSize);
	EnsureBuffer(byteBuffer, byteCapacity, byteSize);
	struct ImageUpload {
		SDL_GPUTexture *texture;
		const void *source;
		unsigned w, h, bytes, pitch, offset = 0;
	};
	std::vector<ImageUpload> images {
		{ headTexture, headPixels.data(), headWidth, unsigned(nativeH), 4, headWidth * 4 },
        { paletteTexture, palettes.data(), 256, 18, 4, 256 * 4 }
    };
    if(HasHdUiRaster())images.push_back({ uiTexture, ui->pixels, unsigned(width), unsigned(height), 4, unsigned(ui->pitch) });
	if (!gpuSpans) {
		images.push_back({ ownerTexture, ownerPixels.data(), unsigned(nativeW), unsigned(nativeH), 2, unsigned(nativeW) * 2 });
		images.push_back({ indexTexture, indexPixels.data(), unsigned(nativeW), unsigned(nativeH), 4, unsigned(nativeW) * 4 });
	}
	if (indexedPresent) images.push_back({ classicTexture, classic->pixels, unsigned(width), unsigned(height), 1, unsigned(classic->pitch) });
	unsigned total = 0;
	for (auto &image : images) {
		image.offset = total;
		total += ((image.w * image.bytes + 255) & ~255U) * image.h;
	}
	const unsigned commandOffset = total, nodeOffset = (commandOffset + commandBytes + 255) & ~255U;
	const unsigned spanOffset = (nodeOffset + nodeBytes + 255) & ~255U;
	const unsigned linkOffset = (spanOffset + spanSize + 255) & ~255U, byteOffset = (linkOffset + linkSize + 255) & ~255U;
	auto *mapped = static_cast<uint8_t *>(Map(byteOffset + byteSize));
	for (const auto &image : images) {
		const unsigned pitch = (image.w * image.bytes + 255) & ~255U;
		for (unsigned y = 0; y < image.h; ++y)
			std::memcpy(mapped + image.offset + y * pitch, static_cast<const uint8_t *>(image.source) + y * image.pitch, image.w * image.bytes);
	}
	std::memcpy(mapped + commandOffset, commands.empty() ? &empty : commands.data(), commandBytes);
	std::memcpy(mapped + nodeOffset, nodes.data(), nodeBytes);
	std::memset(mapped + spanOffset, 0, spanSize);
	std::memset(mapped + linkOffset, 0, linkSize);
	std::memset(mapped + byteOffset, 0, byteSize);
	if (!rasterSpans.empty()) std::memcpy(mapped + spanOffset, rasterSpans.data(), rasterSpans.size() * sizeof(RasterSpan));
	if (!spanLinks.empty()) std::memcpy(mapped + linkOffset, spanLinks.data(), spanLinks.size() * sizeof(SpanLink));
	if (!spanBytes.empty()) std::memcpy(mapped + byteOffset, spanBytes.data(), spanBytes.size());
	SDL_UnmapGPUTransferBuffer(device, staging);
	auto *copy = SDL_BeginGPUCopyPass(cmd);
	for (const auto &image : images) {
		SDL_GPUTextureTransferInfo src {};
		src.transfer_buffer = staging;
		src.offset = image.offset;
		src.pixels_per_row = ((image.w * image.bytes + 255) & ~255U) / image.bytes;
		src.rows_per_layer = image.h;
		SDL_GPUTextureRegion dst {};
		dst.texture = image.texture;
		dst.w = image.w;
		dst.h = image.h;
		dst.d = 1;
		SDL_UploadToGPUTexture(copy, &src, &dst, true);
	}
	SDL_GPUTransferBufferLocation commandSrc { staging, commandOffset }, nodeSrc { staging, nodeOffset };
	SDL_GPUBufferRegion commandDst { commandBuffer, 0, commandBytes }, nodeDst { nodeBuffer, 0, nodeBytes };
	SDL_UploadToGPUBuffer(copy, &commandSrc, &commandDst, true);
	SDL_UploadToGPUBuffer(copy, &nodeSrc, &nodeDst, true);
	SDL_GPUTransferBufferLocation spanSrc { staging, spanOffset }, linkSrc { staging, linkOffset }, byteSrc { staging, byteOffset };
	SDL_GPUBufferRegion spanDst { spanBuffer, 0, spanSize }, linkDst { linkBuffer, 0, linkSize }, byteDst { byteBuffer, 0, byteSize };
	SDL_UploadToGPUBuffer(copy, &spanSrc, &spanDst, true);
	SDL_UploadToGPUBuffer(copy, &linkSrc, &linkDst, true);
	SDL_UploadToGPUBuffer(copy, &byteSrc, &byteDst, true);
	SDL_EndGPUCopyPass(copy);
	SDL_GPUColorTargetInfo color {};
	color.texture = target;
	color.load_op = indexedPresent ? SDL_GPU_LOADOP_CLEAR : SDL_GPU_LOADOP_LOAD;
	color.store_op = SDL_GPU_STOREOP_STORE;
	auto *pass = SDL_BeginGPURenderPass(cmd, &color, 1, nullptr);
	SDL_BindGPUGraphicsPipeline(pass, pipeline);
	SDL_GPUViewport viewport { 0, 0, float(pixelWidth), float(pixelHeight), 0, 1 };
	SDL_SetGPUViewport(pass, &viewport);
	SDL_GPUTextureSamplerBinding bindings[14];
	for (unsigned i = 0; i < 8; ++i)
		bindings[i] = { material->pages[std::min(i, unsigned(material->pages.size() - 1))].texture, sampler };
	bindings[8] = { ownerTexture, sampler };
	bindings[9] = { indexTexture, sampler };
	bindings[10] = { headTexture, sampler };
	bindings[11] = { paletteTexture, sampler };
	bindings[12] = { uiTexture, sampler };
	bindings[13] = { indexedPresent ? classicTexture : indexTexture, sampler };
	SDL_BindGPUFragmentSamplers(pass, 0, bindings, 14);
	SDL_GPUBuffer *buffers[] { nearest, commandBuffer, nodeBuffer, spanBuffer, linkBuffer, byteBuffer };
	SDL_BindGPUFragmentStorageBuffers(pass, 0, buffers, 6);
	const float vertex[] { 0, 0, float(width), float(height), 0, 0, 1, 1, float(width), float(height), 0, 0 };
	const float fragment[] { float(nativeW), float(nativeH), float(zoom), float(offsetX), float(clip.x), float(clip.y), float(clip.w), float(clip.h), indexedPresent ? 1.0f : 0.0f, gpuSpans ? 1.0f : 0.0f, HasHdUiRaster() ? 1.0f : 0.0f, 0 };
	SDL_PushGPUVertexUniformData(cmd, 0, vertex, sizeof(vertex));
	SDL_PushGPUFragmentUniformData(cmd, 0, fragment, sizeof(fragment));
	SDL_DrawGPUPrimitives(pass, 6, 1, 0, 0);
	SDL_EndGPURenderPass(pass);
	static unsigned frames = 0;
	if (SDL_getenv("D1R_PROFILE_HD") && ++frames % 100 == 0) devilution::Log("GPU_TERRAIN_FRAME tiles={} blend_nodes={} cpu_tile_draws_skipped={} indexed_present={} gpu_spans={} spans={} links={} byte_data={} cpu_ui_raster={}", commands.size(), nodes.size() - 1, directTileCount, indexedPresent, gpuSpans, rasterSpans.size(), spanLinks.size() - 1, spanBytes.size(), HasHdUiRaster());
}
} // namespace reincarnated
#endif
