Texture2D<float4> palette : register(t0, space0);
SamplerState pointSampler : register(s0, space0);
RWByteAddressBuffer outputIndex : register(u0, space1);
groupshared float3 colors[256];
[numthreads(256,1,1)]
void main(uint3 id:SV_DispatchThreadID,uint3 local:SV_GroupThreadID) {
    colors[local.x]=round(palette.Load(int3(local.x,0,0)).rgb*255);
    GroupMemoryBarrierWithGroupSync();
    uint key=id.x+(id.y<<16);
    float3 source=float3(key&255,(key>>8)&255,(key>>16)&255);
    float best=1e30;uint match=0;
    [loop] for(uint i=0;i<256;i++) {float3 d=colors[i]-source;float distance=dot(d,d);if(distance<best){best=distance;match=i;}}
    outputIndex.Store(key*4,match);
}
