// Owned synthetic pixels only: native UI, HD PCX blocks, clipping, TRN and fades.
#include "controls/control_mode.hpp"
#include "engine/palette.h"
#include "engine/render/clx_render.hpp"
#include "game_mode.hpp"
#include "reincarnated/gpu_presenter.hpp"
#include "reincarnated/gpu_sprites.hpp"
#include "reincarnated/gpu_ui.hpp"
#include "reincarnated/hd_renderer.hpp"
#include "reincarnated/sheet_source.hpp"
#include "utils/display.h"
#include "utils/endian_write.hpp"
#include "utils/paths.h"
#include <SDL3/SDL.h>
#include <SDL3_image/SDL_image.h>
#include <array>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <vector>
using namespace devilution;
using namespace reincarnated;
static void Check(bool ok, const char *what)
{
	if (!ok) {
		std::fprintf(stderr, "FAIL %s: %s\n", what, SDL_GetError());
		std::exit(1);
	}
}
static OwnedClxSpriteListOrSheet Make(unsigned w, unsigned h, unsigned frames, bool pcx, uint8_t color = 1)
{
	std::vector<uint8_t> data(4 * (frames + 2));
	WriteLE32(data.data(), frames);
	for (unsigned frame = 0; frame < frames; ++frame) {
		const unsigned offset = unsigned(data.size());
		WriteLE32(data.data() + 4 * (frame + 1), offset);
		data.resize(offset + 6);
		WriteLE16(data.data() + offset, 6);
		WriteLE16(data.data() + offset + 2, w);
		WriteLE16(data.data() + offset + 4, h);
		for (int y = int(h) - 1; y >= 0; --y)
			for (unsigned x = 0; x < w;) {
				const unsigned end = std::min({ w, x + 63, ((x / 128) + 1) * 128 });
				data.push_back(uint8_t(0xBF - (end - x)));
				data.push_back(pcx ? uint8_t((x / 128) * 2 + (frame * h + y) / 128 + 1) : color);
				x = end;
			}
	}
	WriteLE32(data.data() + 4 * (frames + 1), unsigned(data.size()));
	auto owned = std::make_unique<uint8_t[]>(data.size());
	std::memcpy(owned.get(), data.data(), data.size());
	return OwnedClxSpriteListOrSheet(std::move(owned), 0);
}
int main()
{
	Check(SDL_Init(SDL_INIT_VIDEO), "video");
	auto root = std::filesystem::temp_directory_path() / ("d1r-ui-synthetic-" + std::to_string(SDL_GetTicksNS()));
	Check(!std::filesystem::exists(root), "fresh synthetic directory");
	std::filesystem::create_directories(root / "hd/ui_art");
	std::filesystem::create_directories(root / "hd/ctrlpan");
	const unsigned char blocks[4][16] = { { 2, 158, 231, 121, 207, 243, 60, 69, 81, 20, 148, 36, 73, 146, 36, 73 }, { 8, 0, 0, 0, 0, 153, 76, 38, 3, 0, 0, 0, 172, 170, 170, 170 }, { 8, 0, 0, 0, 0, 0, 0, 0, 144, 201, 100, 50, 172, 170, 170, 170 }, { 8, 144, 201, 100, 50, 153, 76, 38, 3, 0, 0, 0, 172, 170, 170, 170 } };
	for (unsigned i = 0; i < 4; ++i) {
		std::ofstream f(root / ("hd/ui_art/test.p" + std::to_string(i) + ".bc7"), std::ios::binary);
		uint32_t dimensions[] = { 512, 512 };
		f.write(reinterpret_cast<char *>(dimensions), 8);
		for (unsigned j = 0; j < 16384; ++j)
			f.write(reinterpret_cast<const char *>(blocks[i]), 16);
	}
	{
		std::ofstream f(root / "hd/ctrlpan/test.p0.bc7", std::ios::binary);
		uint32_t dimensions[] = { 16, 16 };
		f.write(reinterpret_cast<char *>(dimensions), 8);
		for (unsigned j = 0; j < 16; ++j)
			f.write(reinterpret_cast<const char *>(blocks[0]), 16);
	}
	{
		std::ofstream f(root / "hd/sprites.gpus");
		f << "D1R_GPU_INDEX_V1\nDEFAULTS 4 1 4 4\nSHEET ctrlpan/test.png 1 1 * * * *\ntest.p0.bc7 16 16\n0 0 0 16 16 0 0\nSHEET ui_art/test.png 2 4 * 2 128 128\n";
		for (unsigned i = 0; i < 4; ++i)
			f << "test.p" << i << ".bc7 512 512\n";
		for (unsigned i = 0; i < 4; ++i)
			f << i << " 0 0 512 512 0 0\n";
	}
	auto previous = std::filesystem::current_path();
	std::filesystem::current_path(root);
	paths::SetBasePath(root.string());
	paths::SetPrefPath(root.string());
	paths::SetAssetsPath(root.string() + "/");
	auto *window = SDL_CreateWindow("Synthetic UI", 800, 360, SDL_WINDOW_HIDDEN);
	Check(window, "window");
	gnScreenWidth = 400;
	gnScreenHeight = 180;
	InitializeGpuPresenter(window);
	ControlMode = ControlTypes::KeyboardAndMouse;
	std::array<SDL_Color, 256> colors {};
	for (auto &color : colors)
		color.a = 255;
	colors[0] = { 10, 20, 30, 255 };
	colors[1] = { 120, 60, 20, 255 };
	colors[2] = { 0, 200, 0, 255 };
	colors[3] = { 0, 0, 200, 255 };
	colors[4] = { 200, 200, 0, 255 };
	logical_palette = colors;
	Palette.reset(SDL_CreatePalette(256));
	Check(SDL_SetPaletteColors(Palette.get(), colors.data(), 0, 256), "palette");
	auto *pal = SDL_CreateSurface(400, 180, SDL_PIXELFORMAT_INDEX8);
	PalSurface = pal;
	Check(SDL_SetSurfacePalette(pal, Palette.get()), "native palette");
	SDL_FillSurfaceRect(pal, nullptr, 0);
	auto *base = SDL_CreateSurface(400, 180, SDL_PIXELFORMAT_RGBA32);
	SDL_FillSurfaceRect(base, nullptr, SDL_MapSurfaceRGBA(base, 10, 20, 30, 255));
	auto pcx = AnnotateSheetSource(Make(160, 120, 2, true), "ui_art/test", true);
	auto cel = AnnotateSheetSource(Make(4, 4, 1, false), "ctrlpan/test");
	auto green = Make(4, 4, 1, false, 2);
	auto zero = Make(4, 4, 1, false, 0);
	auto *backing = SDL_CreateSurface(8, 8, SDL_PIXELFORMAT_INDEX8);
	SDL_FillSurfaceRect(backing, nullptr, 0);
	ClxDraw(Surface(backing), { 2, 5 }, cel.list()[0]);
	*Surface(backing).at(3, 3) = 4;
	GetRendererSwitch().setMode(RenderMode::HighDefinition);
	gbRunGame = true;
	BeginHdUiFrame();
	Check(GpuUiPhase(), "GPU UI phase");
	ClxDraw(Surface(pal), { 10, 129 }, pcx.list()[0]);
	BeginHdUiFrame(); // A second batch belongs to this same unpresented UI frame.
	ClxDraw(Surface(pal), { 210, 129 }, pcx.list()[1]);
	ClxDrawOutline(Surface(pal), 3, { 200, 73 }, cel.list()[0]);
	ClxDraw(Surface(pal), { 200, 73 }, green.list()[0]);
	ClxDrawBlended(Surface(pal), { 20, 23 }, green.list()[0]);
	ClxDraw(Surface(pal), { 25, 23 }, zero.list()[0]);
	std::array<uint8_t, 256> trn;
	for (unsigned i = 0; i < 256; ++i)
		trn[i] = uint8_t(i);
	trn[1] = 3;
	ClxDrawTRN(Surface(pal), { 30, 23 }, cel.list()[0], trn.data());
	Surface(pal).BlitFrom(Surface(backing), SDL_Rect { 2, 2, 4, 4 }, { 180, 50 });
	ClxDraw(Surface(pal).subregion(180, 80, 2, 2), { -1, 2 }, cel.list()[0]);
	std::array<uint8_t, 256> tint;
	for (unsigned i = 0; i < 256; ++i)
		tint[i] = uint8_t(i);
	tint[1] = 4;
	Check(TranslateGpuUiRect(Surface(pal), { 50, 50, 6, 6 }, tint.data()), "GPU inventory-style palette tint");
	SaveGpuUiScene();
	DrawGpuUiRect(Surface(pal), 14, 14, 4, 4, 3);
	RestoreGpuUiScene();
	Check(*Surface(pal).at(20, 20) == 0, "UI sprites bypass indexed painting");
	Check(SDL_SetEnvironmentVariable(SDL_GetEnvironment(), "D1R_FRAME_DUMP", root.string().c_str(), true), "capture");
	auto *surface = ComposeHdFrame(base);
	for (int i = 0; i < 50; ++i)
		PresentGpuFrame(surface);
	auto image = [&]() {SDL_Surface *result=nullptr;for(auto &entry:std::filesystem::directory_iterator(root))if(entry.path().extension()==".png")result=IMG_Load(entry.path().string().c_str());return result; };
	SDL_Surface *read = image();
	Check(read, "UI readback");
	auto expect = [&](int x, int y, int r, int g, int b) {Uint8 rr,gg,bb,aa;Check(SDL_ReadSurfacePixel(read,x*2+1,y*2+1,&rr,&gg,&bb,&aa),"pixel");if(std::abs(int(rr)-r)>3||std::abs(int(gg)-g)>3||std::abs(int(bb)-b)>3){std::fprintf(stderr,"at %d,%d got %u,%u,%u expected %d,%d,%d\n",x,y,rr,gg,bb,r,g,b);Check(false,"UI colour/order");} };
	expect(15, 15, 120, 60, 20);
	expect(51, 51, 200, 200, 0);
	expect(49, 51, 120, 60, 20);
	expect(145, 15, 0, 0, 200);
	expect(215, 15, 120, 60, 20);
	expect(215, 25, 0, 200, 0);
	expect(345, 15, 0, 0, 200);
	expect(345, 25, 200, 200, 0);
	expect(199, 70, 0, 0, 200);
	expect(200, 70, 0, 200, 0);
	expect(21, 21, 60, 130, 10);
	expect(26, 21, 10, 20, 30);
	expect(31, 21, 0, 0, 200);
	expect(180, 50, 120, 60, 20);
	expect(181, 51, 200, 200, 0);
	expect(180, 80, 120, 60, 20);
	expect(182, 80, 10, 20, 30);
	const auto uploads = GetGpuUiStats().uploads;
	Check(GetGpuUiStats().hdDraws >= 5, "HD CEL and PCX resources used");
	SDL_DestroySurface(read);
	for (auto &entry : std::filesystem::directory_iterator(root))
		if (entry.path().extension() == ".png") std::filesystem::remove(entry.path());
	auto faded = colors;
	for (auto &color : faded) {
		color.r /= 2;
		color.g /= 2;
		color.b /= 2;
	}
	Check(SDL_SetPaletteColors(Palette.get(), faded.data(), 0, 256), "fade after queue");
	for (int i = 0; i < 100; ++i)
		PresentGpuFrame(surface);
	read = image();
	Check(read, "fade readback");
	expect(15, 15, 60, 30, 10);
	expect(345, 25, 100, 100, 0);
	expect(31, 21, 0, 0, 100);
	Check(GetGpuUiStats().uploads == uploads, "warm UI texture retention");
	SDL_DestroySurface(read);
	SDL_SetPaletteColors(Palette.get(), colors.data(), 0, 256);
	for (auto &entry : std::filesystem::directory_iterator(root))
		if (entry.path().extension() == ".png") std::filesystem::remove(entry.path());
	ClxDraw(Surface(backing), { 2, 5 }, green.list()[0]);
	BeginHdUiFrame();
	Check(!PrepareGpuUiHudLayer(180, 140, 60, 6), "new retained HUD invalid");
	for (unsigned i = 0; i < 5; ++i) {
		Check(BeginGpuUiHudComponent(i, false), "initialize HUD component");
		DrawGpuUiRect(Surface(pal), 180 + int(i) * 10, 140, 6, 6, 1);
		EndGpuUiHudComponent(i);
	}
	const auto cachedUploads = GetGpuUiStats().uploads;
	BeginHdUiFrame(true);
	Check(PrepareGpuUiHudLayer(180, 140, 60, 6), "retained HUD valid");
	for (unsigned i = 0; i < 5; ++i)
		Check(!BeginGpuUiHudComponent(i, false), "unchanged HUD replays cached commands");
	Surface(pal).BlitFrom(Surface(backing), SDL_Rect { 2, 2, 4, 4 }, { 180, 50 });
	surface = ComposeHdFrame(base);
	for (int i = 0; i < 100; ++i)
		PresentGpuFrame(surface);
	read = image();
	Check(read, "cached HUD readback");
	expect(181, 141, 120, 60, 20);
	expect(181, 51, 0, 200, 0);
	Check(GetGpuUiStats().uploads == cachedUploads + 1, "static backing edits invalidate one native texture");
	SDL_DestroySurface(read);
	for (auto &entry : std::filesystem::directory_iterator(root))
		if (entry.path().extension() == ".png") std::filesystem::remove(entry.path());
	BeginHdUiFrame();
	for (unsigned i = 0; i < 5; ++i) {
		bool rebuild = BeginGpuUiHudComponent(i, i == 1);
		Check(rebuild == (i == 1), "only dirty HUD component rebuilds");
		if (rebuild) {
			DrawGpuUiRect(Surface(pal), 190, 140, 6, 6, 3);
			EndGpuUiHudComponent(i);
		}
	}
	surface = ComposeHdFrame(base);
	for (int i = 0; i < 100; ++i)
		PresentGpuFrame(surface);
	read = image();
	Check(read, "dirty HUD readback");
	expect(181, 141, 120, 60, 20);
	expect(191, 141, 0, 0, 200);
	SDL_DestroySurface(read);
	GetRendererSwitch().setMode(RenderMode::Classic);
	BeginHdUiFrame();
	Check(!GpuUiPhase(), "Classic UI fallback");
	ClxDraw(Surface(pal), { 0, 3 }, cel.list()[0]);
	Check(*Surface(pal).at(0, 0) == 1, "Classic draws indexed UI");
	BeginGpuSpriteFrame();
	SDL_DestroySurface(backing);
	SDL_DestroySurface(base);
	SDL_DestroySurface(pal);
	PalSurface = nullptr;
	DestroyGpuPresenter();
	SDL_DestroyWindow(window);
	SDL_Quit();
	std::filesystem::current_path(previous);
	Check(std::filesystem::canonical(root).parent_path() == std::filesystem::canonical(std::filesystem::temp_directory_path()), "temporary cleanup boundary");
	std::filesystem::remove_all(root);
	std::puts("PASS: GPU UI native indices/zero/TRN, HD CEL/PCX frame-block mapping, localized backing pixels, clips, blends, palette fade, warm cache and Classic fallback");
}
