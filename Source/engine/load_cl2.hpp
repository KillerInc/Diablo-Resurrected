#pragma once

#include <array>
#include <cstdint>
#include <cstring>
#include <expected>
#include <string>

#include <function_ref.hpp>

#include "appfat.h"
#include "engine/clx_sprite.hpp"
#include "engine/load_file.hpp"
#include "mpq/mpq_common.hpp"
#include "utils/endian_read.hpp"
#include "utils/endian_write.hpp"
#include "utils/pointer_value_union.hpp"
#include "utils/static_vector.hpp"
#include "utils/status_macros.hpp"
#include "utils/str_cat.hpp"
#include "reincarnated/sheet_source.hpp"

#ifdef UNPACKED_MPQS
#define DEVILUTIONX_CL2_EXT ".clx"
#else
#include "utils/cl2_to_clx.hpp"

#define DEVILUTIONX_CL2_EXT ".cl2"
#endif

namespace devilution {

std::expected<OwnedClxSpriteListOrSheet, std::string> LoadCl2ListOrSheetWithStatus(const char *pszName, PointerOrValue<uint16_t> widthOrWidths);
OwnedClxSpriteListOrSheet LoadCl2ListOrSheet(const char *pszName, PointerOrValue<uint16_t> widthOrWidths);

template <size_t MaxCount>
std::expected<OwnedClxSpriteSheet, std::string> LoadMultipleCl2Sheet(tl::function_ref<const char *(size_t)> filenames, size_t count, uint16_t width)
{
	StaticVector<std::array<char, MaxMpqPathSize>, MaxCount> paths;
	StaticVector<AssetRef, MaxCount> files;
	StaticVector<size_t, MaxCount> fileSizes;
	const size_t sheetHeaderSize = 4 * count;
	size_t totalSize = sheetHeaderSize;
	for (size_t i = 0; i < count; ++i) {
		{
			const char *path = filenames(i);
			paths.emplace_back();
			memcpy(paths.back().data(), path, strlen(path) + 1);
		}
		const char *path = paths.back().data();
		files.emplace_back(FindAsset(path));
		if (!files.back().ok()) {
			FailedToOpenFileError(path, files.back().error());
		}
		const size_t size = files.back().size();
		fileSizes.emplace_back(size);
		totalSize += size;
	}
	auto data = std::unique_ptr<uint8_t[]> { new uint8_t[totalSize] };
#ifndef UNPACKED_MPQS
	const PointerOrValue<uint16_t> frameWidth { width };
#endif
	size_t accumulatedSize = sheetHeaderSize;
	for (size_t i = 0; i < count; ++i) {
		const size_t size = fileSizes[i];
		AssetHandle handle = OpenAsset(std::move(files[i]));
		if (!handle.ok() || !handle.read(&data[accumulatedSize], size)) {
			FailedToOpenFileError(paths[i].data(), handle.error());
		}
		WriteLE32(&data[i * 4], static_cast<uint32_t>(accumulatedSize));
		accumulatedSize += size;
	}
#ifdef UNPACKED_MPQS
	auto result = OwnedClxSpriteSheet { std::move(data), static_cast<uint16_t>(count) };
#else
	auto result = Cl2ToClx(std::move(data), accumulatedSize, frameWidth).sheet();
#endif
#ifdef USE_SDL3
    std::vector<OwnedClxSpriteListOrSheet> lists;
    size_t annotatedSize = sheetHeaderSize;
    for (size_t i = 0; i < count; ++i) {
        lists.push_back(reincarnated::AnnotateSheetSource(OwnedClxSpriteListOrSheet { result[i].clone() }, paths[i].data()));
        annotatedSize += lists.back().dataSize();
    }
    auto annotated = std::make_unique<uint8_t[]>(annotatedSize);
    size_t offset = sheetHeaderSize;
    for (size_t i = 0; i < count; ++i) {
        WriteLE32(annotated.get() + i * 4, static_cast<uint32_t>(offset));
        std::memcpy(annotated.get() + offset, lists[i].list().data(), lists[i].dataSize());
        offset += lists[i].dataSize();
    }
    return OwnedClxSpriteSheet { std::move(annotated), static_cast<uint16_t>(count) };
#else
    return result;
#endif
}

inline std::expected<OwnedClxSpriteList, std::string> LoadCl2WithStatus(const char *pszName, uint16_t width)
{
	ASSIGN_OR_RETURN(OwnedClxSpriteListOrSheet result, LoadCl2ListOrSheetWithStatus(pszName, PointerOrValue<uint16_t> { width }));
	return std::move(result).list();
}

inline OwnedClxSpriteList LoadCl2(const char *pszName, uint16_t width)
{
	return LoadCl2ListOrSheet(pszName, PointerOrValue<uint16_t> { width }).list();
}

inline OwnedClxSpriteList LoadCl2(const char *pszName, const uint16_t *widths)
{
	return LoadCl2ListOrSheet(pszName, PointerOrValue<uint16_t> { widths }).list();
}

inline OwnedClxSpriteSheet LoadCl2Sheet(const char *pszName, uint16_t width)
{
	return LoadCl2ListOrSheet(pszName, PointerOrValue<uint16_t> { width }).sheet();
}

} // namespace devilution
