// Synthetic GPU proof: compressed sprites, exact colour lookup, ordered
// transparency/occlusion, cursor restore and physical-resolution output.
#include <SDL3/SDL.h>
#include <SDL3_image/SDL_image.h>
#include <filesystem>
#include <fstream>
#include <vector>
#include <array>
#include <bit>
#include <cstdio>
#include "reincarnated/gpu_presenter.hpp"
#include "reincarnated/gpu_sprites.hpp"
#include "reincarnated/hd_renderer.hpp"
#include "engine/surface.hpp"
#include "game_mode.hpp"
#include "options.h"
#include "utils/display.h"
#include "utils/paths.h"
using namespace reincarnated;
static void Check(bool ok,const char *what){if(!ok){std::fprintf(stderr,"FAIL %s: %s\n",what,SDL_GetError());std::exit(1);}}
int main(){
 Check(SDL_Init(SDL_INIT_VIDEO),"video init");
 auto root=std::filesystem::temp_directory_path()/std::filesystem::path("d1r-gpu-synthetic-"+std::to_string(SDL_GetTicksNS()));
 auto folder=root/"hd/plrgfx/warrior/test";std::filesystem::create_directories(folder);
 const unsigned char block[]={32,60,158,199,163,80,0,2,174,170,170,170,86,85,85,85,32,60,158,199,163,80,0,2,174,170,170,170,86,85,85,85,32,60,158,199,163,80,0,2,174,170,170,170,86,85,85,85,32,60,158,199,163,80,0,2,174,170,170,170,86,85,85,85};
 {std::ofstream f(folder/"test.p0.bc7",std::ios::binary);uint32_t dimensions[2]={8,8};f.write(reinterpret_cast<char*>(dimensions),8);f.write(reinterpret_cast<const char*>(block),sizeof(block));}
 {std::ofstream f(root/"hd/sprites.gpus");f<<"D1R_GPU_INDEX_V1\nDEFAULTS 4 1 2 2\nSHEET plrgfx/warrior/test/test.png 1 1 * * * *\ntest.p0.bc7 8 8\n0 0 0 8 8 0 0\n";}
 {std::ofstream f(root/"hd/layouts.csv");f<<"path,layout\nplrgfx/warrior/test/test.png,D1R_SHEET_V1 4 1 2\n";}
 auto monsterFolder=root/"hd/monsters/test";std::filesystem::create_directories(monsterFolder);
 std::filesystem::copy_file(folder/"test.p0.bc7",monsterFolder/"test.p0.bc7");
 {std::ofstream f(root/"hd/sprites.gpus",std::ios::app);f<<"SHEET monsters/test/test.png 1 1 * * * *\ntest.p0.bc7 8 8\n0 0 0 8 8 0 0\n";}
 for(const auto *name:{"authored-off","authored-native","authored-on","authored-bad"}){
  auto npc=root/"hd/towners"/name;std::filesystem::create_directories(npc);
  std::filesystem::copy_file(folder/"test.p0.bc7",npc/"test.p0.bc7");
  {std::ofstream f(root/"hd/sprites.gpus",std::ios::app);f<<"SHEET towners/"<<name<<"/test.png 2 1 * * * *\ntest.p0.bc7 8 8\n0 0 0 8 8 0 0\n0 0 0 8 8 0 0\n";}
  {std::ofstream f(root/"hd/layouts.csv",std::ios::app);f<<"towners/"<<name<<"/test.png,"<<((std::string(name)=="authored-off"||std::string(name)=="authored-native")?"D1R_SHEET_V1":"D1R_AUTHORED_SHEET_V1")<<" 4 1 2\n";}
 }
 // The current-directory pack must retain precedence over pref overrides,
 // even when the data directory aliases the current directory.
 auto pref=root/"pref-override";std::filesystem::create_directories(pref/"hd");
 {std::ofstream f(pref/"hd/sprites.gpus");f<<"D1R_GPU_INDEX_V1\nDEFAULTS 4 1 3 2\nSHEET plrgfx/warrior/test/test.png 1 1 * * * *\nmissing.bc7 8 8\n0 0 0 8 8 0 0\n";}
 const auto previousDirectory=std::filesystem::current_path();
 std::filesystem::current_path(root);devilution::paths::SetBasePath(root.string());devilution::paths::SetPrefPath(pref.string());
 auto *window=SDL_CreateWindow("Synthetic GPU validation",256,256,SDL_WINDOW_HIDDEN);Check(window,"window");
 devilution::gnScreenWidth=128;devilution::gnScreenHeight=128;
 InitializeGpuPresenter(window);(void)GetHdAssetStore();
 auto sheet=LoadGpuSheet(SheetSource{"hd/plrgfx/warrior/test/test.png",1,1,2});Check(bool(sheet),"BC7 load");
 auto playerSheet=sheet;
 sheet=LoadGpuSheet(SheetSource{"hd/monsters/test/test.png",1,1,2});Check(bool(sheet),"monster BC7 load without PNG");
 Check(GetGpuSpriteStats().sheets==2&&GetGpuSpriteStats().playerSheets==1,"separate player and monster residency");
 Check(sheet->bytes==64&&sheet->anchorX==1&&sheet->anchorY==2,"resident data and anchor");
 auto *surface=SDL_CreateSurface(128,128,SDL_PIXELFORMAT_RGBA32);Check(surface,"base surface");
 SDL_FillSurfaceRect(surface,nullptr,SDL_MapSurfaceRGBA(surface,10,20,30,255));
 auto pixel=[&](int x,int y,unsigned char r,unsigned char g,unsigned char b){auto *p=static_cast<unsigned char*>(surface->pixels)+y*surface->pitch+x*4;p[0]=r;p[1]=g;p[2]=b;p[3]=255;};
 auto draw=[&](int x,int y,int mode=0){GpuSpriteDraw d;d.sheet=sheet;d.frame=sheet->frames[0];d.x=x;d.y=y;d.w=d.h=32;d.maskX=x;d.maskY=y;d.maskW=d.maskH=32;
  d.coverage.assign(32*32*4,0);for(size_t i=3;i<d.coverage.size();i+=4)d.coverage[i]=255;
  d.lighting.assign(32*32,0);d.palette.assign(256*17*4,0);
  for(unsigned level=0;level<17;++level)for(unsigned i=0;i<256;++i){auto *p=d.palette.data()+(level*256+i)*4;p[3]=255;if(i==1){p[0]=level>0&&mode==1?60:120;p[1]=level>0&&mode==1?30:60;p[2]=level>0&&mode==1?10:20;if(level>0&&mode==2){p[0]=p[1]=0;p[2]=200;}}}
  QueueGpuSprite(std::move(d));};
 BeginGpuSpriteFrame();draw(16,16);
 const auto green=std::bit_cast<uint32_t>(SDL_Color{0,200,0,255});std::array<uint32_t,16> greenSpan;greenSpan.fill(green);
 for(int y=24;y<40;++y){MaskGpuSpriteBlendedSpan(24,y,greenSpan.data(),greenSpan.size());for(int x=24;x<40;++x)pixel(x,y,5,110,15);}
 draw(32,32);
 for(int y=40;y<50;++y){MaskGpuSpriteOpaqueSpan(40,y,10);for(int x=40;x<50;++x)pixel(x,y,0,0,200);}
 SaveGpuSpriteCursor();MaskGpuSpritePixel(20,20,0,0,0,255);RestoreGpuSpriteCursor();
 SetGpuSpriteFrameReady(true);devilution::gbRunGame=true;
 Check(SDL_SetEnvironmentVariable(SDL_GetEnvironment(),"D1R_FRAME_DUMP",root.string().c_str(),true),"capture path");
 for(int i=0;i<50;++i)PresentGpuFrame(surface);
 SDL_Surface *image=nullptr;for(const auto &entry:std::filesystem::directory_iterator(root))if(entry.path().extension()==".png")image=IMG_Load(entry.path().string().c_str());
 Check(image&&image->w==256&&image->h==256,"physical output is 2x logical resolution");
 auto expect=[&](int x,int y,int r,int g,int b){Uint8 rr,gg,bb,aa;Check(SDL_ReadSurfacePixel(image,x*2+1,y*2+1,&rr,&gg,&bb,&aa),"read pixel");
  if(std::abs(int(rr)-r)>3||std::abs(int(gg)-g)>3||std::abs(int(bb)-b)>3){std::fprintf(stderr,"pixel %d,%d got %u,%u,%u expected %d,%d,%d\n",x,y,rr,gg,bb,r,g,b);Check(false,"ordered compositing");}};
 expect(8,8,10,20,30);expect(20,20,65,40,25);expect(28,28,32,120,12);expect(60,60,65,40,25);expect(36,44,92,50,22);expect(36,36,76,90,16);expect(44,44,0,0,200);
 Check(GetGpuSpriteStats().draws==100,"two GPU actors per frame");
 SDL_DestroySurface(image);image=nullptr;
 for(int mode=1;mode<=2;++mode){
  BeginGpuSpriteFrame();draw(16,16,mode);SetGpuSpriteFrameReady(true);
  SDL_FillSurfaceRect(surface,nullptr,SDL_MapSurfaceRGBA(surface,10,20,30,255));
  for(const auto &entry:std::filesystem::directory_iterator(root))if(entry.path().extension()==".png")std::filesystem::remove(entry.path());
  for(int i=0;i<100;++i)PresentGpuFrame(surface);
  for(const auto &entry:std::filesystem::directory_iterator(root))if(entry.path().extension()==".png")image=IMG_Load(entry.path().string().c_str());
  Check(image,"lighting/translation capture");
  if(mode==1)expect(20,20,35,25,20);else expect(20,20,5,10,115);
  SDL_DestroySurface(image);image=nullptr;
 }
 Check(GetGpuSpriteStats().draws==300,"GPU lighting and translation draws");
 Check(GetGpuSpriteStats().renderPasses==250,"one ordered actor pass per frame");
 Check(GetGpuSpriteStats().paletteUploads==4,"retain palettes and invalidate lighting/TRN changes");
 // Prepared world art retains exact native indices even when source palette
 // entries have identical RGB. Level colours/TRNs must not use nearest ties.
 std::array<uint8_t,16> native{{2,0,2,255, 2,255,2,255, 2,255,2,255, 0,255,0,255}};
 auto nativeTexture=CreateGpuUiIndices(2,2,native.data());Check(bool(nativeTexture),"native world index texture");
 BeginGpuSpriteFrame();
 GpuSpriteDraw exact;exact.sheet=sheet;exact.uiIndices=nativeTexture;exact.frame=sheet->frames[0];exact.x=exact.y=16;exact.w=exact.h=32;
 exact.uiX=exact.uiY=16;exact.uiScaleX=exact.uiScaleY=1.0f/16;
 exact.maskX=exact.maskY=16;exact.maskW=exact.maskH=32;exact.coverage.assign(32*32*4,0);for(size_t i=3;i<exact.coverage.size();i+=4)exact.coverage[i]=255;
 exact.lighting.assign(32*32,0);exact.palette.assign(256*17*4,0);
 for(unsigned row=0;row<17;++row)for(unsigned index=0;index<256;++index){auto *p=exact.palette.data()+(row*256+index)*4;p[3]=255;
  if(index<3){p[0]=120;p[1]=60;p[2]=20;if(row&&index==2){p[0]=p[2]=0;p[1]=200;}if(row&&index==0){p[0]=p[1]=0;p[2]=200;}}}
 QueueGpuSprite(std::move(exact));SetGpuSpriteFrameReady(true);SDL_FillSurfaceRect(surface,nullptr,SDL_MapSurfaceRGBA(surface,10,20,30,255));
 for(const auto &entry:std::filesystem::directory_iterator(root))if(entry.path().extension()==".png")std::filesystem::remove(entry.path());
 for(int i=0;i<100;++i)PresentGpuFrame(surface);
 for(const auto &entry:std::filesystem::directory_iterator(root))if(entry.path().extension()==".png")image=IMG_Load(entry.path().string().c_str());
 Check(image,"native world colour readback");expect(20,20,10,20,30);expect(36,20,5,110,15);expect(36,36,5,10,115);
 SDL_DestroySurface(image);image=nullptr;BeginGpuSpriteFrame();nativeTexture.reset();
 Check(!LoadGpuSheet(SheetSource{"hd/towners/authored-off/test.png",1,1,2}),"native NPC rejects mismatched frame count by default");
 auto nativeNpc=LoadGpuSheet(SheetSource{"hd/towners/authored-native/test.png",1,2,2});
 Check(nativeNpc&&!nativeNpc->authoredTowner,"unmarked NPC retains native silhouette");
 nativeNpc.reset();
 Check(!LoadGpuSheet(SheetSource{"hd/towners/authored-bad/test.png",1,1,2}),"authored NPC also rejects non-native frame count");
 auto authored=LoadGpuSheet(SheetSource{"hd/towners/authored-on/test.png",1,2,2});
 Check(authored&&authored->authoredTowner&&authored->rows==2,"explicit authored NPC frames and layout without a test flag");
 authored.reset();
 SDL_DestroySurface(surface);
 // Drop every reference before releasing the GPU device.
 BeginGpuSpriteFrame();sheet.reset();playerSheet.reset();ReleaseGpuPlayerSheets();Check(GetGpuSpriteStats().sheets==0,"class release");
 DestroyGpuPresenter();SDL_DestroyWindow(window);SDL_Quit();
 std::filesystem::current_path(previousDirectory);
 Check(std::filesystem::equivalent(root.parent_path(),std::filesystem::temp_directory_path()),"temporary cleanup boundary");
 std::filesystem::remove_all(root);
 std::puts("PASS: synthetic BC7 GPU draw, exact lookup, shader lighting/TRN, native 2x viewport, transparent foreground, ordered actors, opaque coverage, cursor restore and resource release");
}
