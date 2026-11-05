#pragma once
#include <cstdio>
#include <ctime>
#include <mutex>
#include "utils/file_util.h"
#include "utils/log.hpp"
#include "utils/paths.h"

namespace reincarnated {
inline std::mutex &SheetDiagnosticMutex() { static std::mutex mutex; return mutex; }
template <typename... Args>
void SheetWarning(std::string_view format, Args &&...args)
{
    const std::string message = devilution::detail::format(format, std::forward<Args>(args)...);
    const std::lock_guard<std::mutex> lock(SheetDiagnosticMutex());
    SDL_LogWarn(SDL_LOG_CATEGORY_APPLICATION, "%s", message.c_str());
    const char *configured = SDL_getenv("D1R_SHEET_LOG");
    const std::string path = configured ? configured : devilution::paths::ConfigPath() + "hd-sprite-loader.log";
    if (FILE *file = devilution::OpenFile(path.c_str(), "ab")) {
        std::fprintf(file, "%lld %s\n", static_cast<long long>(std::time(nullptr)), message.c_str());
        std::fclose(file);
    } else {
        static bool reported = false;
        if (!reported) SDL_LogWarn(SDL_LOG_CATEGORY_APPLICATION, "Cannot append HD sprite diagnostics: %s", path.c_str());
        reported = true;
    }
}
}
