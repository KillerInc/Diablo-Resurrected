#include "gpu_sprites.hpp"
#include "gpu_coverage.hpp"
#ifdef USE_SDL3
#include <algorithm>
#include <cstring>
#include <mutex>
#include <sstream>
#include <unordered_map>
#include "hd_renderer.hpp"
#include "sheet_png.hpp"
#include "utils/log.hpp"
#include "utils/display.h"
#ifdef _WIN32
#include "shaders/sprite_vert.hpp"
#include "shaders/sprite_frag.hpp"
#include "shaders/sprite_comp.hpp"
#endif
namespace reincarnated {
namespace {
SDL_GPUDevice *device=nullptr;
SDL_GPUGraphicsPipeline *pipeline=nullptr;
SDL_GPUSampler *sampler=nullptr;
SDL_GPUComputePipeline *nearestPipeline=nullptr;
SDL_GPUBuffer *nearestBuffer=nullptr;
std::vector<uint8_t> nearestPalette;
std::mutex cacheMutex;
std::mutex stagingMutex;
SDL_GPUTransferBuffer *staging=nullptr;
unsigned stagingCapacity=0;
std::unordered_map<std::string,std::shared_ptr<GpuSheet>> sheets;
std::vector<GpuSpriteDraw> draws;
struct ControlSlot { SDL_GPUTexture *mask=nullptr,*light=nullptr,*palette=nullptr;unsigned w=0,h=0; };
std::vector<ControlSlot> controls;
bool ready=false;
uint64_t uploads=0,drawCount=0;
SDL_GPUTexture *Texture(unsigned w,unsigned h,SDL_GPUTextureFormat format) {
    SDL_GPUTextureCreateInfo info{}; info.type=SDL_GPU_TEXTURETYPE_2D;info.format=format;
    info.usage=SDL_GPU_TEXTUREUSAGE_SAMPLER;info.width=w;info.height=h;info.layer_count_or_depth=1;info.num_levels=1;
    return SDL_CreateGPUTexture(device,&info);
}
// Rows are explicitly aligned for D3D12. Only a bounded page/mask is staged.
bool Upload(SDL_GPUCommandBuffer *cmd,SDL_GPUTexture *texture,const unsigned char *data,unsigned w,unsigned h,unsigned bytesPerPixel,bool bc7=false) {
    const unsigned rows=bc7?h/4:h;
    const unsigned sourcePitch=bc7?w*4:w*bytesPerPixel;
    const unsigned pitch=(sourcePitch+255)&~255U;
    SDL_GPUTransferBufferCreateInfo info{};info.usage=SDL_GPU_TRANSFERBUFFERUSAGE_UPLOAD;info.size=pitch*rows;
    const std::lock_guard<std::mutex> stageLock(stagingMutex);
    if(!staging || stagingCapacity<info.size){
        if(staging)SDL_ReleaseGPUTransferBuffer(device,staging);
        staging=SDL_CreateGPUTransferBuffer(device,&info);stagingCapacity=info.size;
    }
    auto *transfer=staging;if(!transfer)return false;
    auto *mapped=static_cast<unsigned char*>(SDL_MapGPUTransferBuffer(device,transfer,true));
    if(!mapped)return false;
    for(unsigned row=0;row<rows;++row)std::memcpy(mapped+row*pitch,data+row*sourcePitch,sourcePitch);
    SDL_UnmapGPUTransferBuffer(device,transfer);
    auto *copy=SDL_BeginGPUCopyPass(cmd);
    SDL_GPUTextureTransferInfo src{};src.transfer_buffer=transfer;src.pixels_per_row=bc7?pitch/4:pitch/bytesPerPixel;src.rows_per_layer=h;
    SDL_GPUTextureRegion dst{};dst.texture=texture;dst.w=w;dst.h=h;dst.d=1;
    SDL_UploadToGPUTexture(copy,&src,&dst,true);SDL_EndGPUCopyPass(copy);
    return true;
}
}
GpuSheet::~GpuSheet(){for(auto &page:pages)if(page.texture)SDL_ReleaseGPUTexture(owner,page.texture);}
void InitializeGpuSprites(SDL_GPUDevice *target){
    device=target;
#ifdef _WIN32
    if(std::strcmp(SDL_GetGPUDeviceDriver(device),"direct3d12")!=0 || SDL_getenv("D1R_DISABLE_GPU_SPRITES"))return;
    if(!SDL_GPUTextureSupportsFormat(device,SDL_GPU_TEXTUREFORMAT_BC7_RGBA_UNORM,SDL_GPU_TEXTURETYPE_2D,SDL_GPU_TEXTUREUSAGE_SAMPLER))return;
    SDL_GPUShaderCreateInfo sh{};sh.entrypoint="main";sh.format=SDL_GPU_SHADERFORMAT_DXBC;
    sh.stage=SDL_GPU_SHADERSTAGE_VERTEX;sh.code=SpriteVert;sh.code_size=sizeof(SpriteVert);sh.num_uniform_buffers=1;
    auto *vertex=SDL_CreateGPUShader(device,&sh);
    sh.stage=SDL_GPU_SHADERSTAGE_FRAGMENT;sh.code=SpriteFrag;sh.code_size=sizeof(SpriteFrag);sh.num_samplers=4;sh.num_storage_buffers=1;
    auto *fragment=SDL_CreateGPUShader(device,&sh);
    if(vertex && fragment){
        SDL_GPUColorTargetDescription color{};color.format=SDL_GPU_TEXTUREFORMAT_R8G8B8A8_UNORM;
        auto &blend=color.blend_state;blend.enable_blend=true;blend.src_color_blendfactor=SDL_GPU_BLENDFACTOR_SRC_ALPHA;blend.dst_color_blendfactor=SDL_GPU_BLENDFACTOR_ONE_MINUS_SRC_ALPHA;
        blend.color_blend_op=SDL_GPU_BLENDOP_ADD;blend.src_alpha_blendfactor=SDL_GPU_BLENDFACTOR_ONE;blend.dst_alpha_blendfactor=SDL_GPU_BLENDFACTOR_ONE_MINUS_SRC_ALPHA;blend.alpha_blend_op=SDL_GPU_BLENDOP_ADD;
        SDL_GPUGraphicsPipelineCreateInfo p{};p.vertex_shader=vertex;p.fragment_shader=fragment;p.primitive_type=SDL_GPU_PRIMITIVETYPE_TRIANGLELIST;
        p.target_info.color_target_descriptions=&color;p.target_info.num_color_targets=1;
        pipeline=SDL_CreateGPUGraphicsPipeline(device,&p);
    }
    if(vertex)SDL_ReleaseGPUShader(device,vertex);if(fragment)SDL_ReleaseGPUShader(device,fragment);
    SDL_GPUComputePipelineCreateInfo compute{};compute.code=SpriteComp;compute.code_size=sizeof(SpriteComp);compute.entrypoint="main";compute.format=SDL_GPU_SHADERFORMAT_DXBC;
    compute.num_samplers=1;compute.num_readwrite_storage_buffers=1;compute.threadcount_x=256;compute.threadcount_y=compute.threadcount_z=1;
    nearestPipeline=SDL_CreateGPUComputePipeline(device,&compute);
    SDL_GPUSamplerCreateInfo s{};s.min_filter=s.mag_filter=SDL_GPU_FILTER_NEAREST;s.mipmap_mode=SDL_GPU_SAMPLERMIPMAPMODE_NEAREST;
    s.address_mode_u=s.address_mode_v=s.address_mode_w=SDL_GPU_SAMPLERADDRESSMODE_CLAMP_TO_EDGE;
    sampler=SDL_CreateGPUSampler(device,&s);
    if(!pipeline||!sampler||!nearestPipeline){devilution::Log("GPU sprite pipeline unavailable: {}; preserving CPU fallback",SDL_GetError());SDL_ClearError();}
    else devilution::Log("GPU_SPRITES_READY backend=direct3d12 format=BC7 native_window_resolution=1");
#endif
}
void BeginGpuSpriteFrame(){draws.clear();ready=false;}
void ReleaseGpuPlayerSheets(){const std::lock_guard<std::mutex> lock(cacheMutex);sheets.clear();}
void DestroyGpuSprites(){BeginGpuSpriteFrame();ReleaseGpuPlayerSheets();
    for(auto &s:controls){if(s.mask)SDL_ReleaseGPUTexture(device,s.mask);if(s.light)SDL_ReleaseGPUTexture(device,s.light);if(s.palette)SDL_ReleaseGPUTexture(device,s.palette);}controls.clear();if(staging)SDL_ReleaseGPUTransferBuffer(device,staging);staging=nullptr;stagingCapacity=0;if(nearestBuffer)SDL_ReleaseGPUBuffer(device,nearestBuffer);nearestBuffer=nullptr;nearestPalette.clear();if(nearestPipeline)SDL_ReleaseGPUComputePipeline(device,nearestPipeline);nearestPipeline=nullptr;if(pipeline)SDL_ReleaseGPUGraphicsPipeline(device,pipeline);if(sampler)SDL_ReleaseGPUSampler(device,sampler);pipeline=nullptr;sampler=nullptr;device=nullptr;}
std::shared_ptr<GpuSheet> LoadGpuPlayerSheet(const SheetSource &source){
    if(!pipeline||!sampler||!nearestPipeline||source.path.rfind("hd/plrgfx/",0)!=0)return {};
    const std::lock_guard<std::mutex> lock(cacheMutex);
    auto found=sheets.find(source.path);if(found!=sheets.end())return found->second;
    auto insertion=sheets.emplace(source.path,nullptr);
    AssetBytes bytes,layout;
    const std::string manifest=source.path.substr(0,source.path.size()-4)+".gpus";
    auto &store=GetHdAssetStore();
    const AssetProvider *provider=nullptr;
    if(!store.readWithLayout(manifest,bytes,layout,&provider)){sheets.emplace(source.path,nullptr);return {};}
    auto sheet=std::make_shared<GpuSheet>();sheet->owner=device;
    std::istringstream input(std::string(bytes.begin(),bytes.end()));std::string magic;unsigned pages=0;
    input>>magic>>sheet->density>>sheet->columns>>sheet->rows>>sheet->width>>sheet->height>>pages;
    if(!input||magic!="D1R_GPU_SHEET_V1"||sheet->density!=4||sheet->columns!=source.columns||sheet->rows!=source.rows||sheet->width<source.width||!sheet->height||!pages||uint64_t(pages)>uint64_t(sheet->columns)*sheet->rows)return {};
    sheet->anchorX=source.width/2;sheet->anchorY=sheet->height;
    if(!layout.empty()){SheetLayout parsed;if(!ParseSheetLayout(layout,parsed))return {};sheet->anchorX=parsed.anchorX;sheet->anchorY=parsed.anchorY;}
    if(sheet->anchorX<0 || sheet->anchorY<0 || unsigned(sheet->anchorX)>sheet->width || unsigned(sheet->anchorY)>sheet->height || sheet->width>unsigned(INT32_MAX/8) || sheet->height>unsigned(INT32_MAX/8))return {};
    const auto parent=manifest.substr(0,manifest.find_last_of('/')+1);
    for(unsigned i=0;i<pages;++i){
        std::string name;unsigned w=0,h=0;input>>name>>w>>h;
        if(!input||name.find('/')!=std::string::npos||name.find('\\')!=std::string::npos||!IsSafeAssetId(name)||!w||!h||w%4||h%4||w>16384||h>16384)return {};
        AssetBytes page;if(!provider->read(parent+name,page)||page.size()!=size_t(w)*h+8)return {};
        uint32_t fileW=0,fileH=0;std::memcpy(&fileW,page.data(),4);std::memcpy(&fileH,page.data()+4,4);if(fileW!=w||fileH!=h)return {};
        auto *tex=Texture(w,h,SDL_GPU_TEXTUREFORMAT_BC7_RGBA_UNORM);if(!tex)return {};
        sheet->pages.push_back({tex,w,h});
        auto *cmd=SDL_AcquireGPUCommandBuffer(device);if(!cmd)return {};
        if(!Upload(cmd,tex,page.data()+8,w,h,1,true)){SDL_CancelGPUCommandBuffer(cmd);return {};}
        auto *fence=SDL_SubmitGPUCommandBufferAndAcquireFence(cmd);if(!fence)return {};
        const bool success=SDL_WaitForGPUFences(device,true,&fence,1);SDL_ReleaseGPUFence(device,fence);if(!success)return {};
        sheet->bytes+=size_t(w)*h;++uploads;
    }
    sheet->frames.resize(size_t(sheet->columns)*sheet->rows);
    for(auto &f:sheet->frames){input>>f.page>>f.x>>f.y>>f.w>>f.h>>f.cropX>>f.cropY;
        if(!input||f.page>=pages)return {};
        const auto &p=sheet->pages[f.page];
        if(uint64_t(f.x)+f.w>p.width||uint64_t(f.y)+f.h>p.height||uint64_t(f.cropX)+f.w>sheet->width*4ULL||uint64_t(f.cropY)+f.h>sheet->height*4ULL)return {};
    }
    std::string trailing;if(input>>trailing)return {};
    insertion.first->second=sheet;
    devilution::Log("GPU_SHEET_RESIDENT source={} pages={} bytes={} density=4 cpu_rgba_bytes=0",source.path,pages,sheet->bytes);
    return sheet;
}
GpuSpriteStats GetGpuSpriteStats(){const std::lock_guard<std::mutex> lock(cacheMutex);GpuSpriteStats s;for(const auto &entry:sheets)if(entry.second){++s.sheets;s.bytes+=entry.second->bytes;}s.uploads=uploads;s.draws=drawCount;return s;}
void QueueGpuSprite(GpuSpriteDraw draw){draws.push_back(std::move(draw));}
void MaskGpuSpritePixel(int x,int y,unsigned char r,unsigned char g,unsigned char b,unsigned alpha){
    for(auto &draw:draws){int dx=x-draw.maskX,dy=y-draw.maskY;if(dx<0||dy<0||dx>=draw.maskW||dy>=draw.maskH)continue;
        auto *p=draw.coverage.data()+(size_t(dy)*draw.maskW+dx)*4;
        ApplyGpuCoverage(p,r,g,b,alpha);
    }
}
void SaveGpuSpriteCursor(){for(auto &d:draws)d.cursorCoverage=d.coverage;}
void RestoreGpuSpriteCursor(){for(auto &d:draws)if(d.cursorCoverage.size()==d.coverage.size())d.coverage=d.cursorCoverage;}
bool HasQueuedGpuSprites(){return !draws.empty();}
bool GpuSpriteFrameReady(){return ready&&!draws.empty()&&pipeline;}
void SetGpuSpriteFrameReady(bool value){ready=value;}
void EnsureGpuPalette(SDL_GPUCommandBuffer *cmd,const uint8_t *colors) {
    if(nearestPalette.size()!=1024 || !std::equal(nearestPalette.begin(),nearestPalette.end(),colors)) {
        if(nearestBuffer)SDL_ReleaseGPUBuffer(device,nearestBuffer);
        SDL_GPUBufferCreateInfo info{};info.usage=SDL_GPU_BUFFERUSAGE_COMPUTE_STORAGE_WRITE|SDL_GPU_BUFFERUSAGE_GRAPHICS_STORAGE_READ;info.size=256*256*256*4;
        nearestBuffer=SDL_CreateGPUBuffer(device,&info);if(!nearestBuffer)devilution::ErrSdl();
        auto *paletteTexture=Texture(256,1,SDL_GPU_TEXTUREFORMAT_R8G8B8A8_UNORM);
        if(!paletteTexture||!Upload(cmd,paletteTexture,colors,256,1,4))devilution::ErrSdl();
        SDL_GPUStorageBufferReadWriteBinding output{};output.buffer=nearestBuffer;output.cycle=false;
        auto *pass=SDL_BeginGPUComputePass(cmd,nullptr,0,&output,1);SDL_BindGPUComputePipeline(pass,nearestPipeline);
        SDL_GPUTextureSamplerBinding input{paletteTexture,sampler};SDL_BindGPUComputeSamplers(pass,0,&input,1);
        SDL_DispatchGPUCompute(pass,256,256,1);SDL_EndGPUComputePass(pass);SDL_ReleaseGPUTexture(device,paletteTexture);
        nearestPalette.assign(colors,colors+1024);
        devilution::Log("GPU_PALETTE_LOOKUP bytes=67108864 cpu_rgba_bytes=0 exact_rgb24=1");
    }
}
void WarmGpuSpritePalette(const SDL_Color *palette) {
    if(!pipeline||!nearestPipeline||!GetGpuSpriteStats().sheets)return;
    const auto *colors=reinterpret_cast<const uint8_t*>(palette);
    if(nearestPalette.size()==1024 && std::equal(nearestPalette.begin(),nearestPalette.end(),colors))return;
    auto *cmd=SDL_AcquireGPUCommandBuffer(device);if(!cmd)devilution::ErrSdl();EnsureGpuPalette(cmd,colors);
    auto *fence=SDL_SubmitGPUCommandBufferAndAcquireFence(cmd);if(!fence||!SDL_WaitForGPUFences(device,true,&fence,1))devilution::ErrSdl();
    SDL_ReleaseGPUFence(device,fence);
}
void RenderGpuSprites(SDL_GPUCommandBuffer *cmd,SDL_GPUTexture *target,int logicalW,int logicalH,int pixelW,int pixelH){
    if(!GpuSpriteFrameReady())return;
    if(controls.size()<draws.size())controls.resize(draws.size());
    size_t slotIndex=0;
    EnsureGpuPalette(cmd,draws.front().palette.data());
    static bool reported=false;
    if(!reported){devilution::Log("GPU_SPRITE_DRAW physical={}x{} logical={}x{} actors={} shader_lighting=1",pixelW,pixelH,logicalW,logicalH,draws.size());reported=true;}
    for(const auto &draw:draws){
        auto &slot=controls[slotIndex++];
        if(slot.w<unsigned(draw.maskW)||slot.h<unsigned(draw.maskH)){
            if(slot.mask)SDL_ReleaseGPUTexture(device,slot.mask);if(slot.light)SDL_ReleaseGPUTexture(device,slot.light);
            slot.w=std::max(slot.w,(unsigned(draw.maskW)+63)&~63U);slot.h=std::max(slot.h,(unsigned(draw.maskH)+63)&~63U);
            slot.mask=Texture(slot.w,slot.h,SDL_GPU_TEXTUREFORMAT_R8G8B8A8_UNORM);slot.light=Texture(slot.w,slot.h,SDL_GPU_TEXTUREFORMAT_R8_UNORM);
        }
        if(!slot.palette)slot.palette=Texture(256,17,SDL_GPU_TEXTUREFORMAT_R8G8B8A8_UNORM);
        auto *mask=slot.mask,*light=slot.light,*pal=slot.palette;
        if(!mask||!light||!pal)devilution::ErrSdl();
        if(!Upload(cmd,mask,draw.coverage.data(),draw.maskW,draw.maskH,4)||!Upload(cmd,light,draw.lighting.data(),draw.maskW,draw.maskH,1)||!Upload(cmd,pal,draw.palette.data(),256,17,4))devilution::ErrSdl();
        SDL_GPUColorTargetInfo color{};color.texture=target;color.load_op=SDL_GPU_LOADOP_LOAD;color.store_op=SDL_GPU_STOREOP_STORE;
        auto *pass=SDL_BeginGPURenderPass(cmd,&color,1,nullptr);SDL_BindGPUGraphicsPipeline(pass,pipeline);
        SDL_GPUViewport viewport{0,0,float(pixelW),float(pixelH),0,1};SDL_SetGPUViewport(pass,&viewport);
        const auto &page=draw.sheet->pages[draw.frame.page];
        SDL_GPUTextureSamplerBinding bindings[4]={{page.texture,sampler},{mask,sampler},{light,sampler},{pal,sampler}};SDL_BindGPUFragmentSamplers(pass,0,bindings,4);
        SDL_BindGPUFragmentStorageBuffers(pass,0,&nearestBuffer,1);
        const float vertex[12]={draw.x,draw.y,draw.w,draw.h,float(draw.frame.x)/page.width,float(draw.frame.y)/page.height,float(draw.frame.w)/page.width,float(draw.frame.h)/page.height,float(logicalW),float(logicalH),0,0};
        const float fragment[8]={float(draw.maskX),float(draw.maskY),float(draw.maskW),float(draw.maskH),draw.alpha,0,0,0};
        SDL_PushGPUVertexUniformData(cmd,0,vertex,sizeof(vertex));SDL_PushGPUFragmentUniformData(cmd,0,fragment,sizeof(fragment));
        SDL_DrawGPUPrimitives(pass,6,1,0,0);SDL_EndGPURenderPass(pass);++drawCount;

    }
}
}
#endif
