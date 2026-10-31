Texture2D<float4> atlas0:register(t0,space2);
Texture2D<float4> atlas1:register(t1,space2);
Texture2D<float4> atlas2:register(t2,space2);
Texture2D<float4> atlas3:register(t3,space2);
Texture2D<float4> atlas4:register(t4,space2);
Texture2D<float4> atlas5:register(t5,space2);
Texture2D<float4> atlas6:register(t6,space2);
Texture2D<float4> atlas7:register(t7,space2);
Texture2D<uint> owners:register(t8,space2);
Texture2D<float4> indices:register(t9,space2);
Texture2D<uint> heads:register(t10,space2);
Texture2D<float4> palette:register(t11,space2);
Texture2D<float4> ui:register(t12,space2);
// SDL D3D12 storage descriptors are raw SRVs: use byte-addressed loads.
Texture2D<float> classicImage:register(t13,space2);
ByteAddressBuffer nearestIndex:register(t14,space2);
ByteAddressBuffer commands:register(t15,space2);
ByteAddressBuffer nodes:register(t16,space2);
SamplerState pointSampler:register(s0,space2);
cbuffer Frame:register(b0,space3) {float4 mapping;float4 clipping;float4 options;};
float4 SampleAtlas(uint page,float2 uv) {
    switch(page){
    case 0:return atlas0.SampleLevel(pointSampler,uv,0);
    case 1:return atlas1.SampleLevel(pointSampler,uv,0);
    case 2:return atlas2.SampleLevel(pointSampler,uv,0);
    case 3:return atlas3.SampleLevel(pointSampler,uv,0);
    case 4:return atlas4.SampleLevel(pointSampler,uv,0);
    case 5:return atlas5.SampleLevel(pointSampler,uv,0);
    case 6:return atlas6.SampleLevel(pointSampler,uv,0);
    default:return atlas7.SampleLevel(pointSampler,uv,0);
    }
}
float3 Lit(uint owner,uint packed,float2 nativePosition) {
    uint index=packed&255,originalIndex=(packed>>8)&255,lightLevel=(packed>>16)&255;
    float3 lit=round(palette.Load((packed>>24)!=0?int3(originalIndex,lightLevel+1,0):int3(index,17,0)).rgb*255);
    if(owner==0)return lit;
    uint base=(owner-1)*3;
    uint4 origin=commands.Load4(base*16),crop=commands.Load4((base+1)*16),page=commands.Load4((base+2)*16);
    float2 local=(nativePosition-float2(asint(origin.xy)))*page.y-float2(crop.xy);
    if(any(local<0)||any(local>=float2(crop.zw)))return lit;
    float4 sample=SampleAtlas(page.x,(float2(origin.zw)+local)/float2(page.zw));
    if(sample.a==0)return lit;
    uint3 bytes=(uint3)round(sample.rgb*255);
    uint match=nearestIndex.Load((bytes.r|(bytes.g<<8)|(bytes.b<<16))*4);
    float3 original=round(palette.Load(int3(originalIndex,0,0)).rgb*255);
    if(all(abs((float3)bytes-original)<=1))match=originalIndex;
    original=round(palette.Load(int3(match,0,0)).rgb*255);
    if(match!=originalIndex)lit=round(palette.Load(int3(match,lightLevel+1,0)).rgb*255);
    float intensity=min(256,floor(dot(lit,float3(1,1,1))*256/max(1,dot(original,float3(1,1,1)))));
    return clamp(lit+trunc(((float3)bytes-original)*intensity/256),0,255);
}
float4 main(float4 position:SV_Position,float2 uv:TEXCOORD0,float2 logical:TEXCOORD1):SV_Target0 {
    if(any(logical<clipping.xy)||any(logical>=clipping.xy+clipping.zw)){
        if(options.x!=0){uint color=(uint)round(classicImage.Load(int3(int2(floor(logical)),0))*255);return float4(palette.Load(int3(color,17,0)).rgb,1);}
        discard;
    }
    float2 nativePosition=(logical-float2(mapping.w,0))/mapping.z;
    int2 cell=int2(floor(nativePosition));
    if(any(cell<0)||any(cell>=int2(mapping.xy)))discard;
    uint4 packed=(uint4)round(indices.Load(int3(cell,0))*255);
    uint index=packed.x|(packed.y<<8)|(packed.z<<16)|(packed.w<<24);
    uint owner=owners.Load(int3(cell,0)),node=heads.Load(int3(cell,0));
    // Traverse newest-to-oldest. Powers of two preserve the original ordered
    // 50% blends; floor is applied after accumulating the integer numerator.
    float weight=1;float3 additions=0;
    [loop] while(node!=0){uint4 item=nodes.Load4(node*16);weight*=0.5;additions+=Lit(item.y,item.z,nativePosition)*weight;node=item.x;}
    float3 color=floor(Lit(owner,index,nativePosition)*weight+additions)/255;
    float4 overlay=ui.Load(int3(int2(floor(logical)),0));
    return float4(color*overlay.a+overlay.rgb,1);
}
