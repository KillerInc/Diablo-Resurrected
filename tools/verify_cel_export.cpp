// Compare offline CEL extraction with the engine's CEL-to-CLX converter/draw.
#include <SDL3/SDL.h>
#include <algorithm>
#include <array>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <vector>
#include "engine/clx_sprite.hpp"
#include "engine/render/clx_render.hpp"
#include "engine/surface.hpp"
#include "utils/cel_to_clx.hpp"
using namespace devilution;
int main(int argc,char **argv) { try {
    if(argc!=4)throw std::runtime_error("Usage: verify_cel_export CEL WIDTHS NEW_REFERENCE_BINARY");
    if(std::filesystem::exists(argv[3]))throw std::runtime_error("Reference output already exists");
    std::ifstream input(argv[1],std::ios::binary|std::ios::ate),sizes(argv[2]);
    if(!input||!sizes)throw std::runtime_error("Cannot read input");
    std::vector<uint8_t> bytes(size_t(input.tellg()));input.seekg(0);input.read(reinterpret_cast<char*>(bytes.data()),bytes.size());
    std::vector<uint16_t> widths;unsigned value;while(sizes>>value){if(!value||value>65535)throw std::runtime_error("Invalid width");widths.push_back(uint16_t(value));}
    if(widths.empty())throw std::runtime_error("Missing widths");
    auto owned=CelToClx(bytes.data(),bytes.size(),PointerOrValue<uint16_t>{widths.data()});ClxSpriteListOrSheet view(owned);
    const uint32_t columns=view.isSheet()?view.sheet().numLists():1;
    uint32_t rows=0,width=0,height=0;
    for(unsigned col=0;col<columns;++col){const auto list=view.isSheet()?view.sheet()[col]:view.list();rows=std::max(rows,list.numSprites());
        for(const auto sprite:list){width=std::max<unsigned>(width,sprite.width());height=std::max<unsigned>(height,sprite.height());}}
    if(!width||!height)throw std::runtime_error("Empty CEL");
    auto *surface=SDL_CreateSurface(width,height,SDL_PIXELFORMAT_INDEX8);
    if(!surface)throw std::runtime_error(SDL_GetError());Surface out(surface);
    std::ofstream target(argv[3],std::ios::binary);uint32_t header[]{columns,rows,width,height};target.write(reinterpret_cast<const char*>(header),sizeof(header));
    const size_t size=size_t(width)*height;std::vector<uint8_t> first(size),second(size),mask(size);
    for(unsigned col=0;col<columns;++col){const auto list=view.isSheet()?view.sheet()[col]:view.list();
        for(unsigned row=0;row<rows;++row){
            for(unsigned pass=0;pass<2;++pass){SDL_FillSurfaceRect(surface,nullptr,pass?252:251);
                if(row<list.numSprites())ClxDraw(out,{0,int(height)-1},list[row]);
                auto &pixels=pass?second:first;for(unsigned y=0;y<height;++y)std::copy_n(out.at(0,y),width,pixels.data()+y*width);}
            for(size_t i=0;i<size;++i){mask[i]=first[i]==second[i]?255:0;if(!mask[i])first[i]=0;}
            target.write(reinterpret_cast<const char*>(first.data()),size);target.write(reinterpret_cast<const char*>(mask.data()),size);
        }}
    if(!target)throw std::runtime_error("Reference write failed");SDL_DestroySurface(surface);
    std::cout<<"PASS engine CEL decode: "<<columns*rows<<" cells\n";return 0;
}catch(const std::exception &error){std::cerr<<error.what()<<'\n';return 1;} }
