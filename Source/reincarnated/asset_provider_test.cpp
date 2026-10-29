#include "asset_provider.hpp"

#include <cassert>
#include <algorithm>
#include <chrono>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <memory>
#include <string>
#include <utility>
#include <thread>

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
class TableProvider final : public AssetProvider {
public:
    std::string csv;
    mutable unsigned tableReads = 0;
    mutable unsigned individualLayoutReads = 0;
    bool read(const std::string &id, AssetBytes &bytes) const override
    {
        if (id == "hd/layouts.csv") {
            ++tableReads;
            bytes.assign(csv.begin(), csv.end());
            return !csv.empty();
        }
        if (id == "hd/players/0.png" || id == "hd/players/a,b.png") {
            bytes = {'p', 'n', 'g'};
            return true;
        }
        if (id == "hd/players/0.png.layout") {
            ++individualLayoutReads;
            const std::string text = "96 128 48 128";
            bytes.assign(text.begin(), text.end());
            return true;
        }
        return false;
    }
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

    Write(low / "hd/layouts.csv", "path,layout\nplayers/0.png,96 128 48 128\n");

    AssetStore store;
    store.mount(std::make_unique<FakeArchiveProvider>(AssetBytes {'p','a','c','k'}));
    store.mountLoose(low.string());
    store.mountLoose(high.string());
    assert(store.providerCount() == 3);
    const auto listed = store.list("hd/players/");
    assert(std::count(listed.begin(), listed.end(), id) == 1);
    assert(store.list("hd/../players").empty());
    assert(store.list("hd/monsters").empty());
    AssetBytes value;
    assert(store.read(id, value));
    assert(std::string(value.begin(), value.end()) == "high");
    store.mountFallback(std::make_unique<FakeArchiveProvider>(AssetBytes {'n','e','w'}));
    assert(store.read(id, value));
    assert(std::string(value.begin(), value.end()) == "high");
    AssetBytes pairedImage;
    AssetBytes pairedLayout;
    assert(store.readWithLayout(id, pairedImage, pairedLayout));
    assert(std::string(pairedImage.begin(), pairedImage.end()) == "high");
    assert(pairedLayout.empty()); // high-priority override must not inherit base metadata
    assert(store.read(id + ".layout", value));
    assert(std::string(value.begin(), value.end()) == "96 128 48 128");
    assert(!store.read("hd/missing.png", value) && value.empty());
    assert(!store.read("../outside", value) && value.empty());

    fs::remove(high / id);
    assert(store.read(id, value));
    assert(std::string(value.begin(), value.end()) == "low");
    assert(store.readWithLayout(id, pairedImage, pairedLayout));
    assert(std::string(pairedLayout.begin(), pairedLayout.end()) == "96 128 48 128");
    fs::remove(low / id);
    assert(store.read(id, value));
    assert(std::string(value.begin(), value.end()) == "pack");
    assert(store.readWithLayout(id, pairedImage, pairedLayout));
    assert(pairedLayout.empty());
    assert(!store.readWithLayout("hd/../players/0.png", pairedImage, pairedLayout));
    assert(pairedImage.empty() && pairedLayout.empty());
    assert(!store.read("hd/../players/0.png", value) && value.empty());

    // A table wins over stale sidecars, and remains cached for the store's
    // entire lifetime even if the source file changes or disappears.
    AssetStore indexed;
    auto provider = std::make_unique<TableProvider>();
    auto *table = provider.get();
    table->csv = "\xEF\xBB\xBFpath,layout\r\n"
                 "PLAYERS/0.PNG,D1R_SHEET_V1 8 96 160\r\n"
                 "\"players/a,b.png\",\"D1R_SHEET_V1 4 48 96\"\r\n";
    indexed.mount(std::move(provider));
    for (int i = 0; i < 20; ++i) {
        assert(indexed.readWithLayout(id, pairedImage, pairedLayout));
        assert(std::string(pairedLayout.begin(), pairedLayout.end()) == "D1R_SHEET_V1 8 96 160");
    }
    assert(table->tableReads == 1);
    assert(table->individualLayoutReads == 0);

    AssetStore parallel;
    auto parallelProvider = std::make_unique<TableProvider>();
    auto *parallelSource = parallelProvider.get();
    parallelSource->csv = "path,layout\nplayers/0.png,D1R_SHEET_V1 8 96 160\n";
    parallel.mount(std::move(parallelProvider));
    std::vector<std::thread> readers;
    for (int i = 0; i < 8; ++i) readers.emplace_back([&] {
        for (int n = 0; n < 100; ++n) {
            AssetBytes image, layout;
            assert(parallel.readWithLayout(id, image, layout));
            assert(std::string(layout.begin(), layout.end()) == "D1R_SHEET_V1 8 96 160");
        }
    });
    for (auto &reader : readers) reader.join();
    assert(parallelSource->tableReads == 1 && parallelSource->individualLayoutReads == 0);

    AssetStore missingTable;
    auto missing = std::make_unique<TableProvider>();
    auto *missingSource = missing.get();
    missingTable.mount(std::move(missing));
    assert(missingTable.readWithLayout(id, pairedImage, pairedLayout) && pairedLayout.empty());
    assert(missingSource->tableReads == 1 && missingSource->individualLayoutReads == 0);
    table->csv.clear();
    assert(indexed.readWithLayout("hd/players/a,b.png", pairedImage, pairedLayout));
    assert(std::string(pairedLayout.begin(), pairedLayout.end()) == "D1R_SHEET_V1 4 48 96");
    assert(table->tableReads == 1);

    // A new store (the next process) reads the edited table. Missing rows use
    // default alignment, never a lower provider's consolidated metadata.
    Write(low / id, "low"); Write(high / id, "high");
    Write(low / "hd/layouts.csv", "path,layout\nplayers/0.png,D1R_SHEET_V1 8 96 160\n");
    Write(high / "hd/layouts.csv", "path,layout\nplayers/other.png,D1R_SHEET_V1 4 48 96\n");
    AssetStore isolated;
    isolated.mountLoose(low.string()); isolated.mountLoose(high.string());
    assert(isolated.readWithLayout(id, pairedImage, pairedLayout) && pairedLayout.empty());
    Write(high / "hd/layouts.csv", "path,layout\nplayers/0.png,D1R_SHEET_V1 8 50 100\n");
    assert(isolated.readWithLayout(id, pairedImage, pairedLayout) && pairedLayout.empty());
    AssetStore restarted;
    restarted.mountLoose(high.string());
    assert(restarted.readWithLayout(id, pairedImage, pairedLayout));
    assert(std::string(pairedLayout.begin(), pairedLayout.end()) == "D1R_SHEET_V1 8 50 100");
    fs::remove(high / id);
    assert(isolated.readWithLayout(id, pairedImage, pairedLayout));
    assert(std::string(pairedLayout.begin(), pairedLayout.end()) == "D1R_SHEET_V1 8 96 160");

    // Invalid/ambiguous CSVs fail as a unit; individual sidecars are ignored.
    for (const std::string &csv : {
             "wrong,header\nplayers/0.png,bad\n",
             "path,layout\n../escape.png,bad\n",
             "path,layout\nplayers/0.png,first\nPLAYERS/0.PNG,duplicate\n",
             "path,layout\n\"players/0.png,unclosed\n",
             "path,layout\nplayers/0.png,value,extra\n" }) {
        AssetStore invalid;
        auto bad = std::make_unique<TableProvider>(); bad->csv = csv;
        invalid.mount(std::move(bad));
        assert(invalid.readWithLayout(id, pairedImage, pairedLayout));
        assert(pairedLayout.empty());
    }

    {
        AssetStore gpuStore;
        auto table = std::make_unique<TableProvider>();
        table->csv = "path,layout\nplayers/0.png,D1R_SHEET_V1 8 48 96\n";
        // Separate loose synthetic provider includes manifest/pages and one CSV.
        Write(high / "hd/gpu.gpus", "synthetic gpu manifest");
        Write(high / "hd/layouts.csv", "path,layout\ngpu.png,D1R_SHEET_V1 8 48 96\n");
        auto owner=std::make_unique<LooseFileAssetProvider>(high.string());
        const AssetProvider *expectedOwner=owner.get();gpuStore.mount(std::move(owner));
        const AssetProvider *actualOwner=nullptr;
        assert(gpuStore.readWithLayout("hd/gpu.gpus",pairedImage,pairedLayout,&actualOwner));
        assert(actualOwner==expectedOwner);
        assert(std::string(pairedLayout.begin(),pairedLayout.end())=="D1R_SHEET_V1 8 48 96");
        actualOwner=expectedOwner;
        assert(!gpuStore.readWithLayout("hd/missing.gpus",pairedImage,pairedLayout,&actualOwner));
        assert(actualOwner==nullptr);
    }

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
