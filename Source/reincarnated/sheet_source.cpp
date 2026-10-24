#include "sheet_source.hpp"
#ifdef USE_SDL3

#include <algorithm>
#include <cstring>
#include <deque>
#include <vector>
#include "utils/endian_write.hpp"

namespace reincarnated {
namespace {
std::deque<SheetSource> &Sources() { static std::deque<SheetSource> sources; return sources; }
}

devilution::OwnedClxSpriteListOrSheet AnnotateSheetSource(
    devilution::OwnedClxSpriteListOrSheet data, const char *path)
{
#ifndef USE_SDL3
    return data;
#else
    using namespace devilution;
    std::string name(path);
    for (char &c : name) { if (c == '\\') c = '/'; else if (c >= 'A' && c <= 'Z') c += 'a' - 'A'; }
    // Only installed world-sprite directories participate; UI and tile microcells
    // keep their existing rendering and special masks.
    if (!(name.starts_with("plrgfx/") || name.starts_with("monsters/")
            || name.starts_with("missiles/") || name.starts_with("objects/")
            || name.starts_with("towners/"))) return data;
    const auto dot = name.find_last_of('.');
    if (dot != std::string::npos) name.resize(dot);
    name = "hd/" + name + ".png";
    const ClxSpriteListOrSheet view(data);
    const unsigned columns = view.isSheet() ? view.sheet().numLists() : 1;
    unsigned rows = 0, width = 0;
    for (unsigned group = 0; group < columns; ++group) {
        const auto list = view.isSheet() ? view.sheet()[group] : view.list();
        rows = std::max(rows, list.numSprites());
        for (const auto sprite : list) {
            if (width && width != sprite.width()) return data;
            width = sprite.width();
        }
    }
    if (!width || !rows || columns > 65535 || rows > 65535) return data;
    auto &sources = Sources();
    auto found = std::find_if(sources.begin(), sources.end(), [&](const SheetSource &s) {
        return s.path == name && s.columns == columns && s.rows == rows && s.width == width;
    });
    const uint32_t id = static_cast<uint32_t>(found - sources.begin());
    if (found == sources.end()) sources.push_back({ name, columns, rows, width });
    std::vector<uint8_t> bytes(view.isSheet() ? 4 * columns : 0);
    for (unsigned group = 0; group < columns; ++group) {
        const auto list = view.isSheet() ? view.sheet()[group] : view.list();
        const size_t base = bytes.size();
        if (view.isSheet()) WriteLE32(bytes.data() + group * 4, static_cast<uint32_t>(base));
        bytes.resize(base + 4 * (list.numSprites() + 2));
        WriteLE32(bytes.data() + base, list.numSprites());
        for (unsigned frame = 0; frame < list.numSprites(); ++frame) {
            const auto sprite = list[frame];
            const size_t start = bytes.size();
            WriteLE32(bytes.data() + base + 4 * (frame + 1), static_cast<uint32_t>(start - base));
            bytes.resize(start + SheetHeaderSize + sprite.pixelDataSize());
            auto *header = bytes.data() + start;
            WriteLE16(header, SheetHeaderSize);
            WriteLE16(header + 2, sprite.width()); WriteLE16(header + 4, sprite.height());
            WriteLE32(header + 6, SheetHeaderMagic); WriteLE32(header + 10, id);
            WriteLE16(header + 14, static_cast<uint16_t>(group));
            WriteLE16(header + 16, static_cast<uint16_t>(frame));
            for (unsigned i = 0; i < 256; ++i) header[18 + i] = static_cast<uint8_t>(i);
            std::memcpy(header + SheetHeaderSize, sprite.pixelData(), sprite.pixelDataSize());
        }
        WriteLE32(bytes.data() + base + 4 * (list.numSprites() + 1), static_cast<uint32_t>(bytes.size() - base));
    }
    auto owned = std::make_unique<uint8_t[]>(bytes.size());
    std::memcpy(owned.get(), bytes.data(), bytes.size());
    return OwnedClxSpriteListOrSheet(std::move(owned), data.numLists());
#endif
}

const SheetSource *GetSheetSource(devilution::ClxSprite sprite)
{
    if (sprite.headerSize() != SheetHeaderSize) return nullptr;
    const auto *header = sprite.pixelData() - SheetHeaderSize;
    if (devilution::LoadLE32(header + 6) != SheetHeaderMagic) return nullptr;
    const auto id = devilution::LoadLE32(header + 10);
    auto &sources = Sources();
    return id < sources.size() ? &sources[id] : nullptr;
}

void ApplySheetTranslation(devilution::ClxSprite sprite, const uint8_t *translation)
{
    if (!GetSheetSource(sprite)) return;
    auto *map = const_cast<uint8_t *>(sprite.pixelData()) - SheetHeaderSize + 18;
    for (unsigned i = 0; i < 256; ++i) map[i] = translation[map[i]];
}
} // namespace reincarnated
#endif
