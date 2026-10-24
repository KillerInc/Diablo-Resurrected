#pragma once
#include <cstdint>
#include <vector>
#include "sheet_source.hpp"
namespace reincarnated {
struct SheetLayout {
    unsigned density = 0;
    int anchorX = 0, anchorY = 0;
};
// Optional named-sheet sidecar, in original logical pixels:
// D1R_SHEET_V1 <source density> <horizontal center anchor> <bottom anchor>
bool ParseSheetLayout(const std::vector<uint8_t> &bytes, SheetLayout &layout);
struct SheetImage {
    unsigned width = 0, height = 0, cellWidth = 0, cellHeight = 0, density = 0;
    unsigned logicalWidth = 0;
    int anchorX = 0, anchorY = 0;
    std::vector<uint8_t> rgba;
};
// Stream even huge atlases one row at a time. Retain the source samples needed
// by the current 1x/2x world mapping, never allocate the full 8x decode.
bool DecodeSheetPng(const std::vector<uint8_t> &bytes, const SheetSource &source, SheetImage &image, const SheetLayout *layout = nullptr);
} // namespace reincarnated
