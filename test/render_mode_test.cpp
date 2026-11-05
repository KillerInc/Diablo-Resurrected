#include <SDL3/SDL.h>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include "options.h"
#include "reincarnated/hd_renderer.hpp"
#include "utils/paths.h"

static void Check(bool ok, const char *what)
{
    if (!ok) { std::fprintf(stderr, "FAIL: %s\n", what); std::exit(1); }
}

int main()
{
    using namespace devilution;
    Check(SDL_Init(0), "SDL init without audio/video");
    const auto root = std::filesystem::temp_directory_path()
        / ("d1r-render-mode-" + std::to_string(SDL_GetTicksNS()));
    std::filesystem::create_directory(root);
    paths::SetConfigPath(root.string());
    paths::SetPrefPath(root.string());
    paths::SetBasePath(root.string());
    LoadOptions();
    auto &option = GetOptions().Graphics.hdGraphics;
    Check(!*option, "missing setting defaults to Classic");
    option.SetValue(true);
    Check(reincarnated::GetRendererSwitch().usesHdRenderer(), "graphics toggle applies HD");
    SaveOptions();
    option.SetValue(false);
    LoadOptions();
    Check(*option, "saved HD setting survives reload");
    option.SetValue(false);
    Check(!reincarnated::GetRendererSwitch().usesHdRenderer(), "graphics toggle applies Classic");
    SaveOptions();
    option.SetValue(true);
    LoadOptions();
    Check(!*option, "saved Classic setting survives reload");
    Check(std::filesystem::equivalent(root.parent_path(), std::filesystem::temp_directory_path()), "cleanup boundary");
    std::filesystem::remove_all(root);
    SDL_Quit();
    std::puts("PASS: HD/Classic toggle callback, default mode and both saved-mode round trips");
}
