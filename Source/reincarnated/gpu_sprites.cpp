#include "gpu_sprites.hpp"
#include "gpu_coverage.hpp"
#include "gpu_ui.hpp"
#include "world_sprite_indices.hpp"
#ifdef USE_SDL3
#include <algorithm>
#include <bit>
#include <cstring>
#include <mutex>
#include <sstream>
#include <unordered_map>
#include "hd_renderer.hpp"
#include "sheet_png.hpp"
#include "engine/palette.h"
#include "engine/surface.hpp"
#include "utils/log.hpp"
#include "utils/display.h"
#ifdef _WIN32
#include "shaders/sprite_vert.hpp"
#include "shaders/sprite_frag.hpp"
#include "shaders/ui_frag.hpp"
#include "shaders/ui_cache_frag.hpp"
#include "shaders/sprite_comp.hpp"
#endif
namespace reincarnated {
namespace {
SDL_GPUDevice *device=nullptr;
SDL_GPUGraphicsPipeline *pipeline=nullptr,*uiPipeline=nullptr,*uiCachePipeline=nullptr;
SDL_GPUSampler *sampler=nullptr;
SDL_GPUComputePipeline *nearestPipeline=nullptr;
SDL_GPUBuffer *nearestBuffer=nullptr;
std::vector<uint8_t> nearestPalette;
std::mutex cacheMutex;
std::mutex stagingMutex;
SDL_GPUTransferBuffer *staging=nullptr,*pageStaging=nullptr;
unsigned stagingCapacity=0,pageStagingCapacity=0;
std::unordered_map<std::string,std::shared_ptr<GpuSheet>> sheets;
std::vector<GpuSpriteDraw> draws, savedUiScene;
struct UiUpload { std::shared_ptr<GpuSheet> sheet; std::vector<uint8_t> bytes; };
std::vector<UiUpload> pendingUiUploads;
constexpr unsigned CoverageTileShift=5, CoverageTileSize=1U<<CoverageTileShift;
unsigned coverageWidth=0,coverageHeight=0,coverageColumns=0;
std::vector<std::vector<size_t>> coverageTiles;
struct ControlSlot { SDL_GPUTexture *mask=nullptr,*light=nullptr,*palette=nullptr;unsigned w=0,h=0;std::vector<unsigned char> paletteBytes, maskBytes;unsigned maskW=0,maskH=0; };
std::vector<ControlSlot> controls;
bool ready=false;
size_t cursorDrawCount=0;
bool cursorSnapshot=false;
std::array<std::vector<GpuSpriteDraw>,5> uiHud;
std::array<bool,5> uiHudValid{};
std::array<size_t,5> uiHudStart{};
SDL_Rect uiHudRect{};
std::shared_ptr<GpuUiPanel> inventoryPanel;
std::string inventoryKey;
SDL_Rect inventoryBounds{};
size_t panelStart=0;
bool panelCapture=false;
uint64_t panelCaptures=0,panelReplays=0,panelBuilds=0;
uint64_t uploads=0,drawCount=0,renderPasses=0,paletteUploads=0,controlBytes=0,maskUploads=0,implicitUiDraws=0;
SDL_GPUTexture *Texture(unsigned w,unsigned h,SDL_GPUTextureFormat format) {
    SDL_GPUTextureCreateInfo info{}; info.type=SDL_GPU_TEXTURETYPE_2D;info.format=format;
    info.usage=SDL_GPU_TEXTUREUSAGE_SAMPLER;info.width=w;info.height=h;info.layer_count_or_depth=1;info.num_levels=1;
    return SDL_CreateGPUTexture(device,&info);
}
// An empty UI mask means identity coverage. Allocate only for actual raster
// overlap; native occupancy and rectangular clipping remain in the UI shader.
void EnsureCoverage(GpuSpriteDraw &draw) {
    if(!draw.ui || !draw.coverage.empty())return;
    draw.coverage.assign(size_t(draw.maskW)*draw.maskH*4,0);
    for(size_t i=3;i<draw.coverage.size();i+=4)draw.coverage[i]=255;
}
// Rows are explicitly aligned for D3D12. Only a bounded page/mask is staged.
bool Upload(SDL_GPUCommandBuffer *cmd,SDL_GPUTexture *texture,const unsigned char *data,unsigned w,unsigned h,unsigned bytesPerPixel,bool bc7=false) {
    const unsigned rows=bc7?h/4:h;
    const unsigned sourcePitch=bc7?w*4:w*bytesPerPixel;
    const unsigned pitch=(sourcePitch+255)&~255U;
    SDL_GPUTransferBufferCreateInfo info{};info.usage=SDL_GPU_TRANSFERBUFFERUSAGE_UPLOAD;info.size=pitch*rows;
    const std::lock_guard<std::mutex> stageLock(stagingMutex);
    auto *&pool=bc7?pageStaging:staging;auto &capacity=bc7?pageStagingCapacity:stagingCapacity;
    if(!pool || capacity<info.size){
        if(pool)SDL_ReleaseGPUTransferBuffer(device,pool);
        pool=SDL_CreateGPUTransferBuffer(device,&info);capacity=info.size;
    }
    auto *transfer=pool;if(!transfer)return false;
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
    sh.stage=SDL_GPU_SHADERSTAGE_FRAGMENT;sh.code=SpriteFrag;sh.code_size=sizeof(SpriteFrag);sh.num_samplers=5;sh.num_storage_buffers=1;
    auto *fragment=SDL_CreateGPUShader(device,&sh);
    if(vertex && fragment){
        SDL_GPUColorTargetDescription color{};color.format=SDL_GPU_TEXTUREFORMAT_R8G8B8A8_UNORM;
        auto &blend=color.blend_state;blend.enable_blend=true;blend.src_color_blendfactor=SDL_GPU_BLENDFACTOR_SRC_ALPHA;blend.dst_color_blendfactor=SDL_GPU_BLENDFACTOR_ONE_MINUS_SRC_ALPHA;
        blend.color_blend_op=SDL_GPU_BLENDOP_ADD;blend.src_alpha_blendfactor=SDL_GPU_BLENDFACTOR_ONE;blend.dst_alpha_blendfactor=SDL_GPU_BLENDFACTOR_ONE_MINUS_SRC_ALPHA;blend.alpha_blend_op=SDL_GPU_BLENDOP_ADD;
        SDL_GPUGraphicsPipelineCreateInfo p{};p.vertex_shader=vertex;p.fragment_shader=fragment;p.primitive_type=SDL_GPU_PRIMITIVETYPE_TRIANGLELIST;
        p.target_info.color_target_descriptions=&color;p.target_info.num_color_targets=1;
        pipeline=SDL_CreateGPUGraphicsPipeline(device,&p);
        sh.code=UiFrag;sh.code_size=sizeof(UiFrag);sh.num_storage_buffers=0;sh.num_samplers=4;
        auto *uiFragment=SDL_CreateGPUShader(device,&sh);
        if(uiFragment){p.fragment_shader=uiFragment;uiPipeline=SDL_CreateGPUGraphicsPipeline(device,&p);SDL_ReleaseGPUShader(device,uiFragment);}
        sh.code=UiCacheFrag;sh.code_size=sizeof(UiCacheFrag);sh.num_samplers=2;
        auto *cacheFragment=SDL_CreateGPUShader(device,&sh);
        if(cacheFragment){color.blend_state.src_color_blendfactor=SDL_GPU_BLENDFACTOR_ONE;p.fragment_shader=cacheFragment;uiCachePipeline=SDL_CreateGPUGraphicsPipeline(device,&p);SDL_ReleaseGPUShader(device,cacheFragment);}
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
void BeginGpuSpriteFrame(){
    draws.clear();ready=false;cursorSnapshot=false;panelCapture=false;
    const unsigned w=unsigned(std::max<int64_t>(0,devilution::gnScreenWidth)),h=unsigned(std::max<int64_t>(0,devilution::gnScreenHeight));
    const unsigned columns=(w+CoverageTileSize-1)>>CoverageTileShift,rows=(h+CoverageTileSize-1)>>CoverageTileShift;
    if(w!=coverageWidth||h!=coverageHeight){coverageTiles.clear();coverageTiles.resize(size_t(columns)*rows);coverageWidth=w;coverageHeight=h;coverageColumns=columns;}
    else for(auto &tile:coverageTiles)tile.clear();
}
void ReleaseGpuPlayerSheets(){const std::lock_guard<std::mutex> lock(cacheMutex);sheets.clear();ClearWorldSpriteIndices();}
void DestroyGpuSprites(){BeginGpuSpriteFrame();pendingUiUploads.clear();ForgetGpuUiScene();InvalidateGpuUiHud();ClearGpuUiAssets();ReleaseGpuPlayerSheets();
    for(auto &s:controls){if(s.mask)SDL_ReleaseGPUTexture(device,s.mask);if(s.light)SDL_ReleaseGPUTexture(device,s.light);if(s.palette)SDL_ReleaseGPUTexture(device,s.palette);}controls.clear();if(staging)SDL_ReleaseGPUTransferBuffer(device,staging);staging=nullptr;stagingCapacity=0;if(pageStaging)SDL_ReleaseGPUTransferBuffer(device,pageStaging);pageStaging=nullptr;pageStagingCapacity=0;if(nearestBuffer)SDL_ReleaseGPUBuffer(device,nearestBuffer);nearestBuffer=nullptr;nearestPalette.clear();if(nearestPipeline)SDL_ReleaseGPUComputePipeline(device,nearestPipeline);nearestPipeline=nullptr;if(uiCachePipeline)SDL_ReleaseGPUGraphicsPipeline(device,uiCachePipeline);uiCachePipeline=nullptr;if(uiPipeline)SDL_ReleaseGPUGraphicsPipeline(device,uiPipeline);uiPipeline=nullptr;if(pipeline)SDL_ReleaseGPUGraphicsPipeline(device,pipeline);if(sampler)SDL_ReleaseGPUSampler(device,sampler);pipeline=nullptr;sampler=nullptr;device=nullptr;}
bool CanDrawGpuUi(){return uiPipeline&&sampler;}
std::shared_ptr<GpuSheet> CreateGpuUiIndices(unsigned w,unsigned h,const uint8_t *rgba){
    if(!CanDrawGpuUi()||!w||!h)return {};
    auto *texture=Texture(w,h,SDL_GPU_TEXTUREFORMAT_R8G8B8A8_UNORM);if(!texture)return {};
    auto sheet=std::make_shared<GpuSheet>();sheet->owner=device;sheet->width=w;sheet->height=h;sheet->density=1;sheet->columns=sheet->rows=1;
    sheet->pages.push_back({texture,w,h});sheet->frames.push_back({0,0,0,w,h,0,0});sheet->bytes=size_t(w)*h*4;
    pendingUiUploads.push_back({sheet,std::vector<uint8_t>(rgba,rgba+size_t(w)*h*4)});
    return sheet;
}
std::shared_ptr<GpuSheet> LoadGpuSheet(const SheetSource &source){
    if(!pipeline||!sampler||!nearestPipeline)return {};
    const std::lock_guard<std::mutex> lock(cacheMutex);
    auto found=sheets.find(source.path);if(found!=sheets.end())return found->second;
    auto insertion=sheets.emplace(source.path,nullptr);
    AssetBytes bytes,layout;
    const std::string manifest=source.path.substr(0,source.path.size()-4)+".gpus";
    auto &store=GetHdAssetStore();
    const AssetProvider *provider=nullptr;
    if(!store.readGpuWithLayout(source.path,bytes,layout,&provider)){sheets.emplace(source.path,nullptr);return {};}
    auto sheet=std::make_shared<GpuSheet>();sheet->owner=device;
    std::istringstream input(std::string(bytes.begin(),bytes.end()));std::string magic;unsigned pages=0;
    input>>magic>>sheet->density>>sheet->columns>>sheet->rows>>sheet->width>>sheet->height>>pages;
    if(!input||magic!="D1R_GPU_SHEET_V1"||sheet->density!=4||sheet->columns!=source.columns||sheet->rows!=source.rows||sheet->width<source.width||!sheet->height||!pages||uint64_t(pages)>uint64_t(sheet->columns)*sheet->rows)return {};
    sheet->anchorX=source.width/2;sheet->anchorY=sheet->height;
    if(!layout.empty()){
        SheetLayout parsed;if(!ParseSheetLayout(layout,parsed))return {};
        if(parsed.authored && !source.path.starts_with("hd/towners/"))return {};
        sheet->authoredTowner=parsed.authored;
        sheet->anchorX=parsed.anchorX;sheet->anchorY=parsed.anchorY;
    }
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
GpuSpriteStats GetGpuSpriteStats(){const std::lock_guard<std::mutex> lock(cacheMutex);GpuSpriteStats s;for(const auto &entry:sheets)if(entry.second){++s.sheets;if(entry.first.starts_with("hd/plrgfx/"))++s.playerSheets;s.bytes+=entry.second->bytes;}s.uploads=uploads;s.draws=drawCount;s.renderPasses=renderPasses;s.paletteUploads=paletteUploads;s.controlBytes=controlBytes;return s;}
void QueueGpuSprite(GpuSpriteDraw draw){
    const size_t index=draws.size();draws.push_back(std::move(draw));const auto &queued=draws.back();
    const int left=std::max(0,queued.maskX),top=std::max(0,queued.maskY);
    const int right=std::min<int64_t>(coverageWidth,int64_t(queued.maskX)+queued.maskW);
    const int bottom=std::min<int64_t>(coverageHeight,int64_t(queued.maskY)+queued.maskH);
    if(left>=right||top>=bottom)return;
    for(unsigned row=unsigned(top)>>CoverageTileShift;row<=unsigned(bottom-1)>>CoverageTileShift;++row)
        for(unsigned column=unsigned(left)>>CoverageTileShift;column<=unsigned(right-1)>>CoverageTileShift;++column)
            coverageTiles[size_t(row)*coverageColumns+column].push_back(index);
}
void MaskGpuSpritePixel(int x,int y,unsigned char r,unsigned char g,unsigned char b,unsigned alpha){
    if(draws.empty()||unsigned(x)>=coverageWidth||unsigned(y)>=coverageHeight)return;
    const auto &tile=coverageTiles[size_t(unsigned(y)>>CoverageTileShift)*coverageColumns+(unsigned(x)>>CoverageTileShift)];
    for(const size_t index:tile){auto &draw=draws[index];const int dx=x-draw.maskX,dy=y-draw.maskY;
        if(dx<0||dy<0||dx>=draw.maskW||dy>=draw.maskH)continue;
        EnsureCoverage(draw);auto *p=draw.coverage.data()+(size_t(dy)*draw.maskW+dx)*4;ApplyGpuCoverage(p,r,g,b,alpha);
    }
}
void MaskGpuSpriteOpaqueSpan(int x,int y,unsigned length){
    if(draws.empty()||unsigned(y)>=coverageHeight)return;
    const int64_t left=std::max<int64_t>(0,x),end=std::min<int64_t>(coverageWidth,int64_t(x)+length);
    if(left>=end)return;
    const size_t row=size_t(unsigned(y)>>CoverageTileShift)*coverageColumns;
    for(unsigned column=unsigned(left)>>CoverageTileShift;column<=unsigned(end-1)>>CoverageTileShift;++column){
        const int64_t cellLeft=std::max<int64_t>(left,column*CoverageTileSize),cellRight=std::min<int64_t>(end,(column+1)*CoverageTileSize);
        for(const size_t index:coverageTiles[row+column]){auto &draw=draws[index];const int dy=y-draw.maskY;
            if(dy<0||dy>=draw.maskH)continue;
            const int64_t begin=std::max<int64_t>(cellLeft,draw.maskX),finish=std::min<int64_t>(cellRight,int64_t(draw.maskX)+draw.maskW);
            if(begin>=finish)continue;
            EnsureCoverage(draw);auto *pixels=draw.coverage.data()+(size_t(dy)*draw.maskW+size_t(begin-draw.maskX))*4;
            // Fully occluded pixels stay discarded through subsequent blends.
            std::memset(pixels,0,size_t(finish-begin)*4);
        }
    }
}
void MaskGpuSpriteBlendedSpan(int x,int y,const uint32_t *colors,unsigned length){
    if(draws.empty()||unsigned(y)>=coverageHeight)return;
    const int64_t left=std::max<int64_t>(0,x),end=std::min<int64_t>(coverageWidth,int64_t(x)+length);
    if(left>=end)return;
    const size_t row=size_t(unsigned(y)>>CoverageTileShift)*coverageColumns;
    for(unsigned column=unsigned(left)>>CoverageTileShift;column<=unsigned(end-1)>>CoverageTileShift;++column){
        const int64_t cellLeft=std::max<int64_t>(left,column*CoverageTileSize),cellRight=std::min<int64_t>(end,(column+1)*CoverageTileSize);
        for(const size_t index:coverageTiles[row+column]){auto &draw=draws[index];const int dy=y-draw.maskY;
            if(dy<0||dy>=draw.maskH)continue;
            const int64_t begin=std::max<int64_t>(cellLeft,draw.maskX),finish=std::min<int64_t>(cellRight,int64_t(draw.maskX)+draw.maskW);
            if(begin>=finish)continue;
            EnsureCoverage(draw);auto *pixels=draw.coverage.data()+(size_t(dy)*draw.maskW+size_t(begin-draw.maskX))*4;
            const auto *source=reinterpret_cast<const uint8_t*>(colors+size_t(begin-x));
            for(int64_t px=begin;px<finish;++px,pixels+=4,source+=4)
                if(pixels[3])ApplyGpuCoverage(pixels,source[0],source[1],source[2],128);
        }
    }
}
GpuUiPanelStats GetGpuUiPanelStats(){return {panelCaptures,panelReplays,panelBuilds,inventoryPanel&&inventoryPanel->composite?inventoryPanel->composite->bytes:0};}
void InvalidateGpuUiPanel(){inventoryPanel.reset();inventoryKey.clear();panelCapture=false;}
void QueueInventoryPanel(){
    GpuSpriteDraw draw;draw.ui=true;draw.panel=inventoryPanel;
    draw.x=draw.y=0;draw.w=float(devilution::gnScreenWidth);draw.h=float(devilution::gnScreenHeight);
    draw.maskX=inventoryBounds.x;draw.maskY=inventoryBounds.y;draw.maskW=inventoryBounds.w;draw.maskH=inventoryBounds.h;
    QueueGpuSprite(std::move(draw));
}
bool BeginGpuUiPanel(const devilution::Surface &out,SDL_Rect bounds,std::string_view key){
    panelCapture=false;
    const char *setting=SDL_getenv("D1R_GPU_INVENTORY_CACHE");
    if(!GpuUiPhase()||!uiCachePipeline||(setting&&std::strcmp(setting,"0")==0))return false;
    std::string complete(key);complete.append(reinterpret_cast<const char*>(&out.region),sizeof(out.region));
    const int dimensions[2]={int(devilution::gnScreenWidth),int(devilution::gnScreenHeight)};
    complete.append(reinterpret_cast<const char*>(dimensions),sizeof(dimensions));
    if(inventoryPanel&&inventoryKey==complete&&SDL_RectsEqual(&bounds,&inventoryBounds)){++panelReplays;QueueInventoryPanel();return true;}
    inventoryPanel=std::make_shared<GpuUiPanel>();inventoryKey=std::move(complete);inventoryBounds=bounds;panelStart=draws.size();panelCapture=true;return false;
}
void EndGpuUiPanel(){
    if(!panelCapture)return;
    inventoryPanel->commands.assign(draws.begin()+panelStart,draws.end());
    draws.resize(panelStart);auto earlier=std::move(draws);const bool previousReady=ready;
    BeginGpuSpriteFrame();for(auto &draw:earlier)QueueGpuSprite(std::move(draw));QueueInventoryPanel();ready=previousReady;++panelCaptures;
}
void SaveGpuUiScene(){savedUiScene=draws;}
void RestoreGpuUiScene(){BeginGpuSpriteFrame();for(const auto &draw:savedUiScene)QueueGpuSprite(draw);}
void ForgetGpuUiScene(){savedUiScene.clear();}
void InvalidateGpuUiHud(){for(auto &component:uiHud)component.clear();uiHudValid.fill(false);}
bool PrepareGpuUiHudLayer(int x,int y,int w,int h){SDL_Rect rect{x,y,w,h};if(!SDL_RectsEqual(&rect,&uiHudRect)){InvalidateGpuUiHud();uiHudRect=rect;}return std::all_of(uiHudValid.begin(),uiHudValid.end(),[](bool value){return value;});}
bool BeginGpuUiHudComponent(unsigned component,bool changed){
    if(changed||!uiHudValid[component]){uiHudStart[component]=draws.size();return true;}
    for(const auto &draw:uiHud[component])QueueGpuSprite(draw);return false;
}
void EndGpuUiHudComponent(unsigned component){uiHud[component].assign(draws.begin()+uiHudStart[component],draws.end());uiHudValid[component]=true;}
bool TranslateGpuUiDraws(SDL_Rect rect,const uint8_t *trn){
    std::vector<GpuSpriteDraw> translated;
    for(auto &draw:draws){if(!draw.ui||draw.panel)continue;SDL_Rect bounds{draw.maskX,draw.maskY,draw.maskW,draw.maskH},area;
        if(!SDL_GetRectIntersection(&bounds,&rect,&area))continue;
        auto copy=draw;copy.maskX=area.x;copy.maskY=area.y;copy.maskW=area.w;copy.maskH=area.h;if(!draw.coverage.empty())copy.coverage.resize(size_t(area.w)*area.h*4);
        const bool identity=draw.coverage.empty();EnsureCoverage(draw);
        for(int y=0;y<area.h;++y){auto *src=draw.coverage.data()+(size_t(y+area.y-draw.maskY)*draw.maskW+area.x-draw.maskX)*4;if(!identity)std::memcpy(copy.coverage.data()+size_t(y)*area.w*4,src,size_t(area.w)*4);std::memset(src,0,size_t(area.w)*4);}
        for(auto &index:copy.uiTranslation)index=trn[index];translated.push_back(std::move(copy));
    }
    for(auto &draw:translated)QueueGpuSprite(std::move(draw));return !translated.empty();
}
void SaveGpuSpriteCursor(){cursorSnapshot=true;cursorDrawCount=draws.size();for(auto &d:draws)d.cursorCoverage=d.coverage;}
void RestoreGpuSpriteCursor(){
    if(!cursorSnapshot)return;
    if(draws.size()>cursorDrawCount){draws.resize(cursorDrawCount);for(auto &tile:coverageTiles)tile.erase(std::remove_if(tile.begin(),tile.end(),[](size_t i){return i>=cursorDrawCount;}),tile.end());}
    for(auto &d:draws)d.coverage=d.cursorCoverage;
}
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
    for(auto &draw:draws)if(draw.panel){
        auto panel=draw.panel;
        const bool resized=!panel->composite||panel->composite->pages[0].width!=unsigned(pixelW)||panel->composite->pages[0].height!=unsigned(pixelH);
        if(resized){
            panel->composite=std::make_shared<GpuSheet>();auto &sheet=*panel->composite;sheet.owner=device;sheet.width=pixelW;sheet.height=pixelH;sheet.bytes=size_t(pixelW)*pixelH*4;
            SDL_GPUTextureCreateInfo info{};info.type=SDL_GPU_TEXTURETYPE_2D;info.format=SDL_GPU_TEXTUREFORMAT_R8G8B8A8_UNORM;info.usage=SDL_GPU_TEXTUREUSAGE_SAMPLER|SDL_GPU_TEXTUREUSAGE_COLOR_TARGET;info.width=pixelW;info.height=pixelH;info.layer_count_or_depth=info.num_levels=1;
            auto *texture=SDL_CreateGPUTexture(device,&info);if(!texture)devilution::ErrSdl();sheet.pages.push_back({texture,unsigned(pixelW),unsigned(pixelH)});panel->valid=false;
        }
        if(!panel->valid||std::memcmp(panel->palette.data(),devilution::Palette->colors,1024)!=0){
            auto *texture=panel->composite->pages[0].texture;
            SDL_GPUColorTargetInfo clear{};clear.texture=texture;clear.load_op=SDL_GPU_LOADOP_CLEAR;clear.store_op=SDL_GPU_STOREOP_STORE;clear.clear_color={0,0,0,0};
            auto *pass=SDL_BeginGPURenderPass(cmd,&clear,1,nullptr);SDL_EndGPURenderPass(pass);
            std::vector<GpuSpriteDraw> mainDraws;mainDraws.swap(draws);draws=panel->commands;
            RenderGpuSprites(cmd,texture,logicalW,logicalH,pixelW,pixelH);
            draws.clear();draws.swap(mainDraws);
            std::memcpy(panel->palette.data(),devilution::Palette->colors,1024);panel->valid=true;++panelBuilds;
        }
        draw.sheet=panel->composite;draw.frame={0,0,0,unsigned(pixelW),unsigned(pixelH),0,0};
    }
    if(controls.size()<draws.size())controls.resize(draws.size());
    const char *batchSetting=SDL_getenv("D1R_GPU_ACTOR_BATCH");
    const bool batch=!batchSetting||std::strcmp(batchSetting,"0")!=0;
    const char *uiControlsSetting=SDL_getenv("D1R_GPU_UI_CONTROLS");
    const bool compactUi=!uiControlsSetting||std::strcmp(uiControlsSetting,"0")!=0;
    size_t slotIndex=0;
    auto worldDraw=std::find_if(draws.begin(),draws.end(),[](const GpuSpriteDraw &d){return !d.ui&&!d.uiIndices;});
    if(worldDraw!=draws.end())EnsureGpuPalette(cmd,worldDraw->palette.data());
    else if(!nearestBuffer&&std::any_of(draws.begin(),draws.end(),[](const GpuSpriteDraw &d){return !d.ui;})){
        // Native-index materials do not read the lookup, but the pipeline's
        // storage binding must remain valid. Never regenerate it for these draws.
        SDL_GPUBufferCreateInfo info{};info.usage=SDL_GPU_BUFFERUSAGE_GRAPHICS_STORAGE_READ;info.size=4;
        nearestBuffer=SDL_CreateGPUBuffer(device,&info);if(!nearestBuffer)devilution::ErrSdl();
    }
    static bool reported=false;
    if(!reported){devilution::Log("GPU_SPRITE_DRAW physical={}x{} logical={}x{} actors={} shader_lighting=1",pixelW,pixelH,logicalW,logicalH,draws.size());reported=true;}
    // Page uploads and per-frame controls use separate transfer pools. A large
    // BC7 page must not set the allocation size for every tiny mask/palette.
    struct ControlUpload{SDL_GPUTexture *texture;const uint8_t *data;unsigned w,h,bytes,offset=0;};
    std::vector<ControlUpload> jobs;jobs.reserve(draws.size()*3+pendingUiUploads.size());
    for(const auto &upload:pendingUiUploads)jobs.push_back({upload.sheet->pages[0].texture,upload.bytes.data(),upload.sheet->width,upload.sheet->height,4});
    for(auto &draw:draws){
        if(draw.ui&&!draw.panel)for(unsigned i=0;i<256;++i)std::memcpy(draw.palette.data()+(256+i)*4,&devilution::Palette->colors[draw.uiTranslation[i]],4);
        if(draw.ui&&!compactUi)EnsureCoverage(draw);
        const bool implicit=draw.ui&&draw.coverage.empty();
        auto &slot=controls[slotIndex++];
        if(!implicit&&(slot.w<unsigned(draw.maskW)||slot.h<unsigned(draw.maskH))){
            slot.maskBytes.clear();
            if(slot.mask)SDL_ReleaseGPUTexture(device,slot.mask);if(slot.light)SDL_ReleaseGPUTexture(device,slot.light);
            slot.w=std::max(slot.w,(unsigned(draw.maskW)+63)&~63U);slot.h=std::max(slot.h,(unsigned(draw.maskH)+63)&~63U);
            slot.mask=Texture(slot.w,slot.h,SDL_GPU_TEXTUREFORMAT_R8G8B8A8_UNORM);slot.light=Texture(slot.w,slot.h,SDL_GPU_TEXTUREFORMAT_R8_UNORM);
        }
        if(!draw.panel&&!slot.palette)slot.palette=Texture(256,17,SDL_GPU_TEXTUREFORMAT_R8G8B8A8_UNORM);
        if((!implicit&&(!slot.mask||!slot.light))||(!draw.panel&&!slot.palette))devilution::ErrSdl();
        if(!implicit){
            if(!draw.ui||!compactUi||slot.maskW!=unsigned(draw.maskW)||slot.maskH!=unsigned(draw.maskH)||slot.maskBytes!=draw.coverage){
                jobs.push_back({slot.mask,draw.coverage.data(),unsigned(draw.maskW),unsigned(draw.maskH),4});++maskUploads;
                if(draw.ui&&compactUi){slot.maskBytes=draw.coverage;slot.maskW=draw.maskW;slot.maskH=draw.maskH;}
                else slot.maskBytes.clear();
            }
        }else ++implicitUiDraws;
        if(!draw.ui)jobs.push_back({slot.light,draw.lighting.data(),unsigned(draw.maskW),unsigned(draw.maskH),1});
        // Compare bytes rather than identities: palette cycling and mutable TRNs
        // must invalidate even when the originating pointer stays unchanged.
        if(!draw.panel&&(!batch||slot.paletteBytes!=draw.palette)){
            jobs.push_back({slot.palette,draw.palette.data(),256,draw.ui?2U:17U,4});
            slot.paletteBytes=draw.palette;++paletteUploads;
        }
    }
    unsigned total=0;for(auto &job:jobs){job.offset=total;total+=((job.w*job.bytes+255)&~255U)*job.h;}
    if(total){
        const std::lock_guard<std::mutex> stageLock(stagingMutex);
        if(!staging||stagingCapacity<total){if(staging)SDL_ReleaseGPUTransferBuffer(device,staging);
            SDL_GPUTransferBufferCreateInfo info{};info.usage=SDL_GPU_TRANSFERBUFFERUSAGE_UPLOAD;info.size=std::bit_ceil(std::max(65536U,total));
            staging=SDL_CreateGPUTransferBuffer(device,&info);stagingCapacity=info.size;}
        if(!staging)devilution::ErrSdl();auto *mapped=static_cast<uint8_t*>(SDL_MapGPUTransferBuffer(device,staging,true));if(!mapped)devilution::ErrSdl();
        for(const auto &job:jobs){const unsigned pitch=(job.w*job.bytes+255)&~255U;for(unsigned y=0;y<job.h;++y)std::memcpy(mapped+job.offset+y*pitch,job.data+y*job.w*job.bytes,job.w*job.bytes);}
        SDL_UnmapGPUTransferBuffer(device,staging);auto *copy=SDL_BeginGPUCopyPass(cmd);
        for(const auto &job:jobs){SDL_GPUTextureTransferInfo src{};src.transfer_buffer=staging;src.offset=job.offset;src.pixels_per_row=((job.w*job.bytes+255)&~255U)/job.bytes;src.rows_per_layer=job.h;
            SDL_GPUTextureRegion dst{};dst.texture=job.texture;dst.w=job.w;dst.h=job.h;dst.d=1;SDL_UploadToGPUTexture(copy,&src,&dst,true);}
        SDL_EndGPUCopyPass(copy);
    }
    pendingUiUploads.clear();
    controlBytes+=total;
    SDL_GPURenderPass *pass=nullptr;
    const auto beginPass=[&](){
        SDL_GPUColorTargetInfo color{};color.texture=target;color.load_op=SDL_GPU_LOADOP_LOAD;color.store_op=SDL_GPU_STOREOP_STORE;
        auto *result=SDL_BeginGPURenderPass(cmd,&color,1,nullptr);SDL_BindGPUGraphicsPipeline(result,pipeline);
        SDL_GPUViewport viewport{0,0,float(pixelW),float(pixelH),0,1};SDL_SetGPUViewport(result,&viewport);++renderPasses;return result;
    };
    if(batch)pass=beginPass();
    SDL_GPUGraphicsPipeline *boundPipeline=pipeline;
    slotIndex=0;
    for(const auto &draw:draws){const auto &slot=controls[slotIndex++];auto *mask=slot.mask,*light=slot.light,*pal=slot.palette;
        if(!batch){pass=beginPass();boundPipeline=pipeline;}
        auto *desiredPipeline=draw.panel?uiCachePipeline:(draw.ui?uiPipeline:pipeline);
        if(boundPipeline!=desiredPipeline){SDL_BindGPUGraphicsPipeline(pass,desiredPipeline);boundPipeline=desiredPipeline;}
        if(draw.ui){light=draw.panel?draw.sheet->pages[0].texture:draw.uiIndices->pages[0].texture;if(draw.coverage.empty())mask=light;}
        const auto &page=draw.sheet->pages[draw.frame.page];
        SDL_GPUTextureSamplerBinding bindings[5]={{page.texture,sampler},{mask,sampler},{light,sampler},{pal,sampler},{draw.uiIndices?draw.uiIndices->pages[0].texture:light,sampler}};SDL_BindGPUFragmentSamplers(pass,0,bindings,draw.panel?2:(draw.ui?4:5));
        if(!draw.ui)SDL_BindGPUFragmentStorageBuffers(pass,0,&nearestBuffer,1);
        const float vertex[12]={draw.x,draw.y,draw.w,draw.h,float(draw.frame.x)/page.width,float(draw.frame.y)/page.height,float(draw.frame.w)/page.width,float(draw.frame.h)/page.height,float(logicalW),float(logicalH),0,0};
        const float fragment[16]={float(draw.maskX),float(draw.maskY),float(draw.maskW),float(draw.maskH),draw.alpha,(draw.ui?draw.uiHd:bool(draw.uiIndices))?1.0f:0.0f,draw.uiScaleX,draw.uiScaleY,draw.uiX,draw.uiY,draw.uiIndices?float(draw.uiIndices->width):0,draw.uiIndices?float(draw.uiIndices->height):0,draw.ui&&draw.coverage.empty()?1.0f:0.0f,0,0,0};
        SDL_PushGPUVertexUniformData(cmd,0,vertex,sizeof(vertex));SDL_PushGPUFragmentUniformData(cmd,0,fragment,sizeof(fragment));
        SDL_DrawGPUPrimitives(pass,6,1,0,0);if(!batch)SDL_EndGPURenderPass(pass);++drawCount;

    }
    if(batch)SDL_EndGPURenderPass(pass);
    static unsigned profileFrames=0;
    if(SDL_getenv("D1R_PROFILE_HD")&&++profileFrames%100==0)devilution::Log("GPU_ACTOR_BATCH enabled={} draws={} render_passes={} palette_uploads={} control_bytes={} mask_uploads={} implicit_ui_draws={}",batch,drawCount,renderPasses,paletteUploads,controlBytes,maskUploads,implicitUiDraws);
}
}
#endif
