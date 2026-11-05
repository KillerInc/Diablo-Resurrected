#include "dds_decode.hpp"
#include <cassert>
using namespace reincarnated;
int main()
{
    std::vector<uint8_t> data(144);
    auto put = [&](size_t p, uint32_t v) { for (int i=0;i<4;++i) data[p+i] = v >> (i*8); };
    put(0,0x20534444); put(4,124); put(12,4); put(16,4); put(76,32); put(80,4); put(84,0x31545844);
    data[128]=0; data[129]=0xf8; // red RGB565, all first color
    DdsImage image;
    assert(DecodeDds(data,image));
    assert(image.width==4 && image.height==4 && image.rgba[0]==255 && image.rgba[1]==0 && image.rgba[3]==255);
    data[128]=0; data[129]=0; data[130]=0xff; data[131]=0xff; put(132,0xffffffff);
    assert(DecodeDds(data,image) && image.rgba[3]==0); // BC1 transparent index
    put(84,0x35545844); for (unsigned i=130;i<136;++i) data[i]=0; data[128]=23; data[129]=0; data[136]=0; data[137]=0xf8; put(140,0);
    assert(DecodeDds(data,image) && image.rgba[0]==255 && image.rgba[3]==23);
    put(84,0x33545844); data[128]=0x88;
    assert(DecodeDds(data,image) && image.rgba[3]==136);
    data.resize(143); assert(!DecodeDds(data,image));
    data.resize(144); put(16,0xffffffff); assert(!DecodeDds(data,image));
    put(16,1); put(12,1); put(80,0x41); put(84,0); put(88,32);
    put(92,0xff); put(96,0xff00); put(100,0xff0000); put(104,0xff000000); put(128,0x80402010);
    assert(DecodeDds(data,image) && image.rgba[0]==16 && image.rgba[1]==32 && image.rgba[2]==64 && image.rgba[3]==128);
    put(96,0xff); assert(!DecodeDds(data,image)); // overlapping channel masks
    put(0,0); assert(!DecodeDds(data,image));
}
