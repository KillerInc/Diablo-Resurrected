#pragma once

#include <cstddef>
#include <cstdint>
#include <memory>
#include <string>
#include <unordered_map>
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
    virtual std::vector<std::string> list(const std::string &prefix) const { return {}; }
};

class LooseFileAssetProvider final : public AssetProvider {
public:
    explicit LooseFileAssetProvider(std::string root);
    bool read(const std::string &assetId, AssetBytes &bytes) const override;
    std::vector<std::string> list(const std::string &prefix) const override;
private:
    std::string root_;
};

class AssetStore {
public:
    // Last mounted provider takes precedence: mount base packs first, loose
    // overrides last. A missing asset falls through to the next provider.
    void mount(std::unique_ptr<AssetProvider> provider);
    // Insert below *all* existing providers. Intended for future archives:
    // loose content always overrides packaged content even if the pack mounts later.
    void mountFallback(std::unique_ptr<AssetProvider> provider);
    void mountLoose(std::string root);

    [[nodiscard]] bool read(const std::string &assetId, AssetBytes &bytes) const;
    [[nodiscard]] std::vector<std::string> list(const std::string &prefix) const;
    // Resolve image + optional HD/layouts.csv row from the SAME provider.
    // This avoids mixing an overriding PNG with stale metadata from a base pack.
    [[nodiscard]] bool readWithLayout(const std::string &assetId,
        AssetBytes &bytes, AssetBytes &sidecar) const;
    [[nodiscard]] size_t providerCount() const noexcept { return providers_.size(); }
private:
    using LayoutRows = std::unordered_map<std::string, AssetBytes>;
    const LayoutRows &layoutRows(const AssetProvider &provider) const;
    std::vector<std::unique_ptr<AssetProvider>> providers_;
    // Loaded on first use, including a missing/invalid table. The global HD
    // store lives until process exit; F10/image-cache resets do not evict this.
    mutable std::unordered_map<const AssetProvider *, LayoutRows> layoutTables_;
};

} // namespace reincarnated
