"""Render and package the local light-warrior sword/shield or mace equipment plan.

python SCRIPT render PLAN.json --blender BLENDER.exe [--workers 2] [--watch]
python SCRIPT validate PLAN.json
Only install after all sheets and review artifacts have passed validation.
"""
import argparse,concurrent.futures,hashlib,json,os,shutil,subprocess,sys,time
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
Image.MAX_IMAGE_PIXELS=None
TOOLS=Path(__file__).resolve().parent

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()

def fingerprint(job):
 ref=json.loads(Path(job['reference']).read_text());parts=[sha(job['model']),sha(job['reference'])]
 parts.extend(sha(TOOLS/name) for name in ['render_paladin_town_walk.py','render_paladin_shadows.py','assemble_paladin_canvas.py','paladin_equipment.py','paladin_fire_effect.py','paladin_fire_bubble.py','paladin_lightning_effect.py','paladin_magic_effect.py','paladin_magic_emitter.py'])
 parts.extend(sha(item['path']) for item in ref.get('equipment',[]));return hashlib.sha256('|'.join(parts).encode()).hexdigest()

def command(args,log):
 with Path(log).open('w',encoding='utf8') as output:
  result=subprocess.run([str(a) for a in args],cwd=TOOLS.parents[1],stdout=output,stderr=subprocess.STDOUT,creationflags=0x08000000 if os.name=='nt' else 0)
 text=Path(log).read_text(errors='replace')
 if result.returncode or 'Traceback (most recent call last)' in text:raise RuntimeError(str(log)+'\n'+text[-1800:])

def render_one(job,plan,blender):
 root=Path(job['root']);ref=json.loads(Path(job['reference']).read_text());mark=root/'completed.json';key=fingerprint(job);png=root/'output'/(job['sheet']+'.png')
 if mark.exists() and png.exists():
  old=json.loads(mark.read_text())
  if old.get('fingerprint')==key and old.get('sha256')==sha(png):return {'sheet':job['sheet'],'cached':True,'sha256':old['sha256']}
 print('START',job['sheet'],flush=True)
 command([blender,'-b','--python',TOOLS/'render_paladin_town_walk.py','--',job['model'],job['reference'],root/'frames'],root/'body.log')
 assert len(list((root/'frames').glob('body-*.png')))==ref['rows']*8,job['sheet']
 command([blender,'-b','--python',TOOLS/'render_paladin_shadows.py','--',root/'frames/Paladin-town-walk-render.blend',root/'frames/render.json',root/'shadows'],root/'shadow.log')
 assert len(list((root/'shadows').glob('shadow-*.png')))==ref['rows']*8,job['sheet']
 command([sys.executable,TOOLS/'assemble_paladin_canvas.py',root/'frames',root/'shadows',root/'frames/render.json',plan['calibration'],root/'output'],root/'assembly.log')
 validation=json.loads((root/'output/validation.json').read_text());assert validation['size']==plan['inventory'][job['code']][job['sheet']]['size'];assert sha(png)==validation['sheet_sha256'].upper()
 record={'sheet':job['sheet'],'fingerprint':key,'sha256':sha(png)};mark.write_text(json.dumps(record,indent=2));print('DONE',job['sheet'],flush=True);return record

def render(plan,blender,workers=2,watch=False):
 work=Path(plan['work']);submitted=set();completed=[];failures=[];futures={};all_jobs=plan['jobs'];state=work/'render-progress.json';state.write_text(json.dumps({'done':completed,'failures':failures},indent=2))
 with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
  while True:
   progress=work/'preflight-progress.json';records=json.loads(progress.read_text()) if progress.exists() else [];ready={r['motion'] for r in records if r['safe']};blocked=any(not r['safe'] for r in records)
   for job in all_jobs:
    if job['sheet'] in submitted:continue
    if job['motion'] in ready and (Path(job['root'])/'preflight.json').exists():futures[pool.submit(render_one,job,plan,blender)]=job['sheet'];submitted.add(job['sheet'])
   for future in list(futures):
    if not future.done():continue
    sheet=futures.pop(future)
    try:completed.append(future.result())
    except Exception as error:failures.append({'sheet':sheet,'error':str(error)});print('FAILED',sheet,str(error),flush=True)
    state.write_text(json.dumps({'done':completed,'failures':failures,'submitted':sorted(submitted),'total':len(all_jobs)},indent=2))
   if not futures:
    if len(submitted)==len(all_jobs) or len(records)==len(plan['motions']) or not watch:break
   time.sleep(1)
 if len(submitted)!=len(all_jobs):raise RuntimeError('Preflight incomplete; rendered '+str(len(submitted))+' ready jobs')
 if failures:raise RuntimeError('Some sheets failed; inspect render-progress.json')
 print('All canonical renders validated',flush=True)

def validate(plan):
 assert not plan.get('attack_only'),'Attack-only revisions must be reviewed and installed as updates, not as a full 29-sheet pack'
 work=Path(plan['work']);pack=work/'pack';pack.mkdir(exist_ok=True);records={};jobs={j['sheet']:j for j in plan['jobs']};source_hashes={str(Path(e['source']).resolve()):e['sha256'] for e in plan['starting_custom_manifest']['sheets'].values()}
 def target(sheet):
  dest=pack/sheet[:3]/(sheet+'.png');dest.parent.mkdir(parents=True,exist_ok=True);return dest
 for sheet,job in jobs.items():
  root=Path(job['root']);ref=json.loads(Path(job['reference']).read_text())
  if ref.get('fire_effect'):
   masks=list((root/'frames/fire-masks').glob('*/maskMask.png'));assert len(masks)==ref['rows']*8,('Missing effect masks',sheet)
  mark=json.loads((root/'completed.json').read_text());assert mark['fingerprint']==fingerprint(job),('Stale render',sheet);source=root/'output'/(sheet+'.png');assert mark['sha256']==sha(source);dest=target(sheet);shutil.copy2(source,dest);shutil.copy2(source.with_name(source.name+'.layout'),dest.with_name(dest.name+'.layout'));record=json.loads((root/'output/validation.json').read_text());record.update(sha256=sha(dest),origin='render',job=job['root']);records[sheet]=record
 pending=list(plan['copies'])
 while pending:
  changed=False
  for item in list(pending):
   sheet=item['sheet'];donor=item.get('source_sheet')
   if donor and donor not in records:continue
   source=target(donor) if donor else Path(item['path']);dest=target(sheet)
   if not donor:assert sha(source)==source_hashes[str(source.resolve())].upper(),('Changed approved source',source)
   if item.get('crop_rows'):
    with Image.open(source) as image:cell=image.width//8;image.crop((0,0,image.width,cell*item['crop_rows'])).save(dest,compress_level=6)
   else:shutil.copy2(source,dest)
   shutil.copy2(source.with_name(source.name+'.layout'),dest.with_name(dest.name+'.layout'));records[sheet]={'sha256':sha(dest),'origin':'alias' if donor else 'approved source','donor':donor or str(source),'crop_rows':item.get('crop_rows')};pending.remove(item);changed=True
  assert changed,'Unresolved alias dependency'
 for code,inventory in plan['inventory'].items():
  for sheet,expected in inventory.items():
   dest=target(sheet)
   with Image.open(dest) as image:assert list(image.size)==expected['size'];assert image.mode=='RGBA';image.verify()
   logical=expected['cell']//8;anchor=expected.get('canvas_anchor',[logical//2,logical]);layout=f'D1R_SHEET_V1 8 {anchor[0]} {anchor[1]}';assert dest.with_name(dest.name+'.layout').read_text().strip()==layout
   records[sheet].update(size=expected['size'],rows=expected['rows'],layout=layout,path=str(dest),sha256=sha(dest))
 expected_count={'light-mace':19,'light-axe':9,'light-town':10,'light-town-stow':8,'light-town-two-hand-back':2,'light-town-bow':2,'light-bow':9,'light-staff':9}.get(plan.get('equipment_family'),29)
 if plan.get('equipment_family')=='full-motion-restoration':
  expected_count=len(plan['restoration_targets']);assert set(records)==set(plan['restoration_targets'])
 assert len(records)==expected_count
 report={'sheets':records,'sheet_count':expected_count,'stored_directional_frames':sum(v['rows']*8 for v in records.values()),'approved_unarmed_preserved':not any(n.startswith('wln') for n in records),'death_shared_unarmed':True,'attack_action_frame':plan.get('attack_action_frame',9),'casting_action_frame':14};(work/'pack-validation.json').write_text(json.dumps(report,indent=2));make_previews(plan,pack);print('Validated complete '+str(expected_count)+'-sheet pack',flush=True);return report

def make_previews(plan,pack):
 work=Path(plan['work']);dest=work/'review';dest.mkdir(exist_ok=True);directions=['S','SW','W','NW','N','NE','E','SE'];priority=['as','aw','at','ht','bl','st','wl','fm','lm','qm','dt']
 for code,inventory in plan['inventory'].items():
  actions=[a for a in priority if code+a in inventory];images={a:Image.open(pack/code/(code+a+'.png')).convert('RGBA') for a in actions}
  anchors={a:list(map(int,(pack/code/(code+a+'.png.layout')).read_text().split()[2:4])) for a in actions}
  def thumbnail(action,direction,row,pixels):
   image=images[action];width=image.width//8;height=image.height//inventory[code+action]['rows'];tile=image.crop((direction*width,row*height,(direction+1)*width,(row+1)*height));factor=pixels/(192*8);anchor=anchors[action];dx=pixels/2-factor*anchor[0]*8;dy=pixels*160/192-factor*(anchor[1]-16)*8;tile=tile.transform((pixels,pixels),Image.Transform.AFFINE,(1/factor,0,-dx/factor,0,1/factor,-dy/factor),resample=Image.Resampling.BICUBIC);bg=Image.new('RGBA',(pixels,pixels),(32,32,32,255));bg.alpha_composite(tile);return bg.convert('RGB')
  size=128;overview=Image.new('RGB',(len(actions)*size,8*(size+24)),(32,32,32));draw=ImageDraw.Draw(overview)
  for col,a in enumerate(actions):
   rows=inventory[code+a]['rows'];row=plan.get('attack_action_frame',9)-1 if a=='at' else 1 if a=='bl' else min(rows-1,13 if a in ['fm','lm','qm'] else rows//2);cell=inventory[code+a]['cell']
   for d in range(8):
    overview.paste(thumbnail(a,d,row,size),(col*size,d*(size+24)+24));draw.text((col*size+5,d*(size+24)+6),a.upper()+' '+directions[d],fill='white')
  overview.save(dest/(code+'-all-actions-all-directions.png'))
  frames=[];thumb=256;cols=4;grid_rows=(len(actions)+cols-1)//cols
  for tick in range(80):
   canvas=Image.new('RGB',(cols*thumb,grid_rows*(thumb+24)),(32,32,32));draw=ImageDraw.Draw(canvas)
   for i,a in enumerate(actions):
    count=inventory[code+a]['rows'];step=4 if a in ['as','st'] else 3 if a=='bl' else 1;row=(tick//step)%count;cell=inventory[code+a]['cell'];x=(i%cols)*thumb;y=(i//cols)*(thumb+24);canvas.paste(thumbnail(a,0,row,thumb),(x,y+24));draw.text((x+8,y+7),code.upper()+' '+a.upper(),fill='white')
   frames.append(canvas)
  frames[0].save(dest/(code+'-all-actions.gif'),save_all=True,append_images=frames[1:],duration=50,loop=0,optimize=False)

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('stage',choices=['render','validate']);parser.add_argument('plan',type=Path);parser.add_argument('--blender');parser.add_argument('--workers',type=int,default=2);parser.add_argument('--watch',action='store_true');args=parser.parse_args();plan=json.loads(args.plan.read_text())
 if args.stage=='render':assert args.blender;render(plan,args.blender,args.workers,args.watch)
 else:validate(plan)

if __name__=='__main__':main()
