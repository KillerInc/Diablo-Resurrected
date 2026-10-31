// Synthetic assets only: exercise terrain BC7, palette lighting and UI layers.
#include "controls/control_mode.hpp"
#include "engine/light_tables.hpp"
#include "engine/palette.h"
#include "engine/render/primitive_render.hpp"
#include "game_mode.hpp"
#include "levels/gendung.h"
#include "levels/reencode_dun_cels.hpp"
#include "options.h"
#include "reincarnated/gpu_presenter.hpp"
#include "reincarnated/gpu_sprites.hpp"
#include "reincarnated/gpu_terrain.hpp"
#include "reincarnated/hd_renderer.hpp"
#include "reincarnated/raster_bridge.hpp"
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
using namespace devilution;
using namespace reincarnated;
static void Check(bool ok, const char *what)
{
	if (!ok) {
		std::fprintf(stderr, "FAIL %s: %s\n", what, SDL_GetError());
		std::exit(1);
	}
}
int main(int argc, char **argv)
{
	Check(SDL_Init(SDL_INIT_VIDEO), "video");
	const bool direct = argc < 2 || std::strcmp(argv[1], "--legacy") != 0;
	SDL_SetEnvironmentVariable(SDL_GetEnvironment(), "D1R_GPU_TILE_COMMANDS", direct ? "1" : "0", true);
	SDL_SetEnvironmentVariable(SDL_GetEnvironment(), "D1R_GPU_INDEXED_PRESENT", direct ? "1" : "0", true);
	auto root = std::filesystem::temp_directory_path() / ("d1r-terrain-synthetic-" + std::to_string(SDL_GetTicksNS()));
	std::filesystem::create_directories(root / "hd/levels/towndata");
	std::filesystem::create_directories(root / "levels/towndata");
	const std::array<SDL_Color, 5> colors { { { 10, 20, 30, 255 }, { 120, 60, 20, 255 }, { 60, 30, 10, 255 }, { 0, 0, 200, 255 }, { 0, 200, 0, 255 } } };
	std::array<uint8_t, 768> raw {};
	for (unsigned i = 0; i < colors.size(); ++i) {
		raw[i * 3] = colors[i].r;
		raw[i * 3 + 1] = colors[i].g;
		raw[i * 3 + 2] = colors[i].b;
	}
	{
		std::ofstream f(root / "levels/towndata/town.pal", std::ios::binary);
		f.write(reinterpret_cast<char *>(raw.data()), raw.size());
	}
	const unsigned char block[] = { 32, 60, 158, 199, 163, 80, 0, 2, 174, 170, 170, 170, 86, 85, 85, 85 };
	{
		std::ofstream f(root / "hd/levels/towndata/town.p0.bc7", std::ios::binary);
		uint32_t dimensions[] = { 128, 128 };
		f.write(reinterpret_cast<char *>(dimensions), 8);
		for (int i = 0; i < 1024; ++i)
			f.write(reinterpret_cast<const char *>(block), 16);
	}
	{
		std::ofstream f(root / "hd/sprites.gpus");
		f << "D1R_GPU_INDEX_V1\nDEFAULTS 4 2 32 32\nSHEET levels/towndata/town.png 1 1 * * * *\ntown.p0.bc7 128 128\n0 0 0 128 128 0 0\n0 0 0 128 128 0 0\n";
	}
	const auto previous = std::filesystem::current_path();
	std::filesystem::current_path(root);
	paths::SetBasePath(root.string());
	paths::SetPrefPath(root.string());
	paths::SetAssetsPath(root.string() + "/");
	SDL_SetEnvironmentVariable(SDL_GetEnvironment(), "D1R_GPU_TERRAIN", "1", true);
	SDL_UnsetEnvironmentVariable(SDL_GetEnvironment(), "D1R_GPU_TERRAIN_NATIVE");
	SDL_SetEnvironmentVariable(SDL_GetEnvironment(), "D1R_FRAME_DUMP", root.string().c_str(), true);
	auto *window = SDL_CreateWindow("Synthetic terrain validation", 256, 256, SDL_WINDOW_HIDDEN);
	Check(window, "window");
	gnScreenWidth = gnScreenHeight = 128;
	InitializeGpuPresenter(window);
	gbRunGame = true;
	Palette.reset(SDL_CreatePalette(256));
	Check(bool(Palette), "palette");
	std::array<SDL_Color, 256> palette {};
	for (auto &c : palette)
		c.a = 255;
	std::copy(colors.begin(), colors.end(), palette.begin());
	Check(SDL_SetPaletteColors(Palette.get(), palette.data(), 0, 256), "palette colors");
	auto *pal = SDL_CreateSurface(128, 128, SDL_PIXELFORMAT_INDEX8);
	Check(pal, "indexed surface");
	PalSurface = pal;
	Check(SDL_SetSurfacePalette(pal, Palette.get()), "surface palette");
	for (auto &table : LightTables)
		for (unsigned i = 0; i < 256; ++i)
			table[i] = uint8_t(i);
	LightTables[1][1] = 2;
	FullyLitLightTable = LightTables[0].data();
	FullyDarkLightTable = LightTables[15].data();
	GetOptions().Graphics.perPixelLighting.SetValue(false);
	GetRendererSwitch().setMode(RenderMode::HighDefinition);
	leveltype = DTYPE_TOWN;
	std::array<std::byte, 2064> cel {};
	WriteLE32(cel.data(), 2);
	WriteLE32(cel.data() + 4, 16);
	WriteLE32(cel.data() + 8, 1040);
	WriteLE32(cel.data() + 12, 2064);
	std::memset(cel.data() + 16, 1, 1024);
	std::memset(cel.data() + 1040, 2, 1024);
	const std::array<std::pair<uint16_t, DunFrameInfo>, 2> frames { { { 1, { 0, TileType::Square, TileProperties::Solid } }, { 2, { 0, TileType::Square, TileProperties::Solid } } } };
	RegisterGpuTerrain(cel.data(), frames);
	std::vector<uint8_t> lights(size_t(pal->pitch) * 128, 0);
	Lightmap light(static_cast<uint8_t *>(pal->pixels), lights, pal->pitch, LightTables, FullyLitLightTable, FullyDarkLightTable);
	auto *classic = SDL_CreateSurface(128, 128, SDL_PIXELFORMAT_RGBA32);
	Check(classic, "classic canvas");
	SDL_FillSurfaceRect(classic, nullptr, SDL_MapSurfaceRGBA(classic, 10, 20, 30, 255));
	std::vector<uint8_t> dimLights(lights.size(), 1);
	Lightmap dim(static_cast<uint8_t *>(pal->pixels), dimLights, pal->pitch, LightTables, FullyLitLightTable, FullyDarkLightTable);
	unsigned expectedCaptures = 0;
	for (bool perPixel : { false, true }) {
		GetOptions().Graphics.perPixelLighting.SetValue(perPixel);
		for (int zoom : { 1, 2 }) {
			SDL_FillSurfaceRect(pal, nullptr, 0);
			BeginHdWorldFrame(zoom, 0, 0, 128, 100);
			Check(GpuTerrainActive(), "terrain active");
			RenderTileFrame(Surface(pal), light, { 8, 39 }, TileType::Square, reinterpret_cast<const uint8_t *>(cel.data() + 16), 32, MaskType::Solid, LightTables[0].data());
			Check(*Surface(pal).at(10, 10) == (direct ? 0 : 1), "HD terrain bypasses indexed painting");
			RenderTileFrame(Surface(pal), dim, { 16, 47 }, TileType::Square, reinterpret_cast<const uint8_t *>(cel.data() + 16), 32, MaskType::Transparent, LightTables[1].data());
			// Repeat a translucent layer: ordered integer averaging must remain stable.
			RenderTileFrame(Surface(pal), dim, { 24, 55 }, TileType::Square, reinterpret_cast<const uint8_t *>(cel.data() + 16), 32, MaskType::Transparent, LightTables[1].data());
			// The compiled art deliberately differs from this native frame's
			// palette index: HD must preserve its own color, not repaint native RGB.
			RenderTileFrame(Surface(pal), light, { 56, 39 }, TileType::Square, reinterpret_cast<const uint8_t *>(cel.data() + 1040), 32, MaskType::Solid, LightTables[0].data());
			EndHdWorldFrame();
			*Surface(pal).at(20 * zoom, 20 * zoom) = 3;
			MirrorOpaque(Surface(pal).at(20 * zoom, 20 * zoom), 1);
			*Surface(pal).at(21 * zoom, 21 * zoom) = 0;
			MirrorOpaque(Surface(pal).at(21 * zoom, 21 * zoom), 1);
			DrawHalfTransparentRectTo(Surface(pal), 12 * zoom, 12 * zoom, 1, 1, 4);
			*Surface(pal).at(12, 112) = 3;
			const SDL_Color uiColor { 0, 0, 200, 255 };
			std::memcpy(static_cast<uint8_t *>(classic->pixels) + 112 * classic->pitch + 12 * 4, &uiColor, 4);
			auto *composed = ComposeHdFrame(classic);
			Check(GpuTerrainReady(), "terrain ready");
			for (int i = 0; i < (expectedCaptures == 0 ? 50 : 100); ++i)
				PresentGpuFrame(composed);
			SDL_Surface *image = nullptr;
			std::filesystem::path newest;
			for (const auto &file : std::filesystem::directory_iterator(root))
				if (file.path().extension() == ".png") {
					newest = file.path();
					image = IMG_Load(newest.string().c_str());
				}
			Check(image && image->w == 256, "readback");
			Uint8 ur, ug, ub, ua;
			Check(SDL_ReadSurfacePixel(image, 25, 225, &ur, &ug, &ub, &ua) && ur == 0 && ug == 0 && ub == 200, "GPU palette expansion outside viewport");
			++expectedCaptures;
			auto expect = [&](int x, int y, int r, int g, int b) {Uint8 rr,gg,bb,aa;Check(SDL_ReadSurfacePixel(image,x*zoom*2+1,y*zoom*2+1,&rr,&gg,&bb,&aa),"pixel");if(std::abs(int(rr)-r)>3||std::abs(int(gg)-g)>3||std::abs(int(bb)-b)>3){std::fprintf(stderr,"zoom %d pixel %d,%d got %d,%d,%d expected %d,%d,%d\n",zoom,x,y,rr,gg,bb,r,g,b);Check(false,"terrain color");} };
			expect(10, 10, 120, 60, 20);
			expect(12, 12, 60, 130, 10);
			expect(20, 20, 0, 0, 200);
			expect(21, 21, 10, 20, 30);
			expect(22, 22, 90, 45, 15);
			expect(28, 28, 75, 37, 12);
			expect(2, 2, 10, 20, 30);
			expect(58, 10, 120, 60, 20);
			SDL_DestroySurface(image);
			std::filesystem::remove(newest);
			GetRendererSwitch().setMode(RenderMode::Classic);
			BeginHdWorldFrame(zoom, 0, 0, 128, 100);
			Check(!GpuTerrainReady(), "Classic clears frame");
			GetRendererSwitch().setMode(RenderMode::HighDefinition);
		}
	}
	Check(expectedCaptures == 4, "both lighting and zoom modes");
	ControlMode = ControlTypes::VirtualGamepad;
	BeginHdWorldFrame(1, 0, 0, 128, 100);
	Check(!GpuTerrainActive(), "virtual gamepad keeps compatible CPU canvas");
	ControlMode = ControlTypes::KeyboardAndMouse;

	Check(GetGpuSpriteStats().uploads == 1, "F10 retains terrain page");
	{
		GpuTerrainNativeCaptureScope capture;
		SDL_FillSurfaceRect(pal, nullptr, 0);
		BeginHdWorldFrame(1, 0, 0, 128, 100);
		RenderTileFrame(Surface(pal), light, { 8, 39 }, TileType::Square, reinterpret_cast<const uint8_t *>(cel.data() + 16), 32, MaskType::Solid, LightTables[0].data());
		Check(*Surface(pal).at(10, 10) == 1, "screenshot scope restores native indexed drawing");
		EndHdWorldFrame();
	}
	// A pack without this level's terrain must retain the old HD background.
	leveltype = DTYPE_HELL;
	RegisterGpuTerrain(cel.data(), frames);
	BeginHdWorldFrame(1, 0, 0, 128, 100);
	Check(!GpuTerrainActive(), "missing terrain fallback");
	RenderTileFrame(Surface(pal), light, { 8, 39 }, TileType::Square, reinterpret_cast<const uint8_t *>(cel.data() + 16), 32, MaskType::Solid, LightTables[0].data());
	EndHdWorldFrame();
	auto *fallback = ComposeHdFrame(classic);
	Uint8 r, g, b, a;
	Check(SDL_ReadSurfacePixel(fallback, 10, 10, &r, &g, &b, &a) && r == 120 && g == 60 && b == 20, "fallback preserves native pixels");
	// Indexed uploads must respect row pitch and recreate resources on resize.
	SDL_DestroySurface(pal);
	SDL_DestroySurface(classic);
	gnScreenWidth = 193;
	gnScreenHeight = 129;
	pal = SDL_CreateSurface(193, 129, SDL_PIXELFORMAT_INDEX8);
	Check(pal, "resized native canvas");
	PalSurface = pal;
	Check(SDL_SetSurfacePalette(pal, Palette.get()), "resized palette");
	SDL_FillSurfaceRect(pal, nullptr, 0);
	classic = SDL_CreateSurface(193, 129, SDL_PIXELFORMAT_RGBA32);
	Check(classic, "resized classic canvas");
	SDL_FillSurfaceRect(classic, nullptr, SDL_MapSurfaceRGBA(classic, 10, 20, 30, 255));
	std::vector<uint8_t> resizedLights(size_t(pal->pitch) * 129, 0);
	Lightmap resizedLight(static_cast<uint8_t *>(pal->pixels), resizedLights, pal->pitch, LightTables, FullyLitLightTable, FullyDarkLightTable);
	leveltype = DTYPE_TOWN;
	RegisterGpuTerrain(cel.data(), frames);
	BeginHdWorldFrame(1, 0, 0, 193, 100);
	RenderTileFrame(Surface(pal), resizedLight, { 8, 39 }, TileType::Square, reinterpret_cast<const uint8_t *>(cel.data() + 16), 32, MaskType::Solid, LightTables[0].data());
	EndHdWorldFrame();
	auto *resized = ComposeHdFrame(classic);
	for (int i = 0; i < 100; ++i)
		PresentGpuFrame(resized);
	SDL_Surface *resizedImage = nullptr;
	for (const auto &file : std::filesystem::directory_iterator(root))
		if (file.path().extension() == ".png") resizedImage = IMG_Load(file.path().string().c_str());
	Check(resizedImage, "resized GPU readback");
	Uint8 rr, rg, rb, ra;
	Check(SDL_ReadSurfacePixel(resizedImage, 16, 16, &rr, &rg, &rb, &ra) && std::abs(int(rr) - 120) <= 3 && std::abs(int(rg) - 60) <= 3 && std::abs(int(rb) - 20) <= 3, "resized terrain alignment");
	SDL_DestroySurface(resizedImage);
	GetRendererSwitch().setMode(RenderMode::Classic);
	BeginHdWorldFrame(1, 0, 0, 193, 100);
	for (int i = 0; i < 100; ++i)
		PresentGpuFrame(classic);
	SDL_Surface *classicImage = nullptr;
	for (const auto &file : std::filesystem::directory_iterator(root))
		if (file.path().filename().string().find("-Classic.png") != std::string::npos) classicImage = IMG_Load(file.path().string().c_str());
	Check(classicImage && classicImage->w == 193 && classicImage->h == 129, "resized Classic capture");
	Check(SDL_ReadSurfacePixel(classicImage, 190, 125, &rr, &rg, &rb, &ra) && rr == 10 && rg == 20 && rb == 30, "odd-width Classic row pitch");
	SDL_DestroySurface(classicImage);
	ResetHdAssets();
	SDL_DestroySurface(classic);
	PalSurface = nullptr;
	SDL_DestroySurface(pal);
	Palette.reset();
	DestroyGpuPresenter();
	SDL_DestroyWindow(window);
	SDL_Quit();
	std::filesystem::current_path(previous);
	Check(std::filesystem::equivalent(root.parent_path(), std::filesystem::temp_directory_path()), "cleanup boundary");
	std::filesystem::remove_all(root);
	std::puts("PASS: terrain BC7, palette lighting, ordered wall blends, opaque/translucent UI, zoom, Classic/HD reset");
}
