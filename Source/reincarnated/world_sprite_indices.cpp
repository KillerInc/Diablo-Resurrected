#include "world_sprite_indices.hpp"
#ifdef USE_SDL3
#include <cstring>
#include <optional>
#include <string>
#include <unordered_map>
#include <vector>
#include "engine/load_file.hpp"
#include "gpu_sprites.hpp"
#include "utils/clx_decode.hpp"
namespace reincarnated {
namespace {
std::unordered_map<std::string, std::shared_ptr<GpuSheet>> cache;
std::optional<std::array<SDL_Color, 256>> palette;
bool triedPalette = false;
}
bool UsesNativeWorldIndices(const SheetSource &source)
{
    return source.path.starts_with("hd/objects/") || source.path.starts_with("hd/towners/")
        || source.path == "hd/levels/l1data/l1s.png" || source.path == "hd/levels/l2data/l2s.png"
        || source.path == "hd/levels/towndata/towns.png";
}
const std::array<SDL_Color, 256> *WorldSourcePalette()
{
    if (!triedPalette) {
        triedPalette = true;
        size_t size = 0;
        auto bytes = devilution::LoadFileInMemWithStatus<uint8_t>("levels/towndata/town.pal", &size);
        if (bytes && size == 768) {
            palette.emplace();
            for (unsigned i = 0; i < 256; ++i) (*palette)[i] = { (*bytes)[i*3], (*bytes)[i*3+1], (*bytes)[i*3+2], 255 };
        }
    }
    return palette ? &*palette : nullptr;
}
std::shared_ptr<GpuSheet> WorldSpriteIndices(devilution::ClxSprite sprite)
{
    const unsigned w = sprite.width(), h = sprite.height();
    std::string key(reinterpret_cast<const char *>(sprite.pixelData()), sprite.pixelDataSize());
    key.append(reinterpret_cast<const char *>(&w), sizeof(w)); key.append(reinterpret_cast<const char *>(&h), sizeof(h));
    bool identity = true;
    const auto *header = sprite.pixelData() - SheetHeaderSize;
    for (unsigned i = 0; i < 256; ++i) if (header[18+i] != i) { identity = false; break; }
    key.push_back(char(identity));
    if (auto it = cache.find(key); it != cache.end()) return it->second;
    std::vector<uint8_t> data(size_t(w)*h*4, 0);
    const auto *src = sprite.pixelData(), *end = src + sprite.pixelDataSize(); size_t pos = 0;
    while (src < end) {
        const uint8_t control = *src++;
        if (!devilution::IsClxOpaque(control)) { pos += control; if (pos > size_t(w)*h) return {}; continue; }
        const bool fill = devilution::IsClxOpaqueFill(control);
        const unsigned n = fill ? devilution::GetClxOpaqueFillWidth(control) : devilution::GetClxOpaquePixelsWidth(control);
        if (src + (fill ? 1 : n) > end || pos + n > size_t(w)*h) return {};
        for (unsigned i = 0; i < n; ++i, ++pos) {
            const size_t at = (size_t(h - 1 - pos/w)*w + pos%w)*4;
            data[at] = src[fill ? 0 : i]; data[at+1] = 255; data[at+2] = data[at]; data[at+3] = identity ? 255 : 0;
        }
        src += fill ? 1 : n;
    }
    auto texture = CreateGpuUiIndices(w, h, data.data());
    if (texture) cache.emplace(std::move(key), texture);
    return texture;
}
void ClearWorldSpriteIndices() { cache.clear(); palette.reset(); triedPalette = false; }
}
#endif
