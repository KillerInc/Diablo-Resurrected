#include "sheet_png.hpp"
#ifdef USE_SDL3
#include <png.h>
#include <algorithm>
#include <cstdlib>
#include <cstring>
#include <sstream>

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
        || parsed.anchorX < 0 || parsed.anchorY < 0 || parsed.anchorX > 65536 || parsed.anchorY > 65536) return false;
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
    png_set_user_limits(png, 65536, 65536);
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
    const size_t size = size_t(width / step) * (height / step) * 4;
    if (size > 128 * 1024 * 1024) png_error(png, "Sheet cache entry exceeds budget");
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
    std::free(row); std::free(pixels);
    png_destroy_read_struct(&png, &info, nullptr);
    return true;
}
} // namespace reincarnated
#endif
