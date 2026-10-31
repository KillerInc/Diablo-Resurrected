"""python SCRIPT REFERENCE_POSE_PLAN.json
Assemble an eight-direction rotating pose preview, without changing game files.
"""
from pathlib import Path
from PIL import Image,ImageDraw
import sys,json
p=json.loads(Path(sys.argv[1]).read_text());w=Path(p['work']);out=w/'review';out.mkdir(exist_ok=True);frames=[]
for d,label in enumerate(['South','Southwest','West','Northwest','North','Northeast','East','Southeast']):
 frame=Image.new('RGB',(900,478),(32,32,32));draw=ImageDraw.Draw(frame)
 for col,name in enumerate(['wlbas','wlbst']):
  im=Image.open(w/'reference-preview'/(name+'-rotate-'+str(d)+'.png')).convert('RGB').resize((450,450),Image.Resampling.LANCZOS);frame.paste(im,(450*col,28));draw.text((col*450+10,8),('Dungeon idle' if col==0 else 'Town idle')+' - '+label,fill='white')
 frames.append(frame)
frames[0].save(out/'reference-pose-rotating.gif',save_all=True,append_images=frames[1:],duration=400,loop=0,disposal=2)
im=Image.open(out/'reference-pose-rotating.gif')
for i in range(im.n_frames):im.seek(i);im.load()
assert im.n_frames==8
