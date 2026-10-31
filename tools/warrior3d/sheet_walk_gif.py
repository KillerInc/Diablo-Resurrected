"""Make a three-view WHNWL preview from the private NN x8 sheet.

python sheet_walk_gif.py INPUT.png OUTPUT.gif
Eight columns: S, SW, W, NW, N, NE, E, SE. Frames run down rows.
Preview timing matches the Paladin GIF, not a claim about vanilla game speed.
"""
import sys
from pathlib import Path
from PIL import Image,ImageDraw

src,dest=map(Path,sys.argv[1:3]);im=Image.open(src).convert('RGBA')
assert im.size==(6144,6144),'Expected the eight-frame 768px-cell WHNWL NN x8 sheet'
frames=[]
for row in range(8):
 canvas=Image.new('RGBA',(1200,625),(32,32,32,255));draw=ImageDraw.Draw(canvas)
 for panel,(column,label) in enumerate([(0,'Front / South'),(2,'Side / West'),(4,'Back / North')]):
  # Identical crop in each cell preserves the original animation registration.
  crop=im.crop((column*768+120,row*768+128,column*768+520,row*768+720))
  canvas.alpha_composite(crop,(panel*400,29));draw.text((panel*400+12,7),label,fill='white')
 frames.append(canvas.convert('RGB'))
dest.parent.mkdir(parents=True,exist_ok=True)
frames[0].save(dest,save_all=True,append_images=frames[1:],duration=[170,160,170,170,160,170,170,160],loop=0,optimize=False)
frames[0].save(dest.with_suffix('.png'))
with Image.open(dest) as check:assert check.n_frames==8
print('Saved 8-frame front / side / back GIF:',dest)
