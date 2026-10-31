// Independently render original tile frames with the actual engine decoder.
#include <SDL3/SDL.h>
#include <array>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <stdexcept>
#include <vector>
#include "engine/render/dun_render.hpp"
#include "levels/reencode_dun_cels.hpp"
#include "utils/endian_read.hpp"
using namespace devilution;
static std::vector<std::byte> Read(const char *name) {
    std::ifstream file(name,std::ios::binary|std::ios::ate);
    if (!file) throw std::runtime_error("Cannot read input");
    std::vector<std::byte> bytes(size_t(file.tellg()));file.seekg(0);
    file.read(reinterpret_cast<char*>(bytes.data()),bytes.size());return bytes;
}
int main(int argc,char **argv) { try {
    if(argc!=4)throw std::runtime_error("Usage: verify_tile_export CEL MIN NEW_REFERENCE_BINARY");
    if(std::filesystem::exists(argv[3]))throw std::runtime_error("Reference output already exists");
    auto bytes=Read(argv[1]);auto min=Read(argv[2]);
    std::map<uint16_t,TileType> types;
    for(size_t i=0;i<min.size();i+=2){auto word=LoadLE16(min.data()+i);if(!word)continue;
        LevelCelBlock block{word};const auto [it,inserted]=types.emplace(block.frame(),block.type());
        if(!inserted&&it->second!=block.type())throw std::runtime_error("Conflicting tile shape");}
    std::vector<std::pair<uint16_t,DunFrameInfo>> info;
    for(auto [frame,type]:types)info.push_back({frame,{0,type,TileProperties::Solid}});
    auto cel=std::make_unique<std::byte[]>(bytes.size());std::memcpy(cel.get(),bytes.data(),bytes.size());
    ReencodeDungeonCels(cel,info);
    auto *surface=SDL_CreateSurface(32,32,SDL_PIXELFORMAT_INDEX8);
    if(!surface)throw std::runtime_error(SDL_GetError());
    std::array<std::array<uint8_t,LightTableSize>,NumLightingLevels> tables{};
    for(auto &table:tables)for(unsigned i=0;i<256;++i)table[i]=uint8_t(i);
    std::vector<uint8_t> lights(size_t(surface->pitch)*32,0);
    Surface out(surface);Lightmap lightmap(static_cast<const uint8_t*>(surface->pixels),lights,surface->pitch,tables,tables[0].data(),tables.back().data());
    std::ofstream target(argv[3],std::ios::binary);uint32_t count=uint32_t(info.size());target.write(reinterpret_cast<const char*>(&count),4);
    for(size_t i=0;i<info.size();++i){
        std::array<uint8_t,1024> first{},second{},mask{};
        const auto type=info[i].second.type;
        for(unsigned pass=0;pass<2;++pass){
            SDL_FillSurfaceRect(surface,nullptr,pass?252:251);
            RenderTileFrame(out,lightmap,{0,31},type,GetDunFrame(cel.get(),uint32_t(i+1)),
                type==TileType::LeftTriangle||type==TileType::RightTriangle?31:32,MaskType::Solid,tables[0].data());
            auto &pixels=pass?second:first;
            for(int y=0;y<32;++y)std::memcpy(pixels.data()+32*y,out.at(0,y),32);
        }
        for(size_t pixel=0;pixel<1024;++pixel){mask[pixel]=first[pixel]==second[pixel]?255:0;if(!mask[pixel])first[pixel]=0;}
        target.write(reinterpret_cast<const char*>(first.data()),1024);target.write(reinterpret_cast<const char*>(mask.data()),1024);
    }
    if(!target)throw std::runtime_error("Reference write failed");
    SDL_DestroySurface(surface);std::cout<<"PASS engine tile decode: "<<info.size()<<" frames\n";
    return 0;
}catch(const std::exception &error){std::cerr<<error.what()<<'\n';return 1;} }
