#include "gpu_ui.hpp"
#ifdef USE_SDL3
#include "controls/control_mode.hpp"
#include "engine/load_file.hpp"
#include "engine/palette.h"
#include "engine/surface.hpp"
#include "gpu_sprites.hpp"
#include "gpu_terrain.hpp"
#include "hd_renderer.hpp"
#include "sheet_source.hpp"
#include "utils/clx_decode.hpp"
#include "utils/display.h"
#include "utils/log.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstring>
#include <string>
#include <unordered_map>
#include <vector>
namespace reincarnated {
namespace {
bool phase = false;
std::unordered_map<std::string, std::shared_ptr<GpuSheet>> nativeCache;
std::unordered_map<std::string, std::array<SDL_Color, 256>> canonical;
struct Mapping {
	const SheetSource *source;
	unsigned group, frame;
	int x, y, w, h;
	std::string pixels;
};
std::unordered_map<SDL_Surface *, std::vector<Mapping>> mappings;
struct CachedSurface {
	const void *pixels = nullptr;
	int w = 0, h = 0;
	std::array<std::shared_ptr<GpuSheet>, 2> textures;
};
std::unordered_map<SDL_Surface *, CachedSurface> cachedSurfaces;
uint64_t nativeUploads = 0, uiDraws = 0, hdDraws = 0;
std::string RectBytes(const devilution::Surface &src, int x, int y, int w, int h)
{
	std::string result(size_t(w) * h, '\0');
	for (int row = 0; row < h; ++row)
		std::memcpy(result.data() + size_t(row) * w, src.at(x, y + row), w);
	return result;
}
const std::array<SDL_Color, 256> &Canonical(const SheetSource *source)
{
	const std::string key = source ? source->path : "native";
	auto [it, inserted] = canonical.try_emplace(key);
	if (!inserted) return it->second;
	auto &colors = it->second;
	colors = devilution::logical_palette;
	if (!source) return colors;
	std::string path = source->path.substr(3);
	path.resize(path.size() - 4);
	size_t size = 0;
	auto bytes = devilution::LoadFileInMemWithStatus<uint8_t>((path + (source->pcx ? ".pcx" : ".pal")).c_str(), &size);
	if (!bytes && !source->pcx) bytes = devilution::LoadFileInMemWithStatus<uint8_t>("levels/towndata/town.pal", &size);
	const uint8_t *data = nullptr;
	if (bytes) {
		if (source->pcx && size >= 769 && (*bytes)[size - 769] == 12)
			data = bytes->get() + size - 768;
		else if (!source->pcx && size == 768)
			data = bytes->get();
	}
	if (data)
		for (unsigned i = 0; i < 256; ++i)
			colors[i] = { data[i * 3], data[i * 3 + 1], data[i * 3 + 2], 255 };
	return colors;
}
std::shared_ptr<GpuSheet> Native(std::string key, unsigned w, unsigned h, const std::vector<uint8_t> &pixels)
{
	key.append(reinterpret_cast<const char *>(&w), sizeof(w));
	key.append(reinterpret_cast<const char *>(&h), sizeof(h));
	auto it = nativeCache.find(key);
	if (it != nativeCache.end()) return it->second;
	auto sheet = CreateGpuUiIndices(w, h, pixels.data());
	if (sheet) {
		nativeCache.emplace(std::move(key), sheet);
		++nativeUploads;
	}
	return sheet;
}
void Palette(GpuSpriteDraw &d, const SheetSource *source, const uint8_t *trn, int outline)
{
	d.palette.resize(256 * 2 * 4);
	const auto &base = Canonical(source);
	for (unsigned i = 0; i < 256; ++i) {
		std::memcpy(d.palette.data() + i * 4, &base[i], 4);
		d.uiTranslation[i] = outline >= 0 ? uint8_t(outline) : (trn ? trn[i] : uint8_t(i));
	}
}
void Queue(const devilution::Surface &out, std::shared_ptr<GpuSheet> native, const SheetSource *source,
    unsigned group, unsigned frame, int nativeX, int nativeY, int viewX, int viewY, int viewW, int viewH,
    int sourceX, int sourceY, int sourceHeight, bool blend, const uint8_t *trn, int outline)
{
	// viewX/Y is the unclipped destination; sourceX/Y maps back into the native
	// index texture. Packed CEL frames align at their original bottom baseline.
	const int left = std::max({ viewX, out.region.x, 0 }), top = std::max({ viewY, out.region.y, 0 });
	const int right = std::min({ viewX + viewW, out.region.x + out.w(), int(devilution::gnScreenWidth) });
	const int bottom = std::min({ viewY + viewH, out.region.y + out.h(), int(devilution::gnScreenHeight) });
	if (left >= right || top >= bottom) return;
	std::shared_ptr<GpuSheet> hd;
	if (source && outline < 0) {
		SheetSource request = *source;
		if (source->pcx) {
			request.columns = (source->width + 127) / 128;
			request.rows = (source->rows * native->height + 127) / 128;
			request.width = 128;
		}
		hd = LoadGpuSheet(request);
	}
	auto emit = [&](std::shared_ptr<GpuSheet> sheet, GpuFrame packed, float x, float y, float w, float h) {
		const bool usingHd = hd && sheet == hd;
		GpuSpriteDraw d;
		d.ui = true;
		d.uiHd = usingHd;
		d.uiIndices = native;
		d.sheet = std::move(sheet);
		d.frame = packed;
		d.x = x;
		d.y = y;
		d.w = w;
		d.h = h;
		d.alpha = blend ? 0.5f : 1.0f;
		d.uiX = float(nativeX);
		d.uiY = float(nativeY);
		d.maskX = std::max(left, int(std::floor(x)));
		d.maskY = std::max(top, int(std::floor(y)));
		d.maskW = std::min(right, int(std::ceil(x + w))) - d.maskX;
		d.maskH = std::min(bottom, int(std::ceil(y + h))) - d.maskY;
		if (d.maskW <= 0 || d.maskH <= 0) return;
		Palette(d, source, trn, outline);
		QueueGpuSprite(std::move(d));
		++uiDraws;
		if (usingHd) ++hdDraws;
	};
	if (hd && source->pcx) {
		const int sourceTop = int(frame) * int(native->height) + sourceY;
		for (unsigned col = 0; col < hd->columns; ++col)
			for (unsigned row = 0; row < hd->rows; ++row) {
				const auto &p = hd->frames[col * hd->rows + row];
				if (!p.w || !p.h) continue;
				emit(hd, p, float(viewX - sourceX + int(col) * 128) + float(p.cropX) / 4,
				    float(viewY - sourceTop + int(row) * 128) + float(p.cropY) / 4, float(p.w) / 4, float(p.h) / 4);
			}
	} else if (hd && group < hd->columns && frame < hd->rows) {
		const auto &p = hd->frames[group * hd->rows + frame];
		if (p.w && p.h) emit(hd, p, float(viewX - sourceX) + float(p.cropX) / 4,
			float(viewY - sourceY + sourceHeight - int(hd->height)) + float(p.cropY) / 4, float(p.w) / 4, float(p.h) / 4);
	} else
		emit(native, native->frames[0], float(nativeX), float(nativeY), float(native->width), float(native->height));
}
} // namespace
GpuUiStats GetGpuUiStats()
{
	size_t bytes = 0;
	for (const auto &entry : nativeCache)
		bytes += entry.second->bytes;
	return { uiDraws, hdDraws, nativeUploads, nativeCache.size(), bytes };
}
bool GpuUiEnabled()
{
	const char *flag = SDL_getenv("D1R_GPU_UI");
	return (!flag || std::strcmp(flag, "0") != 0) && CanDrawGpuUi() && GetRendererSwitch().usesHdRenderer() && devilution::ControlMode != devilution::ControlTypes::VirtualGamepad && !GpuTerrainNativeCaptureActive();
}
bool GpuUiPhase() { return phase && GpuUiEnabled(); }
void BeginGpuUiFrame(bool standalone) { phase = standalone; }
void EnterGpuUiPhase() { phase = true; }
void ResetGpuUiFrame()
{
	InvalidateGpuUiHud();
	phase = false;
}
void ClearGpuUiAssets()
{
	phase = false;
	nativeCache.clear();
	cachedSurfaces.clear();
	canonical.clear();
	mappings.clear();
}
void MarkGpuUiSurfaceDirty(const devilution::Surface &out)
{
	if (out.surface && out.surface != devilution::PalSurface && cachedSurfaces.erase(out.surface)) InvalidateGpuUiHud();
}
void RememberGpuUiSurface(const devilution::Surface &out, int x, int bottom, devilution::ClxSprite sprite)
{
	MarkGpuUiSurfaceDirty(out);
	const auto *source = GetSheetSource(sprite);
	if (!source || out.surface == devilution::PalSurface || !out.surface) return;
	if (!source->path.starts_with("hd/ctrlpan/")) return;
	const int top = bottom + 1 - int(sprite.height());
	x += out.region.x;
	const int y = top + out.region.y;
	if (x < 0 || y < 0 || x + sprite.width() > out.surface->w || y + sprite.height() > out.surface->h) return;
	const auto *header = sprite.pixelData() - SheetHeaderSize;
	auto &list = mappings[out.surface];
	list.erase(std::remove_if(list.begin(), list.end(), [&](const Mapping &m) { return m.x == x && m.y == y; }), list.end());
	list.push_back({ source, devilution::LoadLE16(header + 14), devilution::LoadLE16(header + 16), x, y, sprite.width(), sprite.height(), RectBytes(devilution::Surface(out.surface), x, y, sprite.width(), sprite.height()) });
}
bool TranslateGpuUiRect(const devilution::Surface &out, SDL_Rect rect, const uint8_t *trn)
{
	if (!GpuUiPhase() || out.surface != devilution::PalSurface) return false;
	rect.x += out.region.x;
	rect.y += out.region.y;
	return TranslateGpuUiDraws(rect, trn);
}
bool DrawGpuUiRect(const devilution::Surface &out, int x, int y, int w, int h, uint8_t color, bool blend)
{
	if (!GpuUiPhase() || out.surface != devilution::PalSurface) return false;
	const int left = std::max(x, 0), top = std::max(y, 0), right = std::min(x + w, out.w()), bottom = std::min(y + h, out.h());
	if (left >= right || top >= bottom) return true;
	const std::vector<uint8_t> pixel { 0, 255, 0, 255 };
	auto native = Native("solid", 1, 1, pixel);
	if (!native) return false;
	GpuSpriteDraw draw;
	draw.ui = true;
	draw.uiIndices = draw.sheet = native;
	draw.frame = native->frames[0];
	draw.x = draw.maskX = left + out.region.x;
	draw.y = draw.maskY = top + out.region.y;
	draw.w = draw.maskW = right - left;
	draw.h = draw.maskH = bottom - top;
	draw.alpha = blend ? 0.5f : 1;
	draw.uiX = draw.x;
	draw.uiY = draw.y;
	draw.uiScaleX = 1 / draw.w;
	draw.uiScaleY = 1 / draw.h;
	Palette(draw, nullptr, nullptr, color);
	QueueGpuSprite(std::move(draw));
	++uiDraws;
	return true;
}
bool DrawGpuUiSprite(const devilution::Surface &out, int x, int bottom, devilution::ClxSprite sprite, const uint8_t *trn, bool blend, int outline, bool skipZero)
{
	if (!GpuUiPhase() || out.surface != devilution::PalSurface) return false;
	const unsigned width = sprite.width(), height = sprite.height();
	if (!width || !height) return true;
	std::string key = "C";
	key.append(reinterpret_cast<const char *>(sprite.pixelData()), sprite.pixelDataSize());
	key.push_back(char(outline >= 0));
	key.push_back(char(skipZero));
	bool identity = true;
	if (GetSheetSource(sprite)) {
		const auto *map = sprite.pixelData() - SheetHeaderSize + 18;
		for (unsigned i = 0; i < 256; ++i)
			if (map[i] != i) {
				identity = false;
				break;
			}
	}
	key.push_back(char(identity));
	const unsigned w = width + (outline >= 0 ? 2 : 0), h = height + (outline >= 0 ? 2 : 0);
	std::string fullKey = key;
	fullKey.append(reinterpret_cast<const char *>(&w), sizeof(w));
	fullKey.append(reinterpret_cast<const char *>(&h), sizeof(h));
	std::shared_ptr<GpuSheet> native;
	if (auto it = nativeCache.find(fullKey); it != nativeCache.end()) native = it->second;
	if (!native) {
		// CLX skip runs may span several rows. Decode once into palette indices and
		// an explicit occupancy channel; index zero can be opaque.
		std::vector<uint8_t> pixels(size_t(w) * h * 4, 0);
		const auto *src = sprite.pixelData(), *end = src + sprite.pixelDataSize();
		size_t pos = 0;
		while (src < end) {
			uint8_t control = *src++;
			unsigned n;
			if (!devilution::IsClxOpaque(control)) {
				pos += control;
				continue;
			}
			const bool fill = devilution::IsClxOpaqueFill(control);
			n = fill ? devilution::GetClxOpaqueFillWidth(control) : devilution::GetClxOpaquePixelsWidth(control);
			if (src + (fill ? 1 : n) > end || pos + n > size_t(width) * height) return false;
			for (unsigned i = 0; i < n; ++i, ++pos) {
				const auto index = src[fill ? 0 : i];
				const unsigned px = unsigned(pos % width), py = height - 1 - unsigned(pos / width);
				if (outline >= 0) {
					if (skipZero && index == 0) continue;
					for (const auto delta : std::array<std::pair<int, int>, 4> { { { -1, 0 }, { 1, 0 }, { 0, -1 }, { 0, 1 } } }) {
						const size_t at = (size_t(int(py) + 1 + delta.second) * w + int(px) + 1 + delta.first) * 4;
						pixels[at + 1] = 255;
					}
				} else {
					const size_t at = (size_t(py) * w + px) * 4;
					pixels[at] = index;
					pixels[at + 1] = 255;
					pixels[at + 2] = index;
					pixels[at + 3] = identity ? 255 : 0;
				}
			}
			src += fill ? 1 : n;
		}
		native = Native(std::move(key), w, h, pixels);
	}
	if (!native) return false;
	const int nx = x + out.region.x - (outline >= 0 ? 1 : 0), ny = bottom + out.region.y + 1 - int(height) - (outline >= 0 ? 1 : 0);
	const auto *source = outline >= 0 ? nullptr : GetSheetSource(sprite);
	unsigned group = 0, frame = 0;
	if (source) {
		const auto *header = sprite.pixelData() - SheetHeaderSize;
		group = devilution::LoadLE16(header + 14);
		frame = devilution::LoadLE16(header + 16);
	}
	Queue(out, native, source, group, frame, nx, ny, nx, ny, w, h, 0, 0, int(h), blend, trn, outline);
	return true;
}
bool DrawGpuUiSurface(const devilution::Surface &out, const devilution::Surface &src, SDL_Rect rect, devilution::Point position, bool skipZero)
{
	if (!GpuUiPhase() || out.surface != devilution::PalSurface) return false;
	out.Clip(&rect, &position);
	if (rect.w <= 0 || rect.h <= 0) return true;
	const devilution::Surface full(src.surface);

	const int sx = src.region.x + rect.x, sy = src.region.y + rect.y, dx = out.region.x + position.x, dy = out.region.y + position.y;
	const SheetSource *source = nullptr;
	unsigned group = 0, frame = 0;
	int sourceX = sx, sourceY = sy, sourceHeight = full.h();
	const Mapping *mapping = nullptr;
	if (auto it = mappings.find(src.surface); it != mappings.end())
		for (const auto &m : it->second) {
			if (sx < m.x || sy < m.y || sx + rect.w > m.x + m.w || sy + rect.h > m.y + m.h || m.x + m.w > full.w() || m.y + m.h > full.h()) continue;
			// Preserve custom/localized button pixels composited into the original
			// backing. Only unchanged native indices use the HD source colour.
			source = m.source;
			group = m.group;
			frame = m.frame;
			sourceX = sx - m.x;
			sourceY = sy - m.y;
			sourceHeight = m.h;
			mapping = &m;
			break;
		}
	const unsigned sw = full.w(), sh = full.h();
	std::shared_ptr<GpuSheet> native;
	CachedSurface *cached = nullptr;
	if (mapping) {
		auto &entry = cachedSurfaces[src.surface];
		if (entry.pixels != src.surface->pixels || entry.w != full.w() || entry.h != full.h()) {
			entry = {};
			entry.pixels = src.surface->pixels;
			entry.w = full.w();
			entry.h = full.h();
		}
		cached = &entry;
		native = entry.textures[skipZero ? 1 : 0];
	}
	if (!native) {
		const std::string values = RectBytes(full, 0, 0, full.w(), full.h());
		std::string key = "S" + values;
		key.push_back(char(skipZero));
		if (auto it = mappings.find(src.surface); it != mappings.end())
			for (const auto &m : it->second)
				key += m.pixels;
		std::string fullKey = key;
		fullKey.append(reinterpret_cast<const char *>(&sw), sizeof(sw));
		fullKey.append(reinterpret_cast<const char *>(&sh), sizeof(sh));
		if (auto it = nativeCache.find(fullKey); it != nativeCache.end()) native = it->second;
		if (!native) {
			std::vector<uint8_t> rgba(values.size() * 4);
			for (size_t i = 0; i < values.size(); ++i) {
				rgba[i * 4] = uint8_t(values[i]);
				rgba[i * 4 + 1] = !skipZero || uint8_t(values[i]) != 0 ? 255 : 0;
				rgba[i * 4 + 2] = uint8_t(values[i]);
				rgba[i * 4 + 3] = 255;
			}
			if (auto it = mappings.find(src.surface); it != mappings.end())
				for (const auto &m : it->second) {
					if (m.x < 0 || m.y < 0 || m.x + m.w > full.w() || m.y + m.h > full.h()) continue;
					for (int y = 0; y < m.h; ++y)
						for (int x = 0; x < m.w; ++x)
							rgba[(size_t(y + m.y) * sw + x + m.x) * 4 + 2] = uint8_t(m.pixels[size_t(y) * m.w + x]);
				}
			native = Native(std::move(key), full.w(), full.h(), rgba);
		}
		if (cached) cached->textures[skipZero ? 1 : 0] = native;
	}
	if (!native) return false;
	// Surface mapping uses the full index texture even when its HD source is a
	// smaller CEL embedded in a padded backing surface.
	Queue(out, native, source, group, frame, dx - sx, dy - sy, dx, dy, rect.w, rect.h, sourceX, sourceY, sourceHeight, false, nullptr, -1);
	return true;
}
} // namespace reincarnated
#endif
