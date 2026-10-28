// Integration checks for provenance, streaming decode and the real compositor.
#include <array>
#include <algorithm>
#include <chrono>
#include <filesystem>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <iterator>
#include <stdexcept>
#include <source_location>
#include <SDL3/SDL.h>
#include <png.h>
#include "engine/palette.h"
#include "engine/render/clx_render.hpp"
#include "engine/render/light_render.hpp"
#include "engine/surface.hpp"
#include "game_mode.hpp"
#include "diablo.h"
#include "reincarnated/hd_renderer.hpp"
#include "reincarnated/raster_bridge.hpp"
#include "reincarnated/sheet_png.hpp"
#include "reincarnated/sheet_memory.hpp"
#include "utils/display.h"
#include "utils/endian_write.hpp"
namespace devilution {
extern "C" void SdlLogToFile(void *, int, SDL_LogPriority, const char *);
}

namespace {
void Check(bool condition, const std::source_location location = std::source_location::current()) { if (!condition) throw std::runtime_error("HD sheet check failed at line " + std::to_string(location.line())); }
std::vector<uint8_t> Png()
{
    // 1 column, 2 frames, 2x2 logical cells, 4x source density.
    std::vector<uint8_t> pixels(8 * 16 * 4);
    for (unsigned y = 0; y < 16; ++y) for (unsigned x = 0; x < 8; ++x) {
        const unsigned color = (y % 8 < 4 ? 2 : 0) + x / 4;
        const uint8_t colors[4][4] { {255,0,0,255}, {0,255,0,255}, {0,0,255,255}, {255,255,255,255} };
        std::memcpy(pixels.data() + (y * 8 + x) * 4, colors[color], 4);
    }
    png_image png {}; png.version = PNG_IMAGE_VERSION; png.width = 8; png.height = 16; png.format = PNG_FORMAT_RGBA;
    png_alloc_size_t size = 0;
    Check(png_image_write_to_memory(&png, nullptr, &size, 0, pixels.data(), 0, nullptr) != 0);
    std::vector<uint8_t> result(size);
    Check(png_image_write_to_memory(&png, result.data(), &size, 0, pixels.data(), 0, nullptr) != 0);
    result.resize(size);
    return result;
}
std::vector<uint8_t> SolidPng(unsigned width, unsigned height)
{
    // Stream synthetic fixtures: no giant source image or proprietary artwork.
    std::vector<uint8_t> bytes;
    auto *png = png_create_write_struct(PNG_LIBPNG_VER_STRING, nullptr, nullptr, nullptr);
    auto *info = png_create_info_struct(png);
    Check(png && info);
    png_set_write_fn(png, &bytes, [](png_structp p, png_bytep data, png_size_t count) {
        auto &out = *static_cast<std::vector<uint8_t> *>(png_get_io_ptr(p));
        out.insert(out.end(), data, data + count);
    }, nullptr);
    png_set_IHDR(png, info, width, height, 8, PNG_COLOR_TYPE_RGBA, PNG_INTERLACE_NONE,
        PNG_COMPRESSION_TYPE_DEFAULT, PNG_FILTER_TYPE_DEFAULT);
    png_write_info(png, info);
    std::vector<uint8_t> row(size_t(width) * 4, 255);
    for (unsigned y = 0; y < height; ++y) png_write_row(png, row.data());
    png_write_end(png, info);
    png_destroy_write_struct(&png, &info);
    return bytes;
}
std::vector<std::string> memoryWarnings;
void SDLCALL CaptureMemoryLog(void *, int, SDL_LogPriority, const char *message)
{
    if (std::strstr(message, "HD_PNG_WARNING") || std::strstr(message, "HD_MEMORY_WARNING"))
        memoryWarnings.emplace_back(message);
}
class LargeProvider final : public reincarnated::AssetProvider {
    std::vector<uint8_t> bytes = SolidPng(8192, 4098);
public:
    bool read(const std::string &id, reincarnated::AssetBytes &out) const override {
        if (id == "hd/plrgfx/warrior/wln/wlnst.png") { out = bytes; return true; }
        if (id == "hd/layouts.csv") {
            const std::string text = "path,layout\nplrgfx/warrior/wln/wlnst.png,D1R_SHEET_V1 1 2 3\n";
            out.assign(text.begin(), text.end()); return true;
        }
        return false;
    }
};
devilution::OwnedClxSpriteListOrSheet Sprites()
{
    using namespace devilution;
    auto bytes = std::make_unique<uint8_t[]>(40);
    WriteLE32(bytes.get(), 2);
    WriteLE32(bytes.get()+4, 16); WriteLE32(bytes.get()+8, 28); WriteLE32(bytes.get()+12, 40);
    for (unsigned offset : {16U,28U}) {
        WriteLE16(bytes.get()+offset, 6); WriteLE16(bytes.get()+offset+2, 2); WriteLE16(bytes.get()+offset+4, 2);
        const uint8_t pixels[] {254,128,129,254,130,131};
        std::memcpy(bytes.get()+offset+6, pixels, 6);
    }
    return reincarnated::AnnotateSheetSource(OwnedClxSpriteListOrSheet(std::move(bytes), 0), "plrgfx\\warrior\\wln\\wlnst");
}
class MemoryProvider final : public reincarnated::AssetProvider {
    std::vector<uint8_t> bytes = Png();
public:
    bool read(const std::string &id, reincarnated::AssetBytes &out) const override {
        if (id != "hd/plrgfx/warrior/wln/wlnst.png") return false;
        out = bytes; return true;
    }
};
class CanvasProvider final : public reincarnated::AssetProvider {
    std::string layout;
public:
    explicit CanvasProvider(std::string text) : layout(std::move(text)) {}
    bool read(const std::string &id, reincarnated::AssetBytes &out) const override {
        if (id == "hd/plrgfx/warrior/wln/wlnst.png") { out = Png(); return true; }
        if (id == "hd/layouts.csv") { const std::string csv="path,layout\nplrgfx/warrior/wln/wlnst.png,"+layout+"\n";out.assign(csv.begin(),csv.end()); return true; }
        return false;
    }
};
}

int main(int argc, char **argv)
{
    using namespace devilution;
    using namespace reincarnated;
    try {
        if (argc == 3) {
            const auto read = [](const char *path) {
                std::ifstream file(path,std::ios::binary);
                Check(bool(file));
                return std::vector<uint8_t>(std::istreambuf_iterator<char>(file),{});
            };
            SheetLayout privateLayout;
            SheetImage privateImage;
            Check(ParseSheetLayout(read(argv[2]),privateLayout));
            Check(DecodeSheetPng(read(argv[1]),SheetSource{"local attack test",8,16,128},privateImage,&privateLayout));
            Check(privateImage.logicalWidth==192 && privateImage.cellHeight/privateImage.density==192);
            Check(privateImage.anchorX==96 && privateImage.anchorY==160 && privateImage.density==2);
            std::puts("PASS: local expanded attack atlas streams at unchanged 2x retained density and explicit anchor");
        }
        auto sprites = Sprites();
        const auto sprite = sprites.list()[0];
        const auto *source = GetSheetSource(sprite);
        Check(source && source->columns == 1 && source->rows == 2 && source->width == 2);
        auto cloned = sprites.list().clone();
        Check(GetSheetSource(cloned[1]) == source);
        Check(LoadLE16(cloned[1].pixelData() - SheetHeaderSize + 16) == 1);
        std::array<uint8_t,256> translation;
        for (unsigned i=0;i<256;++i) translation[i]=static_cast<uint8_t>(i);
        translation[128]=129; translation[129]=130;
        ClxApplyTrans(cloned, translation.data());
        Check(cloned[0].pixelData()[1] == 129);
        Check(*(cloned[0].pixelData() - SheetHeaderSize + 18 + 128) == 129);
        ClxApplyTrans(cloned, translation.data());
        Check(*(cloned[0].pixelData() - SheetHeaderSize + 18 + 128) == 130);
        Check(sprite.pixelData()[1] == 128);

        SheetImage image;
        const auto png = Png();
        Check(DecodeSheetPng(png,*source,image));
        Check(image.width==4 && image.height==8 && image.cellWidth==4 && image.cellHeight==4 && image.density==2);
        Check(image.rgba[2] == 255); // top-left is blue, not vertically flipped
        Check(!DecodeSheetPng({png.begin(),png.begin()+png.size()/2},*source,image));
        auto wrong = *source; wrong.columns=3;
        Check(!DecodeSheetPng(png,wrong,image));
        SheetLayout canvas;
        const auto parse = [&](const std::string &text) { return ParseSheetLayout({text.begin(),text.end()},canvas); };
        Check(parse("D1R_SHEET_V1 2 2 3\n"));
        Check(DecodeSheetPng(png,*source,image,&canvas));
        Check(image.logicalWidth==4 && image.cellHeight/image.density==4 && image.anchorX==2 && image.anchorY==3);
        Check(!parse("D1R_SHEET_V1 3 2 3"));
        Check(!parse("D1R_SHEET_V1 2 -1 3"));
        Check(!parse("D1R_SHEET_V2 2 2 3"));
        Check(!parse("D1R_SHEET_V1 2 2 3 garbage"));
        Check(parse("D1R_SHEET_V1 2 5 3"));
        Check(!DecodeSheetPng(png,*source,image,&canvas)); // anchor outside the real canvas

        Check(MemoryTarget("8192", 4096) == size_t(8192) * MemoryMiB);
        Check(MemoryTarget("bad", 4096) == size_t(4096) * MemoryMiB);
        Check(MemoryTarget("0", 4096) == size_t(4096) * MemoryMiB);
        Check(MemoryWarningFlags(74,100)==0 && MemoryWarningFlags(75,100)==1);
        Check(MemoryWarningFlags(90,100)==3 && MemoryWarningFlags(100,100)==7);
        {
            FILE *log = std::tmpfile();
            Check(log != nullptr);
            SdlLogToFile(log, 0, SDL_LOG_PRIORITY_TRACE, "trace");
            SdlLogToFile(log, 0, SDL_LOG_PRIORITY_INFO, "info");
            SdlLogToFile(log, 0, SDL_LOG_PRIORITY_WARN, "warning");
            SdlLogToFile(log, 0, SDL_LOG_PRIORITY_CRITICAL, "critical");
            std::rewind(log);
            char text[256] {};
            const size_t count = std::fread(text, 1, sizeof(text)-1, log);
            std::fclose(log);
            Check(std::string(text,count)=="TRACE: trace\nINFO: info\nWARN: warning\nCRITICAL: critical\n");
        }
        SDL_LogOutputFunction oldLog;
        void *oldLogData;
        SDL_GetLogOutputFunction(&oldLog, &oldLogData);
        SDL_SetLogOutputFunction(CaptureMemoryLog, nullptr);
        const auto diagnosticPath = std::filesystem::temp_directory_path() /
            ("reincarnated-sheet-test-" + std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()) + ".log");
        Check(SDL_SetEnvironmentVariable(SDL_GetEnvironment(), "D1R_SHEET_LOG", diagnosticPath.string().c_str(), true));
        Check(SDL_SetEnvironmentVariable(SDL_GetEnvironment(), "D1R_SHEET_WARN_MB", "128", true));
        const SheetSource wideSource {"synthetic-wide",1,1,2};
        const auto wide = SolidPng(65544, 1);
        Check(parse("D1R_SHEET_V1 1 65540 1"));
        Check(DecodeSheetPng(wide,wideSource,image,&canvas));
        Check(image.width==65544 && image.anchorX==65540);
        Check(!memoryWarnings.empty() && memoryWarnings.back().find("dimension_over_65536=1")!=std::string::npos);

        Check(SDL_Init(0));
        // A target smaller than one sheet must evict others, never reject it.
        Check(SDL_SetEnvironmentVariable(SDL_GetEnvironment(), "D1R_SHEET_CACHE_MB", "1", true));
        Check(SDL_SetEnvironmentVariable(SDL_GetEnvironment(), "D1R_PROCESS_WARN_MB", "1", true));
        gnScreenWidth=8; gnScreenHeight=8;
        Palette.reset(SDL_CreatePalette(256));
        Check(bool(Palette));
        logical_palette.fill(SDL_Color{0,0,0,255});
        logical_palette[128]={255,0,0,255}; logical_palette[129]={0,255,0,255};
        logical_palette[130]={0,0,255,255}; logical_palette[131]={255,255,255,255};
        Check(SDL_SetPaletteColors(Palette.get(),logical_palette.data(),0,256));
        SDLSurfaceUniquePtr pal(SDL_CreateSurface(8,8,SDL_PIXELFORMAT_INDEX8));
        PalSurface=pal.get(); Check(SDL_SetSurfacePalette(PalSurface,Palette.get()));
        SDL_FillSurfaceRect(PalSurface,nullptr,0);
        Surface out(PalSurface);
        GetHdAssetStore().mount(std::make_unique<MemoryProvider>());
        GetRendererSwitch().setMode(RenderMode::HighDefinition);
        gbRunGame=true;
        BeginHdWorldFrame(2,0,0,8,8);
        ClxDraw(out,{0,3},sprite);
        Check(out[{0,3}]==128 && out[{1,2}]==131); // classic buffer remains exact
        EndHdWorldFrame();
        SDLSurfaceUniquePtr classic(SDL_ConvertSurface(PalSurface,SDL_PIXELFORMAT_RGBA32));
        auto *composed=ComposeHdFrame(classic.get());
        auto *top=static_cast<uint8_t*>(composed->pixels)+4*composed->pitch;
        auto *bottom=static_cast<uint8_t*>(composed->pixels)+7*composed->pitch;
        Check(top[2]==255 && top[0]==0); // logical top-left blue at 2x
        Check(bottom[0]==255 && bottom[1]==0); // bottom-left red
        ResetHdAssets();

        BeginHdWorldFrame(2,0,0,8,8);
        ClxDrawTRN(out,{0,3},sprite,translation.data());
        EndHdWorldFrame(); composed=ComposeHdFrame(classic.get());
        bottom=static_cast<uint8_t*>(composed->pixels)+7*composed->pitch;
        Check(bottom[0]==0 && bottom[1]==255); // vanilla translation, red->green
        ResetHdAssets();
        std::array<std::array<uint8_t,LightTableSize>,NumLightingLevels> tables;
        for (auto &table : tables) for (unsigned i=0;i<256;++i) table[i]=static_cast<uint8_t>(i);
        tables[1][128]=129;
        std::array<uint8_t,64> levels {}; levels.fill(1);
        Lightmap lighting(static_cast<uint8_t*>(PalSurface->pixels),levels,PalSurface->pitch,tables,tables[0].data(),tables.back().data());
        BeginHdWorldFrame(2,0,0,8,8);
        ClxDrawWithLightmap(out,{0,3},sprite,lighting);
        EndHdWorldFrame(); composed=ComposeHdFrame(classic.get());
        bottom=static_cast<uint8_t*>(composed->pixels)+7*composed->pitch;
        Check(bottom[0]==0 && bottom[1]==255);
        ResetHdAssets();
        BeginHdWorldFrame(2,0,0,8,8);
        ClxDrawBlended(out,{0,3},sprite);
        EndHdWorldFrame(); composed=ComposeHdFrame(classic.get());
        bottom=static_cast<uint8_t*>(composed->pixels)+7*composed->pitch;
        Check(bottom[0]==127 && bottom[1]==0);
        ResetHdAssets();
        BeginHdWorldFrame(2,0,0,8,8);
        ClxDraw(out,{0,3},sprite);
        out.SetPixel({0,3},131); // a later classic foreground covers the HD sprite
        EndHdWorldFrame(); composed=ComposeHdFrame(classic.get());
        bottom=static_cast<uint8_t*>(composed->pixels)+7*composed->pitch;
        Check(bottom[0]==255 && bottom[1]==255 && bottom[2]==255);
        ResetHdAssets();
        GetHdAssetStore().mount(std::make_unique<CanvasProvider>("D1R_SHEET_V1 2 2 3\n"));
        SDL_FillSurfaceRect(PalSurface,nullptr,0);
        BeginHdWorldFrame(1,0,0,8,8);
        ClxDraw(out,{2,4},sprite);
        Check(out[{1,2}]==0 && out[{2,4}]==128); // expanded HD pixels never enter the Classic buffer
        EndHdWorldFrame(); classic.reset(SDL_ConvertSurface(PalSurface,SDL_PIXELFORMAT_RGBA32));
        composed=ComposeHdFrame(classic.get());
        auto pixel = [&](int x,int y) { return static_cast<uint8_t*>(composed->pixels)+y*composed->pitch+x*4; };
        Check(pixel(1,2)[2]==255 && pixel(4,2)[0]==255); // larger than the original 2-pixel width
        Check(pixel(1,5)[0]==255 && pixel(4,5)[1]==255); // extra bottom canvas and anchor
        ResetHdAssets();
        SDL_FillSurfaceRect(PalSurface,nullptr,0);
        BeginHdWorldFrame(2,0,0,8,8);
        ClxDraw(out,{1,2},sprite);
        EndHdWorldFrame(); classic.reset(SDL_ConvertSurface(PalSurface,SDL_PIXELFORMAT_RGBA32));
        composed=ComposeHdFrame(classic.get());
        Check(pixel(0,0)[2]==255 && pixel(7,7)[1]==255); // same pivot at 2x
        ResetHdAssets();
        BeginHdWorldFrame(2,0,0,8,8);
        ClxDraw(out,{1,2},sprite);
        out.SetPixel({0,0},131); // later foreground covers extended pixels too
        EndHdWorldFrame(); composed=ComposeHdFrame(classic.get());
        Check(pixel(0,0)[0]==255 && pixel(0,0)[1]==255 && pixel(0,0)[2]==255);
        ResetHdAssets();
        BeginHdWorldFrame(2,0,0,8,8);
        ClxDraw(out,{0,0},sprite); // viewport clipping must retain the correct texture origin
        EndHdWorldFrame(); composed=ComposeHdFrame(classic.get());
        Check(pixel(0,0)[0]==255 && pixel(0,0)[2]==0);
        ResetHdAssets();
        GetHdAssetStore().mount(std::make_unique<CanvasProvider>("D1R_SHEET_V1 3 2 3"));
        BeginHdWorldFrame(1,0,0,8,8);
        Check(!HasHdSheet(sprite)); // malformed metadata takes the existing Classic fallback
        EndHdWorldFrame();
        ResetHdAssets();
        GetHdAssetStore().mount(std::make_unique<LargeProvider>());
        memoryWarnings.clear();
        BeginHdWorldFrame(1,0,0,8,8);
        Check(HasHdSheet(sprite)); // >128 MiB retained; >1 MiB cache target
        EndHdWorldFrame();
        Check(std::any_of(memoryWarnings.begin(), memoryWarnings.end(), [](const std::string &line) {
            return line.find("HD_PNG_WARNING")!=std::string::npos && line.find("flags=7")!=std::string::npos;
        }));
        Check(std::any_of(memoryWarnings.begin(), memoryWarnings.end(), [](const std::string &line) {
            return line.find("kind=sheet_cache flags=7")!=std::string::npos;
        }));
#ifdef _WIN32
        Check(std::any_of(memoryWarnings.begin(), memoryWarnings.end(), [](const std::string &line) {
            return line.find("kind=process_private_commit flags=7")!=std::string::npos;
        }));
#endif
        ResetHdAssets(); PalSurface=nullptr; Palette.reset(); SDL_Quit();
        SDL_SetLogOutputFunction(oldLog, oldLogData);
        {
            std::ifstream file(diagnosticPath);
            const std::string diagnostics(std::istreambuf_iterator<char>(file), {});
            Check(diagnostics.find("HD_PNG_WARNING")!=std::string::npos);
            Check(diagnostics.find("kind=sheet_cache flags=7")!=std::string::npos);
        }
        std::filesystem::remove(diagnosticPath);
        std::puts("PASS: provenance, translations, legacy/expanded decode, 1x/2x anchors, viewport clipping, invalid metadata fallback, Classic buffer, lighting, blending and foreground occlusion");
        return 0;
    } catch (const std::exception &e) { std::fprintf(stderr,"%s\n",e.what()); return 1; }
}
