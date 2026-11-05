#pragma once
#include <array>
#include <cstdint>
#include <vector>

namespace reincarnated {
struct DdsImage { unsigned width = 0, height = 0; std::vector<uint8_t> rgba; };
// Loose prototype DDS: 32-bit RGB(A), BC1/DXT1, BC2/DXT3, BC3/DXT5.
// No animation container, cubemap, volume texture, or implicit GPU format guess.
inline bool DecodeDds(const std::vector<uint8_t> &bytes, DdsImage &out)
{
    out = {};
    if (bytes.size() < 128) return false;
    auto u32 = [&](size_t i) { return uint32_t(bytes[i]) | uint32_t(bytes[i+1]) << 8 | uint32_t(bytes[i+2]) << 16 | uint32_t(bytes[i+3]) << 24; };
    if (u32(0) != 0x20534444 || u32(4) != 124 || u32(76) != 32) return false;
    const unsigned w = u32(16), h = u32(12);
    if (!w || !h || w > 16384 || h > 16384 || uint64_t(w) * h > 16777216 || u32(112) != 0 || u32(24) > 1) return false;
    const unsigned format = u32(84), flags = u32(80);
    const bool bc1 = format == 0x31545844, bc2 = format == 0x33545844, bc3 = format == 0x35545844;
    const bool raw = !(flags & 4) && (flags & 0x40) && u32(88) == 32;
    if (!raw && !(flags & 4 && (bc1 || bc2 || bc3))) return false;
    const size_t blockSize = bc1 ? 8 : 16;
    const size_t pitch = raw ? ((u32(8) & 8) ? u32(20) : size_t(w) * 4) : 0;
    if (raw && (pitch < size_t(w) * 4 || pitch > bytes.size())) return false;
    const size_t required = raw ? pitch * h : size_t((w + 3) / 4) * ((h + 3) / 4) * blockSize;
    if (required > bytes.size() - 128) return false;
    out.width = w; out.height = h; out.rgba.resize(size_t(w) * h * 4);
    if (raw) {
        std::array<uint32_t, 4> masks { u32(92), u32(96), u32(100), u32(104) };
        uint32_t used = 0;
        for (unsigned c = 0; c < 4; ++c) {
            uint32_t mask = masks[c];
            if ((!mask && c < 3) || (used & mask)) { out = {}; return false; }
            used |= mask;
            if (mask) { while (!(mask & 1)) mask >>= 1; if ((mask & (mask + 1)) != 0) { out = {}; return false; } }
        }
        for (unsigned y = 0; y < h; ++y) for (unsigned x = 0; x < w; ++x) {
            const auto pixel = u32(128 + y * pitch + x * 4);
            for (unsigned c = 0; c < 4; ++c) {
                uint32_t mask = masks[c], value = pixel;
                if (!mask) { out.rgba[(size_t(y) * w + x) * 4 + c] = 255; continue; }
                while (!(mask & 1)) { mask >>= 1; value >>= 1; }
                out.rgba[(size_t(y) * w + x) * 4 + c] = uint64_t(value & mask) * 255 / mask;
            }
        }
        return true;
    }
    auto rgb565 = [](unsigned c) { return std::array<unsigned, 4> { ((c >> 11) & 31) * 255 / 31, ((c >> 5) & 63) * 255 / 63, (c & 31) * 255 / 31, 255 }; };
    size_t pos = 128;
    for (unsigned by = 0; by < h; by += 4) for (unsigned bx = 0; bx < w; bx += 4, pos += blockSize) {
        const size_t colors = pos + (bc1 ? 0 : 8);
        const unsigned c0 = bytes[colors] | unsigned(bytes[colors+1]) << 8, c1 = bytes[colors+2] | unsigned(bytes[colors+3]) << 8;
        std::array<std::array<unsigned,4>,4> palette { rgb565(c0), rgb565(c1), {}, {} };
        for (unsigned c = 0; c < 3; ++c) {
            palette[2][c] = c0 > c1 || !bc1 ? (2 * palette[0][c] + palette[1][c]) / 3 : (palette[0][c] + palette[1][c]) / 2;
            palette[3][c] = c0 > c1 || !bc1 ? (palette[0][c] + 2 * palette[1][c]) / 3 : 0;
        }
        palette[2][3] = 255; palette[3][3] = c0 > c1 || !bc1 ? 255 : 0;
        std::array<unsigned,8> alpha {};
        uint64_t alphaIndices = 0;
        if (bc3) {
            alpha[0] = bytes[pos]; alpha[1] = bytes[pos+1];
            const unsigned n = alpha[0] > alpha[1] ? 7 : 5;
            for (unsigned i = 1; i < n; ++i) alpha[i+1] = ((n-i)*alpha[0] + i*alpha[1]) / n;
            if (n == 5) { alpha[6] = 0; alpha[7] = 255; }
            for (unsigned i = 0; i < 6; ++i) alphaIndices |= uint64_t(bytes[pos+2+i]) << (8*i);
        }
        const uint32_t indices = u32(colors+4);
        for (unsigned i = 0; i < 16; ++i) {
            const unsigned x = bx + i % 4, y = by + i / 4;
            if (x >= w || y >= h) continue;
            auto color = palette[(indices >> (2*i)) & 3];
            if (bc2) color[3] = ((bytes[pos+i/2] >> ((i%2)*4)) & 15) * 17;
            if (bc3) color[3] = alpha[(alphaIndices >> (3*i)) & 7];
            for (unsigned c = 0; c < 4; ++c) out.rgba[(size_t(y)*w+x)*4+c] = color[c];
        }
    }
    return true;
}
}
