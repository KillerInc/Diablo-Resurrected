"""python SCRIPT VALIDATED_BOW_IDLE_PLAN.json
Make a rotating eight-direction GIF of the two private final idle sheets.
"""
from pathlib import Path
from PIL import Image,ImageDraw
import json,sys
Image.MAX_IMAGE_PIXELS=None
p=json.loads(Path(sys.argv[1]).read_text());w=Path(p['work']);records=json.loads((w/'pack-validation.json').read_text())['sheets'];out=w/'review';out.mkdir(exist_ok=True);images={};size=480;scale=1
for name in ['wlbas','wlbst']:
 r=records[name];images[name]=(Image.open(r['path']).convert('RGBA'),list(map(int,r['layout'].split()[2:])),r['rows'])
limits=[]
for im,anchor,rows in images.values():
 cw=im.width//8;ch=im.height//rows;gx=anchor[0]*8;gy=(anchor[1]-16)*8
 for d in range(8):
  box=im.crop((d*cw,0,(d+1)*cw,ch)).getbbox();limits.extend([(size/2-12)/max(abs(box[0]-gx),abs(box[2]-gx),1),(size*.8-12)/max(gy-box[1],1),(size*.2-12)/max(box[3]-gy,1)])
scale=min(limits)
frames=[]
for d,label in enumerate(['South','Southwest','West','Northwest','North','Northeast','East','Southeast']):
 frame=Image.new('RGB',(size*2,size+28),(32,32,32));draw=ImageDraw.Draw(frame)
 for col,name in enumerate(['wlbas','wlbst']):
  im,anchor,rows=images[name];cw=im.width//8;ch=im.height//rows;t=im.crop((d*cw,0,(d+1)*cw,ch));dx=size/2-anchor[0]*8*scale;dy=size*.8-(anchor[1]-16)*8*scale;t=t.transform((size,size),Image.Transform.AFFINE,(1/scale,0,-dx/scale,0,1/scale,-dy/scale),resample=Image.Resampling.BICUBIC);bg=Image.new('RGBA',(size,size),(32,32,32,255));bg.alpha_composite(t);frame.paste(bg.convert('RGB'),(col*size,28));draw.text((col*size+12,9),('Dungeon idle' if col==0 else 'Town idle')+' - '+label,fill='white')
 frames.append(frame)
frames[0].save(out/'bow-idles-rotating.gif',save_all=True,append_images=frames[1:],duration=400,loop=0,disposal=2)
im=Image.open(out/'bow-idles-rotating.gif')
for i in range(im.n_frames):im.seek(i);im.load()
assert im.n_frames==8
