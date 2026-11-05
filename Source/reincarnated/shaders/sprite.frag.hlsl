Texture2D<float4> image : register(t0, space2);
Texture2D<float4> coverage : register(t1, space2);
Texture2D<float> lighting : register(t2, space2);
Texture2D<float4> palette : register(t3, space2);
Texture2D<float4> nativeIndices : register(t4, space2);
ByteAddressBuffer nearestIndex : register(t5, space2);
SamplerState pointSampler : register(s0, space2);
SamplerState unused1 : register(s1, space2);
SamplerState unused2 : register(s2, space2);
SamplerState unused3 : register(s3, space2);
cbuffer Mask : register(b0, space3) {
    float4 bounds; float4 options; float4 origin;
    float4 effects; float4 outlineColor; float4 frameRect; float4 pageSize;
};
float silhouetteAlpha(int2 pixel) {
    // Never sample the neighbouring packed frame, including at page edges.
    if(any(pixel<int2(frameRect.xy))||any(pixel>=int2(frameRect.xy+frameRect.zw)))return 0;
    return image.Load(int3(pixel,0)).a;
}
float4 main(float4 position:SV_Position,float2 uv:TEXCOORD0,float2 logical:TEXCOORD1):SV_Target0 {
    int2 xy=int2(floor(logical))-int2(bounds.xy);
    if(any(xy<0)||any(xy>=int2(bounds.zw))) discard;
    float4 overlay=coverage.Load(int3(xy,0)); if(overlay.a==0) discard;
    if(effects.y>0){
        int2 pixel=int2(floor(uv*pageSize.xy));
        // Ground shadows are authored at 70% opacity; only the opaque actor
        // silhouette contributes to selection, including antialiased edges.
        if(silhouetteAlpha(pixel)>=0.8)discard;
        bool edge=false;
        [loop] for(int d=1;d<=int(effects.y);++d){
            edge=edge||silhouetteAlpha(pixel+int2(d,0))>=0.8||silhouetteAlpha(pixel-int2(d,0))>=0.8
                ||silhouetteAlpha(pixel+int2(0,d))>=0.8||silhouetteAlpha(pixel-int2(0,d))>=0.8;
        }
        if(!edge)discard;
        return float4(saturate(outlineColor.rgb*overlay.a+overlay.rgb),outlineColor.a*options.x);
    }
    float4 src=image.SampleLevel(pointSampler,uv,0); if(src.a==0) discard;
    uint3 sourceBytes=(uint3)round(src.rgb*255);
    float3 source=(float3)sourceBytes;
    uint match; bool detail=true;
    if(options.y!=0){
        int2 pos=int2(floor((logical-origin.xy)*options.zw));
        if(any(pos<0)||any(pos>=int2(origin.zw)))discard;
        float4 native=nativeIndices.Load(int3(pos,0));if(native.g==0)discard;
        match=(uint)round(native.r*255);detail=native.a!=0;
    }else match=nearestIndex.Load((sourceBytes.r | (sourceBytes.g<<8) | (sourceBytes.b<<16))*4);
    uint level=(uint)round(lighting.Load(int3(xy,0))*255);
    float3 base=round(palette.Load(int3(match,0,0)).rgb*255);
    float3 lit=round(palette.Load(int3(match,level+1,0)).rgb*255);
    float intensity=min(256,floor(dot(lit,float3(1,1,1))*256/max(1,dot(base,float3(1,1,1)))));
    if(!detail)source=base;
    float3 color=clamp(lit+trunc((source-base)*intensity/256),0,255)/255;
    return float4(saturate(color*overlay.a+overlay.rgb),src.a*options.x);
}
