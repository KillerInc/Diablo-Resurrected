#include "asset_provider.hpp"

#include <filesystem>
#include <algorithm>
#include <cstdio>
#include <fstream>
#include <limits>
#include <mutex>
#include <sstream>
#include <utility>
#include <unordered_set>

namespace reincarnated {

namespace {
// Keep the existing bound on non-PNG resources. PNG sizes are diagnosed by
// the sheet loader instead of being rejected by an arbitrary byte budget.
constexpr std::uintmax_t MaxLooseAssetBytes = 256ULL * 1024ULL * 1024ULL;

std::string LayoutKey(std::string key)
{
    for (char &c : key) {
        if (c >= 'A' && c <= 'Z') c += 'a' - 'A';
    }
    return key;
}

// Two CSV fields per physical line. Quoted paths, escaped quotes, UTF-8 BOM,
// CRLF and LF are supported; layout values never need embedded newlines.
bool CsvFields(const std::string &line, std::vector<std::string> &fields)
{
    size_t pos = 0;
    while (true) {
        std::string field;
        if (pos < line.size() && line[pos] == '"') {
            ++pos;
            bool closed = false;
            while (pos < line.size()) {
                const char c = line[pos++];
                if (c != '"') { field += c; continue; }
                if (pos < line.size() && line[pos] == '"') {
                    field += '"'; ++pos;
                } else { closed = true; break; }
            }
            if (!closed || (pos < line.size() && line[pos] != ',')) return false;
        } else {
            while (pos < line.size() && line[pos] != ',') {
                if (line[pos] == '"') return false;
                field += line[pos++];
            }
        }
        fields.push_back(std::move(field));
        if (pos == line.size()) return fields.size() == 2;
        if (fields.size() >= 2) return false;
        ++pos;
    }
}

bool ParseLayoutTable(const AssetBytes &bytes,
    std::unordered_map<std::string, AssetBytes> &rows)
{
    std::string text(bytes.begin(), bytes.end());
    if (text.compare(0, 3, "\xEF\xBB\xBF") == 0) text.erase(0, 3);
    std::istringstream input(text);
    std::string line;
    bool header = false;
    while (std::getline(input, line)) {
        if (!line.empty() && line.back() == '\r') line.pop_back();
        if (line.empty()) continue;
        std::vector<std::string> fields;
        if (!CsvFields(line, fields)) return false;
        if (!header) {
            if (fields[0] != "path" || fields[1] != "layout") return false;
            header = true;
            continue;
        }
        if (!IsSafeAssetId(fields[0]) || fields[1].empty() || fields[1].size() > 256)
            return false;
        for (unsigned char c : fields[1]) {
            if (c < 32 && c != '\t') return false;
        }
        if (!rows.emplace(LayoutKey(fields[0]),
                AssetBytes(fields[1].begin(), fields[1].end())).second) return false;
    }
    return header;
}
}

bool IsSafeAssetId(const std::string &id) noexcept
{
    if (id.empty() || id.size() > 1024 || id.front() == '/')
        return false;
    // Canonical asset IDs only: no Windows separators, drives, embedded NUL,
    // empty segments, or parent/current-directory traversals.
    size_t start = 0;
    for (size_t i = 0; i <= id.size(); ++i) {
        if (i < id.size()) {
            const unsigned char c = static_cast<unsigned char>(id[i]);
            if (c == '\\' || c == ':' || c < 32)
                return false;
            if (id[i] != '/')
                continue;
        }
        if (i == start)
            return false;
        const size_t length = i - start;
        if ((length == 1 && id[start] == '.')
            || (length == 2 && id[start] == '.' && id[start + 1] == '.'))
            return false;
        start = i + 1;
    }
    return true;
}

LooseFileAssetProvider::LooseFileAssetProvider(std::string root)
    : root_(std::move(root))
{
}

bool LooseFileAssetProvider::read(const std::string &assetId, AssetBytes &bytes) const
{
    if (!IsSafeAssetId(assetId))
        return false;

    const std::filesystem::path filename =
        std::filesystem::u8path(root_.empty() ? "." : root_) /
        std::filesystem::u8path(assetId);
    std::ifstream input(filename, std::ios::in | std::ios::binary | std::ios::ate);
    if (!input)
        return false;
    const std::streampos fileSize = input.tellg();
    const size_t n = assetId.size();
    const bool png = n >= 4 && assetId[n-4] == '.'
        && (assetId[n-3] == 'p' || assetId[n-3] == 'P')
        && (assetId[n-2] == 'n' || assetId[n-2] == 'N')
        && (assetId[n-1] == 'g' || assetId[n-1] == 'G');
    if (fileSize <= 0 || (!png && static_cast<std::uintmax_t>(fileSize) > MaxLooseAssetBytes))
        return false;
    if (fileSize > std::numeric_limits<std::streamsize>::max()
        || static_cast<std::uintmax_t>(fileSize) > AssetBytes{}.max_size())
        return false;

    AssetBytes contents(static_cast<size_t>(fileSize));
    input.seekg(0, std::ios::beg);
    if (!input.read(reinterpret_cast<char *>(contents.data()), static_cast<std::streamsize>(fileSize)))
        return false;
    bytes = std::move(contents);
    return true;
}

void AssetStore::mount(std::unique_ptr<AssetProvider> provider)
{
    if (provider != nullptr)
        providers_.push_back(std::move(provider));
}

std::vector<std::string> LooseFileAssetProvider::list(const std::string &prefix) const
{
    std::string directory = prefix;
    if (!directory.empty() && directory.back() == '/') directory.pop_back();
    if (!IsSafeAssetId(directory)) return {};
    const auto base = std::filesystem::u8path(root_.empty() ? "." : root_);
    std::error_code error;
    std::filesystem::recursive_directory_iterator it(base / std::filesystem::u8path(directory),
        std::filesystem::directory_options::skip_permission_denied, error), end;
    std::vector<std::string> result;
    while (!error && it != end) {
        if (it->is_regular_file(error)) {
            const auto id = it->path().lexically_relative(base).generic_string();
            if (IsSafeAssetId(id)) result.push_back(id);
        }
        it.increment(error);
    }
    return result;
}

std::vector<std::string> AssetStore::list(const std::string &prefix) const
{
    std::string directory = prefix;
    if (!directory.empty() && directory.back() == '/') directory.pop_back();
    if (!IsSafeAssetId(directory)) return {};
    directory += '/';
    std::unordered_set<std::string> seen;
    std::vector<std::string> result;
    for (auto it = providers_.rbegin(); it != providers_.rend(); ++it) {
        for (const auto &id : (*it)->list(directory)) {
            if (!IsSafeAssetId(id) || id.compare(0, directory.size(), directory) != 0) continue;
            if (seen.insert(LayoutKey(id)).second) result.push_back(id);
        }
    }
    std::sort(result.begin(), result.end());
    return result;
}

void AssetStore::mountFallback(std::unique_ptr<AssetProvider> provider)
{
    if (provider != nullptr)
        providers_.insert(providers_.begin(), std::move(provider));
}

void AssetStore::mountLoose(std::string root)
{
    mount(std::make_unique<LooseFileAssetProvider>(std::move(root)));
}

bool AssetStore::read(const std::string &assetId, AssetBytes &bytes) const
{
    bytes.clear();
    if (!IsSafeAssetId(assetId))
        return false;
    for (auto it = providers_.rbegin(); it != providers_.rend(); ++it) {
        if ((*it)->read(assetId, bytes))
            return true;
        bytes.clear();
    }
    return false;
}

bool AssetStore::readWithLayout(const std::string &assetId,
    AssetBytes &bytes, AssetBytes &sidecar, const AssetProvider **provider) const
{
    bytes.clear();
    sidecar.clear();
    if (provider) *provider = nullptr;
    if (!IsSafeAssetId(assetId))
        return false;

    for (auto it = providers_.rbegin(); it != providers_.rend(); ++it) {
        if (!(*it)->read(assetId, bytes)) {
            bytes.clear();
            continue;
        }
        if (provider) *provider = it->get();
        std::string key = LayoutKey(assetId);
        if (key.size() > 5 && key.substr(key.size()-5) == ".gpus") key = key.substr(0,key.size()-5) + ".png";
        if (key.compare(0, 3, "hd/") == 0) {
            const auto &rows = layoutRows(**it);
            const auto row = rows.find(key.substr(3));
            if (row != rows.end()) {
                sidecar = row->second;
                return true;
            }
        }
        return true;
    }
    return false;
}

const AssetStore::LayoutRows &AssetStore::layoutRows(const AssetProvider &provider) const
{
    static std::mutex tableMutex;
    const std::lock_guard<std::mutex> lock(tableMutex);
    auto result = layoutTables_.try_emplace(&provider);
    if (result.second) {
        AssetBytes table;
        if (provider.read("hd/layouts.csv", table)) {
            if (!ParseLayoutTable(table, result.first->second)) {
                result.first->second.clear();
                std::fputs("HD_LAYOUT_CSV: invalid hd/layouts.csv; using default alignment until restart\n", stderr);
            } else {
                std::fprintf(stderr, "HD_LAYOUT_CSV: loaded rows=%zu cache=process-lifetime\n", result.first->second.size());
            }
        }
    }
    return result.first->second;
}

} // namespace reincarnated
