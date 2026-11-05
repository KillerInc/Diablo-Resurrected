"""python SCRIPT VALIDATED_BOW_IDLE_PLAN.json
Create an aligned before/after GIF from original and corrected private sheets.
"""
import sys,json
from pathlib import Path
from PIL import Image,ImageDraw
Image.MAX_IMAGE_PIXELS=None
plan=json.loads(Path(sys.argv[1]).read_text());work=Path(plan['work']);review=work/'review';review.mkdir(exist_ok=True);new=json.loads((work/'pack-validation.json').read_text())['sheets'];images={};rows={'wlbas':8,'wlbst':20}
for name in rows:
 for kind,r in [('Before',plan['starting_custom_manifest']['sheets'][name]),('After',new[name])]:
  path=Path(r.get('path',r.get('source')));im=Image.open(path).convert('RGBA');anchor=list(map(int,r['layout'].split()[2:]));images[name,kind]=(im,anchor)
frames=[];size=384;factor=size/(112*8)
for tick in range(40):
 canvas=Image.new('RGB',(size*2,(size+28)*2),(32,32,32));draw=ImageDraw.Draw(canvas)
 for row,name in enumerate(rows):
  for col,kind in enumerate(['Before','After']):
   im,anchor=images[name,kind];cw=im.width//8;ch=im.height//rows[name];r=(tick//2)%rows[name];t=im.crop((2*cw,r*ch,3*cw,(r+1)*ch));dx=size/2-anchor[0]*8*factor;dy=size*.82-(anchor[1]-16)*8*factor;t=t.transform((size,size),Image.Transform.AFFINE,(1/factor,0,-dx/factor,0,1/factor,-dy/factor),resample=Image.Resampling.BICUBIC);bg=Image.new('RGBA',(size,size),(32,32,32,255));bg.alpha_composite(t);canvas.paste(bg.convert('RGB'),(col*size,row*(size+28)+28));draw.text((col*size+10,row*(size+28)+8),('Dungeon idle' if row==0 else 'Town idle')+' - '+kind+' - West',fill='white')
 frames.append(canvas)
frames[0].save(review/'bow-idle-before-after.gif',save_all=True,append_images=frames[1:],duration=100,loop=0,disposal=2);frames[0].save(review/'bow-idle-before-after.png')
