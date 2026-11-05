"""Compare original CL2 body silhouettes and Paladin at actual game anchors.

python SCRIPT WORKSPACE ORIGINAL_CL2_DIRECTORY CALIBRATION.json OUTPUT
Cyan is vanilla, magenta is Paladin, white is shared coverage. No fitting to body
bounds, independent resizing or frame-by-frame recentering. Shadows are excluded.
"""
import json,struct,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from prepare_reference import body_mask

workspace,originals,calibration,out=map(Path,sys.argv[1:5]);out.mkdir(parents=True,exist_ok=True)
scale=json.loads(calibration.read_text())['global_pixel_scale']
for action,sheet,frames,logical,duration in [
    ('idle','wlnst',workspace/'paladin-root-aligned/idle/frames',96,200),
    ('walk','wlnwl',workspace/'paladin-root-aligned/walk/frames',96,50),
    ('attack','wlnat',workspace/'paladin-knee/frames-final',128,50),
]:
    info=json.loads((frames/'render.json').read_text());rows=info['output_rows'];origin=info['ground_origin_pixel']
    dx=768-scale*origin[0];dy=1152-scale*origin[1]
    data=(originals/(sheet+'.cl2')).read_bytes();offsets=struct.unpack_from('<8I',data)
    assert all(struct.unpack_from('<I',data,o)[0]==rows for o in offsets)
    previews=[]
    for row in range(rows):
        canvas=Image.new('RGB',(1200,510),(24,24,24));draw=ImageDraw.Draw(canvas)
        for column,(direction,label) in enumerate([(0,'South'),(2,'West'),(4,'North')]):
            vanilla=Image.new('L',(1536,1536))
            original=body_mask(data,offsets[direction],row,width=logical).resize((logical*8,logical*8),Image.Resampling.NEAREST)
            vanilla.paste(original,(int((96-logical/2)*8),(160-logical)*8))
            body=Image.open(frames/f'body-{direction}-{row}.png').getchannel('A')
            body=body.transform((1536,1536),Image.Transform.AFFINE,(1/scale,0,-dx/scale,0,1/scale,-dy/scale),resample=Image.Resampling.BICUBIC)
            a=np.asarray(vanilla,dtype=np.float32)/255;b=np.asarray(body,dtype=np.float32)/255
            rgb=np.full((1536,1536,3),28,dtype=np.float32)
            rgb[:,:,0]+=210*b;rgb[:,:,1]+=210*a;rgb[:,:,2]+=210*np.maximum(a,b)
            tile=Image.fromarray(np.clip(rgb,0,255).astype('uint8'));td=ImageDraw.Draw(tile)
            td.line([(744,1152),(792,1152)],fill=(60,255,120),width=4);td.line([(768,1128),(768,1176)],fill=(60,255,120),width=4)
            view=tile.crop((256,256,1280,1456)).resize((400,469),Image.Resampling.LANCZOS)
            canvas.paste(view,(column*400,25));draw.text((column*400+10,7),label,fill='white')
        draw.text((10,496),f'{action}: cyan = vanilla | magenta = ours | white = overlap | green = tile anchor',fill='white');previews.append(canvas)
    previews[0].save(out/(action+'-overlay.png'))
    previews[0].save(out/(action+'-overlay.gif'),save_all=True,append_images=previews[1:],duration=duration,loop=0,optimize=False)
print('Anchor-matched body overlays saved:',out)
