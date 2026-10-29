cbuffer Draw : register(b0, space1) { float4 destination; float4 uvrect; float4 screen; };
struct Output { float4 position : SV_Position; float2 uv : TEXCOORD0; float2 logical : TEXCOORD1; };
Output main(uint vertex : SV_VertexID) {
    const float2 corners[6] = {float2(0,0),float2(1,0),float2(0,1),float2(0,1),float2(1,0),float2(1,1)};
    float2 c=corners[vertex]; Output o;
    o.logical=destination.xy+c*destination.zw;
    o.position=float4(o.logical.x/screen.x*2-1,1-o.logical.y/screen.y*2,0,1);
    o.uv=uvrect.xy+c*uvrect.zw; return o;
}
