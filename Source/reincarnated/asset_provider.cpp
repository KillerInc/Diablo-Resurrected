#include "asset_provider.hpp"

#include <filesystem>
#include <fstream>
#include <limits>
#include <utility>

namespace reincarnated {

namespace {
// Single image resources may be high resolution, but should not exhaust RAM
// because of an accidental or maliciously huge file.
constexpr std::uintmax_t MaxLooseAssetBytes = 256ULL * 1024ULL * 1024ULL;
}

bool IsSafeAssetId(const std::string &id) noexcept
{
    if (id.empty() || id.size() > 1024 || id.front() == '/')
        return false;
    // Canonical asset IDs only: no Windows separators, drives, embedded NUL,
    // empty segments, or parent/current-directory traversals.
    size_t start = 0;
    for (size_t i = 0; i <= id.size(); ++i) {
        if (i < id.size()) {
            const unsigned char c = static_cast<unsigned char>(id[i]);
            if (c == '\\' || c == ':' || c < 32)
                return false;
            if (id[i] != '/')
                continue;
        }
        if (i == start)
            return false;
        const size_t length = i - start;
        if ((length == 1 && id[start] == '.')
            || (length == 2 && id[start] == '.' && id[start + 1] == '.'))
            return false;
        start = i + 1;
    }
    return true;
}

LooseFileAssetProvider::LooseFileAssetProvider(std::string root)
    : root_(std::move(root))
{
}

bool LooseFileAssetProvider::read(const std::string &assetId, AssetBytes &bytes) const
{
    if (!IsSafeAssetId(assetId))
        return false;

    const std::filesystem::path filename =
        std::filesystem::u8path(root_.empty() ? "." : root_) /
        std::filesystem::u8path(assetId);
    std::ifstream input(filename, std::ios::in | std::ios::binary | std::ios::ate);
    if (!input)
        return false;
    const std::streampos fileSize = input.tellg();
    if (fileSize <= 0 || static_cast<std::uintmax_t>(fileSize) > MaxLooseAssetBytes)
        return false;
    if (fileSize > std::numeric_limits<std::streamsize>::max())
        return false;

    AssetBytes contents(static_cast<size_t>(fileSize));
    input.seekg(0, std::ios::beg);
    if (!input.read(reinterpret_cast<char *>(contents.data()), static_cast<std::streamsize>(fileSize)))
        return false;
    bytes = std::move(contents);
    return true;
}

void AssetStore::mount(std::unique_ptr<AssetProvider> provider)
{
    if (provider != nullptr)
        providers_.push_back(std::move(provider));
}

void AssetStore::mountFallback(std::unique_ptr<AssetProvider> provider)
{
    if (provider != nullptr)
        providers_.insert(providers_.begin(), std::move(provider));
}

void AssetStore::mountLoose(std::string root)
{
    mount(std::make_unique<LooseFileAssetProvider>(std::move(root)));
}

bool AssetStore::read(const std::string &assetId, AssetBytes &bytes) const
{
    bytes.clear();
    if (!IsSafeAssetId(assetId))
        return false;
    for (auto it = providers_.rbegin(); it != providers_.rend(); ++it) {
        if ((*it)->read(assetId, bytes))
            return true;
        bytes.clear();
    }
    return false;
}

} // namespace reincarnated
