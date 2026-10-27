"""python SCRIPT MANIFEST GAME_DIR CL2_ROOT OUTPUT_DIR
Export the current installed light-warrior sheets as private review GIFs.
Writes 85 all-direction action GIFs, nine overview GIFs, a gallery and a ZIP.
No game files are changed. Proprietary sheets and derivatives stay out of Git.
"""
import hashlib,html,json,struct,sys,zipfile
from io import BytesIO
from pathlib import Path
from urllib.parse import quote
from PIL import Image,ImageDraw
Image.MAX_IMAGE_PIXELS=None
FAMILIES={'wln':'Unarmed','wlu':'Shield only','wls':'Sword','wld':'Sword and shield','wlm':'Mace','wlh':'Mace and shield','wla':'Two-handed axe','wlb':'Bow','wlt':'Staff'}
ACTIONS={'as':'Dungeon idle','aw':'Dungeon walk','at':'Attack','ht':'Taking a hit','bl':'Block','st':'Town idle','wl':'Town walk','fm':'Fire casting','lm':'Lightning casting','qm':'Other magic','dt':'Death'}
DIRECTIONS=['South','Southwest','West','Northwest','North','Northeast','East','Southeast']

def export(manifest_file,game,cl2_root,out):
 manifest_file=Path(manifest_file);manifest=json.loads(manifest_file.read_text());live=Path(game)/'HD/plrgfx/warrior';cl2_root=Path(cl2_root);out=Path(out).resolve();assert not out.exists();out.mkdir(parents=True);(out/'actions').mkdir();(out/'overviews').mkdir();records=[];groups=[]
 for code,title in FAMILIES.items():
  south={};inventory=[]
  for action,label in ACTIONS.items():
   name=code+action
   if name not in manifest['sheets']:continue
   record=manifest['sheets'][name];path=live/code/(name+'.png');raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest().upper();assert digest==record['sha256'].upper(),('Changed installed sheet',name);layout=path.with_name(path.name+'.layout').read_text().strip();assert layout==record['layout'];parts=layout.split();assert parts[:2]==['D1R_SHEET_V1','8'];anchor=list(map(int,parts[2:]));data=(cl2_root/code/(name+'.cl2')).read_bytes();counts=[struct.unpack_from('<I',data,i)[0] for i in struct.unpack_from('<8I',data)];assert len(set(counts))==1;rows=counts[0];size=320;factor=size/1536;gx=size/2;gy=size*.75;dx=gx-anchor[0]*8*factor;dy=gy-(anchor[1]-16)*8*factor;frames=[];small=[]
   with Image.open(BytesIO(raw)) as image:
    assert image.mode=='RGBA' and list(image.size)==record['size'] and image.width%8==image.height%rows==0;cw=image.width//8;ch=image.height//rows
    assert anchor[0]<=cw/8 and anchor[1]<=ch/8
    # Every complete canvas fits the same world-scale review rectangle.
    assert -anchor[0]>=-96 and cw/8-anchor[0]<=96 and anchor[1]-16<=144 and ch/8-(anchor[1]-16)<=48,(name,'Review canvas too small')
    for row in range(rows):
     frame=Image.new('RGB',(size*4,(size+24)*2+26),(32,32,32));draw=ImageDraw.Draw(frame)
     for d,direction in enumerate(DIRECTIONS):
      tile=image.crop((d*cw,row*ch,(d+1)*cw,(row+1)*ch));tile=tile.transform((size,size),Image.Transform.AFFINE,(1/factor,0,-dx/factor,0,1/factor,-dy/factor),resample=Image.Resampling.BICUBIC);view=Image.new('RGBA',(size,size),(32,32,32,255));view.alpha_composite(tile);view=view.convert('RGB');x=(d%4)*size;y=(d//4)*(size+24);frame.paste(view,(x,y+24));draw.text((x+8,y+7),direction,fill='white')
      if d==0:small.append(view.resize((224,224),Image.Resampling.LANCZOS))
     draw.text((10,(size+24)*2+7),title+' | '+label+' | '+name.upper()+' | frame '+str(row+1)+'/'+str(rows),fill='white');frames.append(frame)
   duration=200 if action in ['as','st'] else 100 if action=='dt' else 50;dest=out/'actions'/(name+'.gif');frames[0].save(dest,save_all=True,append_images=frames[1:],duration=duration,loop=0,optimize=False,disposal=2);south[action]=small;entry={'sheet':name,'family':title,'action':label,'frame_count':rows,'directions':8,'duration_ms':duration,'source_sha256':digest,'source_layout':layout,'gif':str(dest.relative_to(out))};records.append(entry);inventory.append(entry);print('ACTION',name,rows,'frames x 8 directions',flush=True);del frames,raw
  overview=[];columns=4;side=224;grid_rows=(len(inventory)+columns-1)//columns
  for tick in range(80):
   canvas=Image.new('RGB',(columns*side,grid_rows*(side+24)+26),(32,32,32));draw=ImageDraw.Draw(canvas)
   for i,entry in enumerate(inventory):
    a=entry['sheet'][3:];row=(tick//(entry['duration_ms']//50))%entry['frame_count'];x=(i%columns)*side;y=(i//columns)*(side+24);canvas.paste(south[a][row],(x,y+24));draw.text((x+7,y+7),entry['action']+' ['+a.upper()+']',fill='white')
   draw.text((8,grid_rows*(side+24)+7),title+' | South view | installed '+manifest['version'],fill='white');overview.append(canvas)
  dest=out/'overviews'/(code+'-all-animations.gif');overview[0].save(dest,save_all=True,append_images=overview[1:],duration=50,loop=0,optimize=False,disposal=2);groups.append({'code':code,'title':title,'overview':str(dest.relative_to(out)),'actions':inventory});(out/'progress.json').write_text(json.dumps({'finished_families':[g['code'] for g in groups],'action_gifs':len(records)},indent=2));print('OVERVIEW',code,flush=True)
 assert len(records)==85 and len(groups)==9;report={'version':manifest['version'],'action_gifs':85,'overview_gifs':9,'direction_order':DIRECTIONS,'shared_death':'Unarmed death is shared by the other equipment families.','families':groups};(out/'inventory.json').write_text(json.dumps(report,indent=2));shutil_text='85 individual animation GIFs, each with all eight directions.\n9 overview GIFs, each showing every action from South.\nSources are the installed sheets verified against the current manifest.\nDeath is shared from the unarmed set. Bow quiver remains deferred.\nNo game files were changed. Proprietary media must remain private.\n';(out/'README.txt').write_text(shutil_text)
 pages=['<!doctype html><meta charset="utf-8"><title>Light warrior animation GIFs</title><style>body{background:#181818;color:#eee;font:16px system-ui;margin:32px}img{max-width:100%;height:auto}a{color:#f6bb69}details{margin:12px 0}summary{cursor:pointer;padding:10px;background:#292929}h2{margin-top:50px}</style><h1>Light warrior animation GIFs</h1><p>85 individual animations in all eight directions, plus nine South-view overviews. Current installed sheets, including the staff corrections. Death is shared; bow quiver remains deferred.</p>']
 for group in groups:
  pages.append('<h2>'+html.escape(group['title'])+'</h2><img loading="lazy" src="'+quote(group['overview'])+'">')
  for entry in group['actions']:pages.append('<details><summary>'+html.escape(entry['action'])+' — '+entry['sheet'].upper()+' — '+str(entry['frame_count'])+' frames</summary><a href="'+quote(entry['gif'])+'">Open GIF</a><br><img loading="lazy" src="'+quote(entry['gif'])+'"></details>')
 (out/'index.html').write_text('\n'.join(pages),encoding='utf-8');archive=out.parent/(out.name+'.zip');assert not archive.exists()
 with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=3) as z:
  for path in sorted(out.rglob('*')):
   if path.is_file():z.write(path,Path(out.name)/path.relative_to(out))
 print('COMPLETE',len(records),'action GIFs, nine overviews;',archive,flush=True)
if __name__=='__main__':export(*sys.argv[1:])
