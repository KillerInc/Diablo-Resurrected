"""python SCRIPT QUIVER_FIT_PLAN.json
Create a private before/after close-up GIF of the quiver's back fit.
"""
from pathlib import Path
from PIL import Image,ImageDraw
import sys,json
p=json.loads(Path(sys.argv[1]).read_text());w=Path(p['work']);out=w/'review';out.mkdir(exist_ok=True);frames=[]
for name,title in [('before','Before'),('after','Closer back fit')]:
 im=Image.open(w/'quiver-preview'/(name+'.png')).convert('RGB');frame=Image.new('RGB',(im.width,im.height+28),(32,32,32));frame.paste(im,(0,28));ImageDraw.Draw(frame).text((12,8),title,fill='white');frames.append(frame)
frames[0].save(out/'quiver-before-after.gif',save_all=True,append_images=frames[1:],duration=1400,loop=0,disposal=2)
im=Image.open(out/'quiver-before-after.gif')
for i in range(im.n_frames):im.seek(i);im.load()
assert im.n_frames==2
