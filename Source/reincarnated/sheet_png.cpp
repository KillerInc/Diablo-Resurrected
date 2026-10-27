#include "sheet_png.hpp"
#ifdef USE_SDL3
#include <png.h>
#include <algorithm>
#include <cstdlib>
#include <cstring>
#include <sstream>
#include <limits>
#include <SDL3/SDL_log.h>
#include <SDL3/SDL_stdinc.h>
#include "sheet_memory.hpp"
#include "sheet_diagnostics.hpp"

namespace reincarnated {
namespace {
struct Reader { const uint8_t *bytes; size_t size, position; };
void Read(png_structp png, png_bytep target, png_size_t count)
{
    auto *reader = static_cast<Reader *>(png_get_io_ptr(png));
    if (count > reader->size - reader->position) png_error(png, "Truncated sheet");
    std::memcpy(target, reader->bytes + reader->position, count);
    reader->position += count;
}
void Error(png_structp png, png_const_charp) { png_longjmp(png, 1); }
void Warning(png_structp, png_const_charp) {}
}
bool ParseSheetLayout(const std::vector<uint8_t> &bytes, SheetLayout &layout)
{
    layout = {};
    if (bytes.size() > 256) return false;
    std::istringstream input(std::string(bytes.begin(), bytes.end()));
    std::string version;
    SheetLayout parsed;
    if (!(input >> version >> parsed.density >> parsed.anchorX >> parsed.anchorY)
        || version != "D1R_SHEET_V1") return false;
    input >> std::ws;
    if (!input.eof() || !(parsed.density == 1 || parsed.density == 2 || parsed.density == 4
        || parsed.density == 8 || parsed.density == 16)
        || parsed.anchorX < 0 || parsed.anchorY < 0) return false;
    layout = parsed;
    return true;
}
bool DecodeSheetPng(const std::vector<uint8_t> &bytes, const SheetSource &source, SheetImage &image, const SheetLayout *layout)
{
    image = {};
    if (!source.columns || !source.rows || !source.width || bytes.empty()) return false;
    auto *png = png_create_read_struct(PNG_LIBPNG_VER_STRING, nullptr, Error, Warning);
    if (!png) return false;
    auto *info = png_create_info_struct(png);
    if (!info) { png_destroy_read_struct(&png, nullptr, nullptr); return false; }
    uint8_t *volatile row = nullptr;
    uint8_t *volatile pixels = nullptr;
    if (setjmp(png_jmpbuf(png))) {
        std::free(row); std::free(pixels);
        png_destroy_read_struct(&png, &info, nullptr);
        return false;
    }
    Reader reader { bytes.data(), bytes.size(), 0 };
    png_set_read_fn(png, &reader, Read);
    // PNG's format limit, not an artwork-size policy. Allocation/overflow and
    // grid checks below still reject images that cannot actually be decoded.
    png_set_user_limits(png, PNG_UINT_31_MAX, PNG_UINT_31_MAX);
    png_read_info(png, info);
    const unsigned width = png_get_image_width(png, info), height = png_get_image_height(png, info);
    if (width % source.columns || height % source.rows) png_error(png, "Invalid sheet grid");
    const unsigned cellWidth = width / source.columns, cellHeight = height / source.rows;
    if (!cellWidth || (!layout && cellWidth % source.width)) png_error(png, "Invalid sheet scale");
    const unsigned density = layout ? layout->density : cellWidth / source.width;
    if (!(density == 1 || density == 2 || density == 4 || density == 8 || density == 16)
        || cellWidth % density || cellHeight % density || !cellHeight) png_error(png, "Unsupported sheet scale");
    if (layout && (cellWidth / density < source.width || layout->anchorX < 0 || layout->anchorY < 0
        || unsigned(layout->anchorX) > cellWidth / density || unsigned(layout->anchorY) > cellHeight / density))
        png_error(png, "Invalid sheet canvas anchor");
    if (png_get_interlace_type(png, info) != PNG_INTERLACE_NONE) png_error(png, "Interlaced sheets need offline conversion");
    const unsigned step = std::max(1U, density / 2);
    if (width % step || height % step) png_error(png, "Invalid sample grid");
    if (size_t(width) > std::numeric_limits<size_t>::max() / 4
        || size_t(width / step) > std::numeric_limits<size_t>::max() / 4 / (height / step))
        png_error(png, "Sheet allocation size overflows address space");
    const size_t size = size_t(width / step) * (height / step) * 4;
    const size_t warning = MemoryTarget(SDL_getenv("D1R_SHEET_WARN_MB"), 128);
    const unsigned flags = MemoryWarningFlags(size, warning);
    if (flags || width > 65536 || height > 65536 || bytes.size() > 256 * MemoryMiB)
        SheetWarning(
            "HD_PNG_WARNING flags={} source={} png={}x{} compressed_mib={:.2f} retained_mib={:.2f} warning_mib={:.2f} dimension_over_65536={} compressed_over_256mib={} action=continue",
            flags, source.path, width, height, double(bytes.size()) / MemoryMiB,
            double(size) / MemoryMiB, double(warning) / MemoryMiB,
            int(width > 65536 || height > 65536), int(bytes.size() > 256 * MemoryMiB));
    const int type = png_get_color_type(png, info), depth = png_get_bit_depth(png, info);
    if (depth == 16) png_set_strip_16(png);
    if (type == PNG_COLOR_TYPE_PALETTE) png_set_palette_to_rgb(png);
    if (type == PNG_COLOR_TYPE_GRAY && depth < 8) png_set_expand_gray_1_2_4_to_8(png);
    const bool transparent = png_get_valid(png, info, PNG_INFO_tRNS) != 0;
    if (transparent) png_set_tRNS_to_alpha(png);
    if (type == PNG_COLOR_TYPE_GRAY || type == PNG_COLOR_TYPE_GRAY_ALPHA) png_set_gray_to_rgb(png);
    if (!(type & PNG_COLOR_MASK_ALPHA) && !transparent) png_set_add_alpha(png, 255, PNG_FILLER_AFTER);
    png_read_update_info(png, info);
    if (png_get_rowbytes(png, info) != size_t(width) * 4) png_error(png, "Invalid pixel format");
    row = static_cast<uint8_t *>(std::malloc(size_t(width) * 4));
    pixels = static_cast<uint8_t *>(std::malloc(size));
    if (!row || !pixels) png_error(png, "Sheet allocation failed");
    for (unsigned y = 0; y < height; ++y) {
        png_read_row(png, row, nullptr);
        if (y % step != step / 2) continue;
        auto *dst = pixels + size_t(y / step) * (width / step) * 4;
        for (unsigned x = 0; x < width / step; ++x)
            std::memcpy(dst + x * 4, row + (x * step + step / 2) * 4, 4);
    }
    png_read_end(png, nullptr);
    image.width = width / step; image.height = height / step;
    image.cellWidth = cellWidth / step; image.cellHeight = cellHeight / step;
    image.density = density / step;
    image.logicalWidth = cellWidth / density;
    image.anchorX = layout ? layout->anchorX : int(source.width / 2);
    image.anchorY = layout ? layout->anchorY : int(cellHeight / density);
    image.rgba.assign(pixels, pixels + size);
    // Sample while both retained buffers exist, before the staging copy frees.
    // This captures transient decode pressure as well as steady cache usage.
    const size_t process = ProcessPrivateMemoryBytes();
    const size_t processTarget = MemoryTarget(SDL_getenv("D1R_PROCESS_WARN_MB"), 8192);
    const unsigned processFlags = MemoryWarningFlags(process, processTarget);
    if (processFlags)
        SheetWarning(
            "HD_MEMORY_WARNING kind=decode_peak_private_commit flags={} used_mib={:.2f} target_mib={:.2f} source={} action=continue",
            processFlags, double(process) / MemoryMiB, double(processTarget) / MemoryMiB, source.path);
    std::free(row); std::free(pixels);
    png_destroy_read_struct(&png, &info, nullptr);
    return true;
}
} // namespace reincarnated
#endif
