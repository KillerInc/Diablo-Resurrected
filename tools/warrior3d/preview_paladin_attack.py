"""Review an attack without cropping overflow or installing a sheet.

python SCRIPT BODY_FRAMES OVERSCAN_SHADOWS CALIBRATION.json OUTPUT_DIRECTORY
Shadows must have 256 pixels of extra camera canvas on every side, at the same
pixels per metre. Red boxes show the original 1024-pixel attack cell boundary.
"""
import json,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFilter

body_root,shadow_root,calibration,out=map(Path,sys.argv[1:5]);out.mkdir(parents=True,exist_ok=True)
cal=json.loads(calibration.read_text());scale=cal['global_pixel_scale']
cell=1024;pad=256;size=cell+2*pad;frames=[];report={'body_overflow':[],'shadow_overflow':[],'cells':[]}
names=['S','SW','W','NW','N','NE','E','SE']
for row in range(16):
    composed=[]
    for direction in range(8):
        dx,dy=cal['fixed_direction_offsets'][direction]
        dx+=(cell-768)/2*(1-scale);dy+=(cell-768)-scale*(cell-768)/2
        body=Image.open(body_root/f'body-{direction}-{row}.png').convert('RGBA');assert body.size==(cell,cell)
        body=body.transform((size,size),Image.Transform.AFFINE,(1/scale,0,-(dx+pad)/scale,0,1/scale,-(dy+pad)/scale),resample=Image.Resampling.BICUBIC)
        a=np.array(body);rgb=a[:,:,:3].astype(np.float32);lum=rgb@np.array([.2126,.7152,.0722],dtype=np.float32)
        a[:,:,:3]=np.clip((lum[:,:,None]+.86*(rgb-lum[:,:,None]))*.62,0,255).astype(np.uint8);body=Image.fromarray(a)
        shadow=Image.open(shadow_root/f'shadow-{direction}-{row}.png');assert shadow.size==(size,size)
        alpha=shadow.getchannel('A').transform((size,size),Image.Transform.AFFINE,(1/scale,0,-(dx+pad)/scale+pad,0,1/scale,-(dy+pad)/scale+pad),resample=Image.Resampling.BICUBIC)
        alpha=alpha.filter(ImageFilter.GaussianBlur(2)).point(lambda x:round(x*.7))
        ground=Image.new('RGBA',(size,size));ground.putalpha(alpha)
        for kind,box in [('body',body.getbbox()),('shadow',alpha.getbbox())]:
            bounds=[box[0]-pad,box[1]-pad,box[2]-pad,box[3]-pad]
            report['cells'].append({'row':row,'direction':names[direction],'kind':kind,'bounds':bounds})
            if min(bounds[:2])<=0 or max(bounds[2:])>=cell:report[kind+'_overflow'].append({'row':row,'direction':names[direction],'bounds':bounds})
        tile=Image.new('RGBA',(size,size),(46,46,46,255));tile=Image.alpha_composite(Image.alpha_composite(tile,ground),body)
        ImageDraw.Draw(tile).rectangle((pad,pad,pad+cell-1,pad+cell-1),outline=(255,65,65,255),width=5);composed.append(tile)
    preview=Image.new('RGB',(1440,530),(32,32,32));draw=ImageDraw.Draw(preview)
    for column,direction in enumerate([0,2,3]):
        preview.paste(composed[direction].resize((480,480),Image.Resampling.LANCZOS).convert('RGB'),(column*480,38))
        draw.text((column*480+12,10),names[direction]+' | sun SE, moving shadow NW',fill='white')
    draw.text((12,518),f'Knee attack: frame {row+1}/16. Red = original sheet boundary. Normal playback speed.',fill='white');frames.append(preview)
    if row==8:
        contact=Image.new('RGB',(384*4,384*2),(32,32,32));cd=ImageDraw.Draw(contact)
        for d in range(8):
            contact.paste(composed[d].resize((384,384),Image.Resampling.LANCZOS).convert('RGB'),((d%4)*384,(d//4)*384));cd.text(((d%4)*384+8,(d//4)*384+8),names[d],fill='white')
        contact.save(out/'knee-contact-eight-directions.png');preview.save(out/'knee-contact.png')
frames[0].save(out/'knee-preview.gif',save_all=True,append_images=frames[1:],duration=50,loop=0,optimize=False)
(out/'bounds.json').write_text(json.dumps(report,indent=2))
print('Review only:',len(report['body_overflow']),'body and',len(report['shadow_overflow']),'shadow cells cross the original boundary')
