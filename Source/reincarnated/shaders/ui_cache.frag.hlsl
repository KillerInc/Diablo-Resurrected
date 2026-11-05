Texture2D<float4> image:register(t0,space2);
Texture2D<float4> coverage:register(t1,space2);
SamplerState pointSampler:register(s0,space2);
cbuffer Mask:register(b0,space3){float4 bounds;float4 options;float4 origin;float4 controls;};
float4 main(float4 position:SV_Position,float2 uv:TEXCOORD0,float2 logical:TEXCOORD1):SV_Target0{
 int2 xy=int2(floor(logical))-int2(bounds.xy);
 if(any(xy<0)||any(xy>=int2(bounds.zw)))discard;
 float4 overlay=controls.x!=0?float4(0,0,0,1):coverage.Load(int3(xy,0));
 if(overlay.a==0)discard;
 float4 color=image.SampleLevel(pointSampler,uv,0);
 // The retained target stores premultiplied colour, including ghosted weapons.
 return float4((color.rgb*overlay.a+overlay.rgb*color.a)*options.x,color.a*options.x);
}
