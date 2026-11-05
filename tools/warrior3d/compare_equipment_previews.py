"""Build labelled side-by-side M1/M2 idle and swing GIFs from private previews.

python SCRIPT PRIVATE_PREVIEW_DIRECTORY
"""
import json,sys,math
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
root=Path(sys.argv[1]);prefix=sys.argv[2] if len(sys.argv)>2 else 'm';assert prefix in ['m','a'];family='axe' if prefix=='a' else 'mace';font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
for action in ['idle','swing']:
 sources=[Image.open(root/f'{prefix}{i}-{action}/output/{prefix}{i}-{action}-preview.gif') for i in [1,2]];assert sources[0].n_frames==sources[1].n_frames;view_width=sources[0].width//3;frame_limit=sources[0].height-32
 records=[json.loads((root/f'{prefix}{i}-{action}/output/validation.json').read_text()) for i in [1,2]];boxes=[c['bounds'] for r in records for c in r['cells']];top=max(24,math.floor(min(b[1] for b in boxes)/4+24)-12);bottom=min(frame_limit,math.ceil(max(b[3] for b in boxes)/4+24)+12);height=bottom-top;frames=[]
 for row in range(sources[0].n_frames):
  out=Image.new('RGB',(view_width*2,3*(height+32)),(35,35,35));draw=ImageDraw.Draw(out)
  for model,source in enumerate(sources):
   source.seek(row);image=source.convert('RGB')
   for direction,name in enumerate(['South','West','Northwest']):
    y=direction*(height+32);draw.text((model*view_width+10,y+5),f'{prefix.upper()}{model+1}  {name}  {row+1:02d}',font=font,fill='white');out.paste(image.crop((direction*view_width,top,(direction+1)*view_width,bottom)),(model*view_width,y+32))
  frames.append(out)
 frames[0].save(root/f'{family}-{action}-comparison.gif',save_all=True,append_images=frames[1:],duration=200 if action=='idle' else (133 if prefix=='a' else 50),loop=0,optimize=False);frames[0 if action=='idle' else (3 if prefix=='a' else 8)].save(root/f'{family}-{action}-comparison.png')
print('Saved side-by-side idle and swing comparisons:',prefix.upper()+'1 left / '+prefix.upper()+'2 right')
