// Integration checks for provenance, streaming decode and the real compositor.
#include <array>
#include <cstdio>
#include <cstring>
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
#include "utils/display.h"
#include "utils/endian_write.hpp"

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
}

int main()
{
    using namespace devilution;
    using namespace reincarnated;
    try {
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

        Check(SDL_Init(0));
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
        ResetHdAssets(); PalSurface=nullptr; Palette.reset(); SDL_Quit();
        std::puts("PASS: provenance, cloning, translations, streamed decode/rejection, 2x anchoring, Classic buffer, lighting, blending and foreground occlusion");
        return 0;
    } catch (const std::exception &e) { std::fprintf(stderr,"%s\n",e.what()); return 1; }
}
