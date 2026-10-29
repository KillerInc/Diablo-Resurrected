// Synthetic GPU proof: compressed sprites, exact colour lookup, ordered
// transparency/occlusion, cursor restore and physical-resolution output.
#include <SDL3/SDL.h>
#include <SDL3_image/SDL_image.h>
#include <filesystem>
#include <fstream>
#include <vector>
#include <array>
#include <cstdio>
#include "reincarnated/gpu_presenter.hpp"
#include "reincarnated/gpu_sprites.hpp"
#include "reincarnated/hd_renderer.hpp"
#include "engine/surface.hpp"
#include "game_mode.hpp"
#include "options.h"
#include "utils/display.h"
using namespace reincarnated;
static void Check(bool ok,const char *what){if(!ok){std::fprintf(stderr,"FAIL %s: %s\n",what,SDL_GetError());std::exit(1);}}
int main(){
 Check(SDL_Init(SDL_INIT_VIDEO),"video init");
 auto root=std::filesystem::temp_directory_path()/std::filesystem::path("d1r-gpu-synthetic-"+std::to_string(SDL_GetTicksNS()));
 auto folder=root/"hd/plrgfx/warrior/test";std::filesystem::create_directories(folder);
 const unsigned char block[]={32,60,158,199,163,80,0,2,174,170,170,170,86,85,85,85,32,60,158,199,163,80,0,2,174,170,170,170,86,85,85,85,32,60,158,199,163,80,0,2,174,170,170,170,86,85,85,85,32,60,158,199,163,80,0,2,174,170,170,170,86,85,85,85};
 {std::ofstream f(folder/"test.p0.bc7",std::ios::binary);uint32_t dimensions[2]={8,8};f.write(reinterpret_cast<char*>(dimensions),8);f.write(reinterpret_cast<const char*>(block),sizeof(block));}
 {std::ofstream f(folder/"test.gpus");f<<"D1R_GPU_SHEET_V1 4 1 1 2 2 1\ntest.p0.bc7 8 8\n0 0 0 8 8 0 0\n";}
 {std::ofstream f(root/"hd/layouts.csv");f<<"path,layout\nplrgfx/warrior/test/test.png,D1R_SHEET_V1 4 1 2\n";}
 auto *window=SDL_CreateWindow("Synthetic GPU validation",256,256,SDL_WINDOW_HIDDEN);Check(window,"window");
 devilution::gnScreenWidth=128;devilution::gnScreenHeight=128;
 InitializeGpuPresenter(window);GetHdAssetStore().mountLoose(root.string());
 auto sheet=LoadGpuPlayerSheet(SheetSource{"hd/plrgfx/warrior/test/test.png",1,1,2});Check(bool(sheet),"BC7 load");
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
 for(int y=24;y<40;++y)for(int x=24;x<40;++x){MaskGpuSpritePixel(x,y,0,200,0,128);pixel(x,y,5,110,15);}
 draw(32,32);
 for(int y=40;y<50;++y)for(int x=40;x<50;++x){MaskGpuSpritePixel(x,y,0,0,200,255);pixel(x,y,0,0,200);}
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
 SDL_DestroySurface(image);SDL_DestroySurface(surface);
 // Drop every reference before releasing the GPU device.
 BeginGpuSpriteFrame();sheet.reset();ReleaseGpuPlayerSheets();Check(GetGpuSpriteStats().sheets==0,"class release");
 DestroyGpuPresenter();SDL_DestroyWindow(window);SDL_Quit();
 Check(std::filesystem::equivalent(root.parent_path(),std::filesystem::temp_directory_path()),"temporary cleanup boundary");
 std::filesystem::remove_all(root);
 std::puts("PASS: synthetic BC7 GPU draw, exact lookup, shader lighting/TRN, native 2x viewport, transparent foreground, ordered actors, opaque coverage, cursor restore and resource release");
}
