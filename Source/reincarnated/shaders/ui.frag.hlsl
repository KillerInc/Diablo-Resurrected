Texture2D<float4> image:register(t0,space2);
Texture2D<float4> coverage:register(t1,space2);
Texture2D<float4> indices:register(t2,space2);
Texture2D<float4> palette:register(t3,space2);
SamplerState pointSampler:register(s0,space2);
cbuffer Mask:register(b0,space3){float4 bounds;float4 options;float4 origin;};
float4 main(float4 position:SV_Position,float2 uv:TEXCOORD0,float2 logical:TEXCOORD1):SV_Target0{
 int2 xy=int2(floor(logical))-int2(bounds.xy);
 if(any(xy<0)||any(xy>=int2(bounds.zw)))discard;
 float4 overlay=coverage.Load(int3(xy,0));if(overlay.a==0)discard;
 int2 source=int2(floor((logical-origin.xy)*options.zw));
 if(any(source<0)||any(source>=int2(origin.zw)))discard;
 float4 native=indices.Load(int3(source,0));if(native.g==0)discard;
 uint index=(uint)round(native.r*255);
 uint original=(uint)round(native.b*255);
 float3 base=round(palette.Load(int3(original,0,0)).rgb*255);
 float3 lit=round(palette.Load(int3(index,1,0)).rgb*255);
 float3 color=lit;
 if(options.y!=0&&native.a!=0&&index==original){float4 hd=image.SampleLevel(pointSampler,uv,0);
  if(hd.a!=0){float intensity=min(256,floor(dot(lit,float3(1,1,1))*256/max(1,dot(base,float3(1,1,1)))));
   color=clamp(lit+trunc((round(hd.rgb*255)-base)*intensity/256),0,255);}}
 return float4(saturate(color/255*overlay.a+overlay.rgb),options.x);
}
