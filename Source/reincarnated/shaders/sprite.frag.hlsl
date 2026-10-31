Texture2D<float4> image : register(t0, space2);
Texture2D<float4> coverage : register(t1, space2);
Texture2D<float> lighting : register(t2, space2);
Texture2D<float4> palette : register(t3, space2);
ByteAddressBuffer nearestIndex : register(t4, space2);
SamplerState pointSampler : register(s0, space2);
SamplerState unused1 : register(s1, space2);
SamplerState unused2 : register(s2, space2);
SamplerState unused3 : register(s3, space2);
cbuffer Mask : register(b0, space3) { float4 bounds; float4 options; };
float4 main(float4 position:SV_Position,float2 uv:TEXCOORD0,float2 logical:TEXCOORD1):SV_Target0 {
    int2 xy=int2(floor(logical))-int2(bounds.xy);
    if(any(xy<0)||any(xy>=int2(bounds.zw))) discard;
    float4 overlay=coverage.Load(int3(xy,0)); if(overlay.a==0) discard;
    float4 src=image.SampleLevel(pointSampler,uv,0); if(src.a==0) discard;
    uint3 sourceBytes=(uint3)round(src.rgb*255);
    float3 source=(float3)sourceBytes;
    uint match=nearestIndex.Load((sourceBytes.r | (sourceBytes.g<<8) | (sourceBytes.b<<16))*4);
    uint level=(uint)round(lighting.Load(int3(xy,0))*255);
    float3 base=round(palette.Load(int3(match,0,0)).rgb*255);
    float3 lit=round(palette.Load(int3(match,level+1,0)).rgb*255);
    float intensity=min(256,floor(dot(lit,float3(1,1,1))*256/max(1,dot(base,float3(1,1,1)))));
    float3 color=clamp(lit+trunc((source-base)*intensity/256),0,255)/255;
    return float4(saturate(color*overlay.a+overlay.rgb),src.a*options.x);
}
