"""Private installed-medium versus vanilla GIF gallery; never writes game data."""
import argparse,json,sys,html,zipfile,gc
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from gpu_index import read_index
from hd_layouts import read_table

p=argparse.ArgumentParser(description=__doc__)
for key in ('game_hd','vanilla','output'):p.add_argument(key,type=Path)
a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True);Image.MAX_IMAGE_PIXELS=None;index=read_index(a.game_hd/'sprites.gpus');layouts=read_table(a.game_hd/'layouts.csv');scale=.5
weapons={'s':'Sword','m':'Mace','a':'Two-handed axe','b':'Bow','t':'Staff'};actions={'as':'Dungeon idle','aw':'Dungeon walk','at':'Attack','ht':'Taking a hit','fm':'Fire cast','lm':'Lightning cast','qm':'Other magic cast','st':'Town idle','wl':'Town walk'};records={};extents=[0,0,0,0]
for code in weapons:
 for action in actions:
  name='wm'+code+action;rel=f'plrgfx/warrior/{name[:3]}/{name}.png';header=index[rel][0].split();columns,rows,lw,lh=map(int,header[2:6]);density,ax,ay=map(int,layouts[rel].split()[1:]);current=a.game_hd/rel;vanilla=a.vanilla/rel
  with Image.open(current) as im:cw,ch=im.width//columns,im.height//rows;assert im.width%columns==im.height%rows==0
  with Image.open(vanilla) as im:vw,vh=im.width//columns,im.height//rows;assert im.width%columns==im.height%rows==0
  assert cw==lw*density and ch==lh*density and columns==8
  ca=(ax*density,(ay-16)*density);va=(vw/2,vh-128)
  for w,h,anchor in [(cw,ch,ca),(vw,vh,va)]:
   extents=[max(extents[0],anchor[0]*scale),max(extents[1],anchor[1]*scale),max(extents[2],(w-anchor[0])*scale),max(extents[3],(h-anchor[1])*scale)]
  records[name]={'current':str(current),'vanilla':str(vanilla),'rows':rows,'columns':columns,'cell':[cw,ch],'vanilla_cell':[vw,vh],'anchor':ca,'vanilla_anchor':va}
left,top,right,bottom=extents;pw=max(800,round(left+right+64));ph=max(800,round(top+bottom+110));ground=(round(left+32),round(top+60));font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',25);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20);manifest=[];gallery=[]

def frame(cur,van,record,direction,row,label):
 canvas=Image.new('RGB',(pw*2,ph),(25,25,25));draw=ImageDraw.Draw(canvas)
 for col,atlas,key,ak,resample in [(0,cur,'cell','anchor',Image.Resampling.LANCZOS),(1,van,'vanilla_cell','vanilla_anchor',Image.Resampling.NEAREST)]:
  cw,ch=record[key];anchor=record[ak];cell=atlas.crop((direction*cw,row*ch,(direction+1)*cw,(row+1)*ch)).resize((round(cw*scale),round(ch*scale)),resample);x=col*pw+round(ground[0]-anchor[0]*scale);y=round(ground[1]-anchor[1]*scale);assert x>=col*pw and x+cell.width<=(col+1)*pw and y>=45 and y+cell.height<ph-25;canvas.paste(cell,(x,y),cell)
 draw.text((20,12),'Current medium - '+label,font=font,fill='white');draw.text((pw+20,12),'Vanilla NN-x8',font=font,fill='white');draw.text((20,ph-35),f'{["S","SW","W","NW","N","NE","E","SE"][direction]} | frame {row+1}/{record["rows"]}',font=small,fill='white');return canvas.quantize(colors=256,method=Image.Quantize.FASTOCTREE)

def save(frames,path,durations):frames[0].save(path,save_all=True,append_images=frames[1:],duration=durations,loop=0,optimize=False,disposal=2)
for code,weapon in weapons.items():
 overview=[];timing=[];links=[]
 for action,title in actions.items():
  name='wm'+code+action;record=records[name]
  with Image.open(record['current']) as im:cur=im.convert('RGBA')
  with Image.open(record['vanilla']) as im:van=im.convert('RGBA')
  frames=[frame(cur,van,record,0,row,weapon+' - '+title) for row in range(record['rows'])];duration=160 if action in ('as','st') else 85;filename=name+'-vs-vanilla.gif';save(frames,a.output/filename,[duration]*len(frames));overview.extend(frames);timing.extend([duration]*len(frames));timing[-1]=500;links.append((title,filename));manifest.append({'sheet':name,'weapon':weapon,'action':title,'rows':record['rows'],'direction':'South','gif':filename,'installed_png':record['current'],'vanilla_png':record['vanilla']});print('MEDIUM_COMPARISON',name,flush=True)
  if action=='as':
   rotation=[frame(cur,van,record,d,r,weapon+' - Dungeon idle') for d in range(8) for r in range(record['rows'])];save(rotation,a.output/(code+'-idle-rotation.gif'),[85]*len(rotation));del rotation
  cur.close();van.close();gc.collect()
 save(overview,a.output/(code+'-all-animations.gif'),timing);del overview;gallery.append((weapon,code,links));gc.collect()
body=['<!doctype html><html><meta charset="utf-8"><title>Medium weapons versus vanilla</title><style>body{background:#181818;color:#eee;font:18px Arial;margin:24px}img{max-width:100%;height:auto}details{margin:18px 0}a{color:#a8cfff}</style><h1>Medium weapons versus vanilla</h1><p>Current installed medium on the left; original vanilla NN-x8 on the right. No shields. Individual animations show South; idle rotations cover all eight directions. Native row counts are preserved. Death uses a shared weaponless sheet and is not duplicated here.</p>']
for weapon,code,links in gallery:
 body.append(f'<h2>{html.escape(weapon)}</h2><p><a href="{code}-all-animations.gif">All animations</a> | <a href="{code}-idle-rotation.gif">Eight-direction idle rotation</a></p>')
 for title,filename in links:body.append(f'<details><summary>{html.escape(title)}</summary><a href="{filename}">Open GIF</a><br><img loading="lazy" src="{filename}"></details>')
body.append('</html>');(a.output/'index.html').write_text('\n'.join(body),encoding='utf-8');(a.output/'comparison-manifest.json').write_text(json.dumps({'sheets':manifest,'individual_gifs':45,'overview_gifs':5,'rotations':5,'native_frame_counts':True,'display_scale_from_nn8':scale,'frame_size':[pw*2,ph]},indent=2));
with zipfile.ZipFile(a.output/'Medium-weapons-vs-vanilla.zip','w',compression=zipfile.ZIP_STORED) as z:
 for file in a.output.iterdir():
  if file.suffix in ('.gif','.html','.json'):z.write(file,file.name)
print('MEDIUM_GALLERY_DONE 45 individual, 5 overviews, 5 rotations',flush=True)
