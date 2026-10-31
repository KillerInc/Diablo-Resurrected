// Private offline extraction through the game's own read-only MPQ reader.
#include <algorithm>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include "mpq/mpq_reader.hpp"
int main(int argc, char **argv)
{
    try {
        if (argc != 4) throw std::runtime_error("Usage: extract_mpq_art ARCHIVE NAMES OUTPUT_NEW_DIRECTORY");
        auto archive = devilution::MpqArchive::Open(argv[1]);
        if (!archive) throw std::runtime_error(archive.error());
        const auto output = std::filesystem::absolute(argv[3]).lexically_normal();
        if (std::filesystem::exists(output)) throw std::runtime_error("Output must be a new directory");
        std::ifstream names(argv[2]);
        if (!names) throw std::runtime_error("Cannot open names list");
        std::filesystem::create_directories(output);
        unsigned files = 0, missing = 0;
        std::string name;
        while (std::getline(names, name)) {
            if (!name.empty() && name.back() == '\r') name.pop_back();
            if (name.empty()) continue;
            std::replace(name.begin(), name.end(), '\\', '/');
            const std::filesystem::path relative(name);
            if (relative.is_absolute() || relative.has_root_name()) throw std::runtime_error("Absolute archive path rejected");
            for (const auto &part : relative) if (part == "..") throw std::runtime_error("Archive traversal rejected");
            auto lookup = name;
            std::replace(lookup.begin(), lookup.end(), '/', '\\');
            if (!archive->HasFile(lookup)) { std::cout << "MISSING " << name << '\n'; ++missing; continue; }
            size_t size = 0; int32_t error = 0;
            auto bytes = archive->ReadFile(lookup, size, error);
            if (!bytes || error) throw std::runtime_error("Cannot read " + name);
            const auto destination = output / relative;
            std::filesystem::create_directories(destination.parent_path());
            std::ofstream file(destination, std::ios::binary);
            file.write(reinterpret_cast<const char *>(bytes.get()), size);
            if (!file) throw std::runtime_error("Cannot write " + destination.string());
            ++files;
            std::cout << "OK " << name << ' ' << size << '\n';
        }
        std::cout << "EXTRACTED files=" << files << " missing=" << missing << '\n';
        return missing ? 2 : 0;
    } catch (const std::exception &error) { std::cerr << error.what() << '\n'; return 1; }
}
