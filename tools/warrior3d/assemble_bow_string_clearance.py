"""python SCRIPT NEAR_ARM_BOW_PLAN.json
Assemble private close-up GIFs from the two complete idle cycles.
"""
from pathlib import Path
from PIL import Image,ImageDraw
import json,sys
p=json.loads(Path(sys.argv[1]).read_text());w=Path(p['work']);out=w/'review';out.mkdir(exist_ok=True);frames=[]
for tick in range(40):
 frame=Image.new('RGB',(1024,540),(32,32,32));draw=ImageDraw.Draw(frame)
 for col,(name,count) in enumerate([('wlbas',8),('wlbst',20)]):
  row=(tick//2)%count;im=Image.open(w/'closeups/animated'/(name+'-'+str(row)+'.png')).convert('RGB');frame.paste(im,(col*512,28));draw.text((col*512+12,8),('Dungeon idle' if col==0 else 'Town idle')+' - string almost touching inner arm',fill='white')
 frames.append(frame)
frames[0].save(out/'string-arm-closeup.gif',save_all=True,append_images=frames[1:],duration=100,loop=0,disposal=2);frames[0].save(out/'string-arm-closeup.png')
im=Image.open(out/'string-arm-closeup.gif');duration=0
for i in range(im.n_frames):im.seek(i);im.load();duration+=im.info.get('duration',0)
assert duration==4000
