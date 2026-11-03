"""Private authoring colour candidate, retaining texture size and fine detail.

Match used source-UV luminance quantiles to the native facade distribution,
then resolve its native median colour at that luminance. This is a reversible
reference look, not an approval of missing windows, materials or geometry.
"""
import numpy as np
from PIL import Image, ImageDraw


def luminance(rgb):
    return np.asarray(rgb,dtype=np.float64) @ np.array([.2126,.7152,.0722])


def match_palette(source, reference, triangles):
    rgb=np.asarray(source.convert('RGB'))
    native=np.asarray(reference.convert('RGBA'))
    source_mask=Image.new('L',source.size)
    draw=ImageDraw.Draw(source_mask)
    for triangle in triangles:
        draw.polygon([(float(u)*source.width,float(v)*source.height) for u,v in triangle],fill=255)
    used=np.asarray(source_mask)>0
    target=native[native[:,:,3]>=250,:3]
    assert np.count_nonzero(used)>0 and len(target)>0
    source_luma=luminance(rgb)
    target_luma=luminance(target)
    q=np.linspace(0,1,257)
    original=np.quantile(source_luma[used],q)
    wanted=np.quantile(target_luma,q)
    unique,indices=np.unique(original,return_index=True)
    mapped=np.interp(source_luma,unique,wanted[indices])
    bins=np.rint(target_luma).astype(int)
    levels=np.unique(bins)
    colours=np.stack([np.median(target[bins==level],axis=0) for level in levels])
    result=np.stack([np.interp(mapped,levels,colours[:,channel]) for channel in range(3)],axis=2)
    result=np.clip(np.rint(result),0,255).astype(np.uint8)
    report=dict(method='source-UV luminance quantiles to native-facade median colours',
                size=list(source.size),source_used_pixels=int(np.count_nonzero(used)),
                source_median_luma=float(np.median(source_luma[used])),
                native_median_luma=float(np.median(target_luma)),
                output_median_luma=float(np.median(luminance(result)[used])),
                source_unchanged=True,approval='candidate')
    return Image.fromarray(result),report
