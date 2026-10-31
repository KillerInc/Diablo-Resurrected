"""Rotate installed and vanilla weapon idles across all three armor tiers."""
import argparse,json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from gpu_index import read_index
from hd_layouts import read_table
p=argparse.ArgumentParser(description=__doc__)
for name in ['hd','vanilla','output']:p.add_argument(name,type=Path)
p.add_argument('--weapon',choices=['m','s','a','b','t'],default='m');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True);Image.MAX_IMAGE_PIXELS=None
index=read_index(a.hd/'sprites.gpus');layouts=read_table(a.hd/'layouts.csv');labels=['Light','Medium','Heavy'];records=[];extent=[0,0,0,0];scale=.5
for tier,armor in enumerate('lmh'):
 stem='w'+armor+a.weapon+'as';rel=f'plrgfx/warrior/{stem[:3]}/{stem}.png';rows=int(index[rel][0].split()[3]);density,ax,ay=map(int,layouts[rel].split()[1:])
 for version,root in enumerate([a.hd,a.vanilla]):
  path=root/rel
  with Image.open(path) as image:atlas=image.convert('RGBA')
  assert atlas.width%8==atlas.height%rows==0;w,h=atlas.width//8,atlas.height//rows;anchor=(ax*density,(ay-16)*density) if version==0 else (w/2,h-128)
  for i,v in enumerate([anchor[0],anchor[1],w-anchor[0],h-anchor[1]]):extent[i]=max(extent[i],round(v*scale))
  records.append({'tier':tier,'version':version,'path':str(path),'rows':rows,'cell':(w,h),'anchor':anchor,'atlas':atlas})
pw=extent[0]+extent[2]+40;ph=extent[1]+extent[3]+70;ground=(extent[0]+20,extent[1]+45);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',23);frames=[];count=max(r['rows'] for r in records)
for direction in range(8):
 for frame in range(count):
  canvas=Image.new('RGB',(pw*3,ph*2),(30,30,30));draw=ImageDraw.Draw(canvas)
  for r in records:
   w,h=r['cell'];ax,ay=r['anchor'];row=round(frame*(r['rows']-1)/max(1,count-1));cell=r['atlas'].crop((direction*w,row*h,(direction+1)*w,(row+1)*h)).resize((round(w*scale),round(h*scale)),Image.Resampling.LANCZOS if r['version']==0 else Image.Resampling.NEAREST);x=r['tier']*pw+round(ground[0]-ax*scale);y=r['version']*ph+round(ground[1]-ay*scale);assert x>=r['tier']*pw and x+cell.width<=(r['tier']+1)*pw and y>=r['version']*ph+35 and y+cell.height<=(r['version']+1)*ph-15;canvas.paste(cell,(x,y),cell);draw.text((r['tier']*pw+12,r['version']*ph+10),labels[r['tier']]+' - '+['current','vanilla'][r['version']],font=font,fill='white')
  if direction==0 and frame==3:canvas.save(a.output/'comparison-review.png')
  frames.append(canvas.quantize(colors=256,method=Image.Quantize.FASTOCTREE))
frames[0].save(a.output/'mace-three-armor-current-vs-vanilla.gif',save_all=True,append_images=frames[1:],duration=85,loop=0,optimize=False,disposal=2)
(a.output/'manifest.json').write_text(json.dumps({'weapon':a.weapon,'columns':labels,'rows':['current','vanilla NN8'],'direction_order':['S','SW','W','NW','N','NE','E','SE'],'foot_anchors_aligned':True,'scale_from_nn8':scale,'sources':[{k:v for k,v in r.items() if k!='atlas'} for r in records]},indent=2));print('VANILLA_COMPARISON_COMPLETE')
