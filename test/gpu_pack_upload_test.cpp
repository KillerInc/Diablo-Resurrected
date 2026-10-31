// Upload every real compiled record with the actual runtime loader, one sheet
// at a time. No game saves, PNGs, audio subsystem or public captures are used.
#include <SDL3/SDL.h>
#include <cstdio>
#include <sstream>
#include <string>
#include "reincarnated/gpu_presenter.hpp"
#include "reincarnated/gpu_sprites.hpp"
#include "reincarnated/hd_renderer.hpp"

int main(int argc, char **argv)
{
    using namespace reincarnated;
    if (argc != 2 || !SDL_Init(SDL_INIT_VIDEO)) return 1;
    auto *window = SDL_CreateWindow("BC7 pack validation", 64, 64, SDL_WINDOW_HIDDEN);
    if (!window) return 1;
    InitializeGpuPresenter(window);
    GetHdAssetStore().mountLoose(argv[1]);
    size_t sheets = 0, pages = 0, bytes = 0;
    for (const char *prefix : {"hd/plrgfx/", "hd/monsters/", "hd/missiles/", "hd/objects/", "hd/towners/", "hd/levels/", "hd/ctrlpan/", "hd/data/", "hd/items/", "hd/ui_art/", "hd/gendata/"}) {
        for (const auto &path : GetHdAssetStore().listGpu(prefix)) {
            AssetBytes metadata, layout;
            if (!GetHdAssetStore().readGpuWithLayout(path, metadata, layout)) return 2;
            std::istringstream input(std::string(metadata.begin(), metadata.end()));
            std::string magic;
            unsigned density, columns, rows, width, height, count;
            if (!(input >> magic >> density >> columns >> rows >> width >> height >> count)) return 2;
            auto sheet = LoadGpuSheet(SheetSource{path, columns, rows, width});
            if (!sheet) { std::fprintf(stderr, "FAILED BC7 upload: %s\n", path.c_str()); return 3; }
            pages += sheet->pages.size(); bytes += sheet->bytes; ++sheets;
            sheet.reset(); ReleaseGpuPlayerSheets();
            if (GetGpuSpriteStats().sheets != 0) return 4;
            if (sheets % 50 == 0) { std::printf("Uploaded %zu sheets\n", sheets); std::fflush(stdout); }
        }
    }
    const auto uploads = GetGpuSpriteStats().uploads;
    DestroyGpuPresenter(); SDL_DestroyWindow(window); SDL_Quit();
    if (!sheets || uploads != pages) return 5;
    std::printf("PASS: real BC7 pack upload sheets=%zu pages=%zu bytes=%zu; bounded residency, no PNG input\n", sheets, pages, bytes);
}
