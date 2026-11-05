"""Native town special-leaf placement for offline combined artwork review.

Mirror InitTownPieces and scrollrt's delayed leaf pass. Special cells are
bottom-aligned 64x224 sprites, separate from the 32x32 terrain microcells.
This module never changes runtime maps or sprite alpha.
"""
import numpy as np
from PIL import Image

SPECIAL = {359:1,357:2,128:6,129:7,127:8,116:9,156:10,157:11,
           155:12,161:13,159:14,213:15,211:16,216:17,215:18}


def special_layers(layers):
    cells={tuple(l['cell']):l['piece'] for l in layers}
    return [dict(cell=[x,z],piece=p,frame=SPECIAL[p],
                 world=[32*(x-z)-32,16*(x+z)-223],special=True)
            for (x,z),p in cells.items() if p in SPECIAL]


def scene_region(meta,atlas,special,rect,*,instance_tiles=None):
    """Return RGBA and canonical pixel owners for BOTH installed town sheets.

    Owner 0 is unpaintable; terrain uses its ordinary linear atlas address +1;
    special sprites follow the terrain atlas in the same address space.
    Instance tiles are preview-only RGBA replacements keyed by (x, z, block).
    Their pixels have no canonical source address in the shared atlas.
    """
    density=meta['density'];cell=meta['cell'];rows=meta['rows']
    if special.size!=(64*density,224*density*18):raise ValueError('Invalid towns geometry')
    left,top,width,height=rect;image=Image.new('RGBA',(width*density,height*density))
    owners=np.zeros((image.height,image.width),np.uint32)
    layers=[*meta['layers'],*special_layers(meta['layers'])]
    # The special at (x,z) is drawn while processing (x+1,z+1), after terrain.
    layers.sort(key=lambda l:(sum(l['cell'])+(2 if l.get('special') else 0),
                              l['cell'][0]+(1 if l.get('special') else 0),
                              99 if l.get('special') else l['block']))
    for l in layers:
        f=l['frame'];x=(l['world'][0]-left)*density;y=(l['world'][1]-top)*density
        if l.get('special'):
            w,h=64*density,224*density;ax,ay=0,(f-1)*h
            src=special;offset=atlas.width*atlas.height
        else:
            w=h=cell;c,r=divmod(f-1,rows);ax,ay=c*cell,r*cell
            src=atlas;offset=0
        x0,y0=max(0,x),max(0,y);x1,y1=min(image.width,x+w),min(image.height,y+h)
        if x1<=x0 or y1<=y0:continue
        sx,sy=x0-x,y0-y
        override = None if not instance_tiles or l.get('special') else instance_tiles.get((*l['cell'],l['block']))
        if override is not None:
            tile=override.crop((sx,sy,sx+x1-x0,sy+y1-y0))
        else:
            tile=src.crop((ax+sx,ay+sy,ax+sx+x1-x0,ay+sy+y1-y0))
        image.alpha_composite(tile,(x0,y0));alpha=np.asarray(tile)[:,:,3]
        yy,xx=np.mgrid[ay+sy:ay+sy+y1-y0,ax+sx:ax+sx+x1-x0]
        address=offset+yy*src.width+xx+1;dest=owners[y0:y1,x0:x1]
        dest[alpha>0]=0
        if override is None:
            opaque=alpha==255;dest[opaque]=address[opaque]
    return image,owners
