#include "asset_provider.hpp"

#include <cassert>
#include <chrono>
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
    assert(store.read(id + ".layout", value));
    assert(std::string(value.begin(), value.end()) == "96 128 48 128");
    assert(!store.read("hd/missing.png", value) && value.empty());
    assert(!store.read("../outside", value) && value.empty());

    fs::remove(high / id);
    assert(store.read(id, value));
    assert(std::string(value.begin(), value.end()) == "low");
    fs::remove(low / id);
    assert(store.read(id, value));
    assert(std::string(value.begin(), value.end()) == "pack");
    assert(!store.read("hd/../players/0.png", value) && value.empty());

    // Layout metadata is resolved by the same provider chain as image bytes.
    // An archive can supply the same asset ID later without touching renderer code.
}
