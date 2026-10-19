#pragma once

#include <cstddef>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

namespace reincarnated {

using AssetBytes = std::vector<uint8_t>;

// Virtual asset names use forward slashes, relative to an asset root, e.g.
// "hd/players/0.png". Reject absolute paths and traversal before any provider.
[[nodiscard]] bool IsSafeAssetId(const std::string &id) noexcept;

// A future MPQ/ZIP/etc. reader implements this interface; renderers and image
// decoders do not need to know whether bytes came from a folder or an archive.
class AssetProvider {
public:
    virtual ~AssetProvider() = default;
    virtual bool read(const std::string &assetId, AssetBytes &bytes) const = 0;
};

class LooseFileAssetProvider final : public AssetProvider {
public:
    explicit LooseFileAssetProvider(std::string root);
    bool read(const std::string &assetId, AssetBytes &bytes) const override;
private:
    std::string root_;
};

class AssetStore {
public:
    // Last mounted provider takes precedence: mount base packs first, loose
    // overrides last. A missing asset falls through to the next provider.
    void mount(std::unique_ptr<AssetProvider> provider);
    void mountLoose(std::string root);

    [[nodiscard]] bool read(const std::string &assetId, AssetBytes &bytes) const;
    [[nodiscard]] size_t providerCount() const noexcept { return providers_.size(); }
private:
    std::vector<std::unique_ptr<AssetProvider>> providers_;
};

} // namespace reincarnated
