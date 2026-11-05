#include "gpu_coverage.hpp"
#include <cassert>
#include <cmath>
int main(){
 uint8_t m[4]={0,0,0,255};reincarnated::ApplyGpuCoverage(m,200,100,50,128);
 assert(m[0]==100&&m[1]==50&&m[2]==25&&m[3]==127);
 for(int alpha=0;alpha<=255;alpha+=17){
  const double original=(80.0*alpha+20.0*(255-alpha))/255;
  const double reference=(original*127+200*128)/255;
  const double actor=(80.0*m[3]/255+m[0])*alpha/255;
  const double base=(20.0*127/255+200.0*128/255)*(255-alpha)/255;
  assert(std::abs(actor+base-reference)<1.1);
 }
 reincarnated::ApplyGpuCoverage(m,10,20,30,255);assert(m[3]==0&&m[0]==10&&m[1]==20&&m[2]==30);
}
