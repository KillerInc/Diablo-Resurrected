#include "asset_provider.hpp"

#include <cassert>
#include <chrono>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <memory>
#include <string>
#include <utility>

using namespace reincarnated;
namespace fs = std::filesystem;

namespace {
class FakeArchiveProvider final : public AssetProvider {
public:
    explicit FakeArchiveProvider(AssetBytes data) : data_(std::move(data)) {}
    bool read(const std::string &id, AssetBytes &bytes) const override
    {
        if (id != "hd/players/0.png")
            return false;
        bytes = data_;
        return true;
    }
private:
    AssetBytes data_;
};
struct TemporaryDirectory {
    fs::path path;
    ~TemporaryDirectory() {
        std::error_code error;
        fs::remove_all(path, error);
    }
};
void Write(const fs::path &path, const std::string &value)
{
    fs::create_directories(path.parent_path());
    std::ofstream file(path, std::ios::binary);
    assert(file);
    file.write(value.data(), static_cast<std::streamsize>(value.size()));
    assert(file);
}
}

int main()
{
    const std::string id = "hd/players/0.png";
    assert(IsSafeAssetId(id));
    assert(IsSafeAssetId("hd/players/0.png.layout"));
    for (const char *bad : { "", "/etc/passwd", "../outside", "hd/../outside",
                             "hd/./0.png", "hd//0.png", "hd/0.png/",
                             "C:/Windows/file", "hd\\escape" })
        assert(!IsSafeAssetId(bad));

    const auto stamp = std::chrono::steady_clock::now().time_since_epoch().count();
    TemporaryDirectory base {fs::temp_directory_path() /
        ("diablo-reincarnated-assets-" + std::to_string(stamp))};
    const fs::path low = base.path / "installed";
    const fs::path high = base.path / "user";
    Write(low / id, "low");
    Write(high / id, "high");
    Write(low / (id + ".layout"), "96 128 48 128");

    AssetStore store;
    store.mount(std::make_unique<FakeArchiveProvider>(AssetBytes {'p','a','c','k'}));
    store.mountLoose(low.string());
    store.mountLoose(high.string());
    assert(store.providerCount() == 3);
    AssetBytes value;
    assert(store.read(id, value));
    assert(std::string(value.begin(), value.end()) == "high");
    store.mountFallback(std::make_unique<FakeArchiveProvider>(AssetBytes {'n','e','w'}));
    assert(store.read(id, value));
    assert(std::string(value.begin(), value.end()) == "high");
    AssetBytes pairedImage;
    AssetBytes pairedLayout;
    assert(store.readWithSidecar(id, pairedImage, pairedLayout));
    assert(std::string(pairedImage.begin(), pairedImage.end()) == "high");
    assert(pairedLayout.empty()); // high-priority override must not inherit base metadata
    assert(store.read(id + ".layout", value));
    assert(std::string(value.begin(), value.end()) == "96 128 48 128");
    assert(!store.read("hd/missing.png", value) && value.empty());
    assert(!store.read("../outside", value) && value.empty());

    fs::remove(high / id);
    assert(store.read(id, value));
    assert(std::string(value.begin(), value.end()) == "low");
    assert(store.readWithSidecar(id, pairedImage, pairedLayout));
    assert(std::string(pairedLayout.begin(), pairedLayout.end()) == "96 128 48 128");
    fs::remove(low / id);
    assert(store.read(id, value));
    assert(std::string(value.begin(), value.end()) == "pack");
    assert(store.readWithSidecar(id, pairedImage, pairedLayout));
    assert(pairedLayout.empty());
    assert(!store.readWithSidecar("hd/../players/0.png", pairedImage, pairedLayout));
    assert(pairedImage.empty() && pairedLayout.empty());
    assert(!store.read("hd/../players/0.png", value) && value.empty());

    // A sparse synthetic resource above the former 256 MiB byte cap must
    // reach the PNG decoder. Other resource types retain their old policy.
    const auto large = high / "hd/large.PNG";
    {
        std::ofstream file(large, std::ios::binary);
        file.seekp(256ULL * 1024 * 1024);
        file.put('\0');
        if (!file) { std::fputs("Cannot create synthetic oversized PNG\n", stderr); return 1; }
    }
    LooseFileAssetProvider loose(high.string());
    if (!loose.read("hd/large.PNG", value)) { std::fputs("Oversized PNG rejected by provider\n", stderr); return 1; }
    if (value.size() != 256ULL * 1024 * 1024 + 1) { std::fputs("Oversized PNG truncated\n", stderr); return 1; }
    value.clear(); value.shrink_to_fit();
    fs::rename(large, high / "hd/large.dds");
    if (loose.read("hd/large.dds", value)) { std::fputs("Non-PNG guard changed unexpectedly\n", stderr); return 1; }

    // Layout metadata is resolved by the same provider chain as image bytes.
    // An archive can supply the same asset ID later without touching renderer code.
}
