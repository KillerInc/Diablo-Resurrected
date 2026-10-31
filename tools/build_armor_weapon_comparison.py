"""Compare installed weapon sheets across all three armor tiers; artwork stays private."""
import argparse,gc,hashlib,json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from gpu_index import read_index
from hd_layouts import read_table

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('hd',type=Path);p.add_argument('output',type=Path);p.add_argument('--weapon',choices=['m','s','a','b','t'],default='m');a=p.parse_args()
a.output.mkdir(parents=True,exist_ok=True);Image.MAX_IMAGE_PIXELS=None
index=read_index(a.hd/'sprites.gpus');layouts=read_table(a.hd/'layouts.csv');armors={'l':'Light','m':'Medium','h':'Heavy'}
weapon={'m':'Mace','s':'Sword','a':'Axe','b':'Bow','t':'Staff'}[a.weapon]
actions={'as':'Dungeon idle','aw':'Dungeon walk','at':'Attack','ht':'Taking a hit','fm':'Fire cast','lm':'Lightning cast','qm':'Other magic cast','st':'Town idle','wl':'Town walk'}
records={};extent=[0,0,0,0];scale=.375
for action in actions:
 for armor in armors:
  stem='w'+armor+a.weapon+action;rel=f'plrgfx/warrior/{stem[:3]}/{stem}.png';header=index[rel][0].split();cols,rows,lw,lh=map(int,header[2:6]);density,ax,ay=map(int,layouts[rel].split()[1:]);assert cols==8
  cw,ch=lw*density,lh*density;anchor=(ax*density,(ay-16)*density);path=a.hd/rel
  with Image.open(path) as im:assert im.size==(cw*cols,ch*rows)
  records[(armor,action)]={'path':str(path),'rows':rows,'cell':[cw,ch],'anchor':anchor,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
  for i,v in enumerate([anchor[0],anchor[1],cw-anchor[0],ch-anchor[1]]):extent[i]=max(extent[i],round(v*scale))
pw=extent[0]+extent[2]+48;ph=extent[1]+extent[3]+100;ground=(extent[0]+24,extent[1]+60)
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',25);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20)

def render(atlases,action,direction,phase):
 canvas=Image.new('RGB',(pw*3,ph),(25,25,25));draw=ImageDraw.Draw(canvas);mapping=[]
 for column,(armor,label) in enumerate(armors.items()):
  r=records[(armor,action)];row=round(phase*(r['rows']-1));mapping.append(row);cw,ch=r['cell'];ax,ay=r['anchor'];cell=atlases[armor].crop((direction*cw,row*ch,(direction+1)*cw,(row+1)*ch));cell=cell.resize((round(cw*scale),round(ch*scale)),Image.Resampling.LANCZOS);x=column*pw+round(ground[0]-ax*scale);y=round(ground[1]-ay*scale);assert x>=column*pw and x+cell.width<=(column+1)*pw and y>=45 and y+cell.height<=ph-30;canvas.paste(cell,(x,y),cell);draw.text((column*pw+20,12),label+' | '+weapon,font=font,fill='white')
 draw.text((20,ph-32),actions[action]+' | '+['S','SW','W','NW','N','NE','E','SE'][direction]+' | synchronized animation phase',font=small,fill='white')
 return canvas.quantize(colors=256,method=Image.Quantize.FASTOCTREE),mapping

def save(frames,path,timing):frames[0].save(path,save_all=True,append_images=frames[1:],duration=timing,loop=0,optimize=False,disposal=2)
all_frames=[];all_timing=[];manifest=[]
for action in actions:
 atlases={}
 for armor in armors:
  with Image.open(records[(armor,action)]['path']) as im:atlases[armor]=im.convert('RGBA')
 count=max(records[(armor,action)]['rows'] for armor in armors);frames=[];mappings=[]
 for i in range(count):
  frame,mapping=render(atlases,action,0,i/max(1,count-1));frames.append(frame);mappings.append(mapping)
 duration=130 if action in ('as','st') else 85;name=weapon.lower()+'-'+action+'-all-armor.gif';save(frames,a.output/name,[duration]*count);all_frames.extend(frames);all_timing.extend([duration]*count);all_timing[-1]=500
 manifest.append({'action':action,'gif':name,'source_rows':{k:records[(k,action)]['rows'] for k in armors},'source_frame_mapping':mappings})
 if action=='as':
  rotation=[]
  for d in range(8):
   for i in range(count):rotation.append(render(atlases,action,d,i/max(1,count-1))[0])
  save(rotation,a.output/(weapon.lower()+'-idle-rotation-all-armor.gif'),[85]*len(rotation));del rotation
 for im in atlases.values():im.close()
 del atlases;gc.collect();print('ARMOR_COMPARISON',action,flush=True)
save(all_frames,a.output/(weapon.lower()+'-all-animations-all-armor.gif'),all_timing)
(a.output/'manifest.json').write_text(json.dumps({'weapon':weapon,'order':list(armors.values()),'source_pngs':{armor+'-'+act:record for (armor,act),record in records.items()},'animations':manifest,'pixel_scale_from_nn8':scale,'shared_world_anchor':True,'display_size':[pw*3,ph]},indent=2))
print('ARMOR_COMPARISONS_COMPLETE',flush=True)
