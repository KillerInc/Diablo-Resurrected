"""Build labelled side-by-side M1/M2 idle and swing GIFs from private previews.

python SCRIPT PRIVATE_PREVIEW_DIRECTORY
"""
import json,sys,math
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
root=Path(sys.argv[1]);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
for action in ['idle','swing']:
 sources=[Image.open(root/f'm{i}-{action}/output/m{i}-{action}-preview.gif') for i in [1,2]];assert sources[0].n_frames==sources[1].n_frames
 records=[json.loads((root/f'm{i}-{action}/output/validation.json').read_text()) for i in [1,2]];boxes=[c['bounds'] for r in records for c in r['cells']];top=max(24,math.floor(min(b[1] for b in boxes)/4+24)-12);bottom=min(376,math.ceil(max(b[3] for b in boxes)/4+24)+12);height=bottom-top;frames=[]
 for row in range(sources[0].n_frames):
  out=Image.new('RGB',(768,3*(height+32)),(35,35,35));draw=ImageDraw.Draw(out)
  for model,source in enumerate(sources):
   source.seek(row);image=source.convert('RGB')
   for direction,name in enumerate(['South','West','Northwest']):
    y=direction*(height+32);draw.text((model*384+10,y+5),f'M{model+1}  {name}  {row+1:02d}',font=font,fill='white');out.paste(image.crop((direction*384,top,(direction+1)*384,bottom)),(model*384,y+32))
  frames.append(out)
 frames[0].save(root/f'mace-{action}-comparison.gif',save_all=True,append_images=frames[1:],duration=200 if action=='idle' else 50,loop=0,optimize=False);frames[0 if action=='idle' else 8].save(root/f'mace-{action}-comparison.png')
print('Saved side-by-side idle and native swing comparisons, M1 left / M2 right')
