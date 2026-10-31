"""Transactionally install only validated light/medium equipped casting artwork."""
import argparse,copy,json,os,re,shutil
from pathlib import Path
from install_layout_table import sha
from hd_layouts import read_table

def install(pack,art,baseline,game,master,mirror,archive,backup,validation,revision='equipped-casts-v1'):
 pack,art,baseline,game,master,mirror,archive,backup,validation=map(Path,(pack,art,baseline,game,master,mirror,archive,backup,validation))
 assets=json.loads((pack/'validated-gpu-pack.json').read_text());before=json.loads((baseline/'validated-gpu-pack.json').read_text());art=json.loads(art.read_text());proof=json.loads(validation.read_text());hd=(game/'HD').resolve();exe_hash=sha(game/'Diablo Reincarnated.exe')
 assert revision in ('equipped-casts-v1','fire-bubble-v2','spell-effects-v2','medium-shield-v1','heavy-v1','heavy-colour-v2')
 required=['gpu_sprites','gameplay_reference_same','gameplay_reference_repeat_same','gpu_index_process_cache']
 required+=['casting_bounds','casting_head_clearance','casting_visual_review','casting_live_draw'] if revision=='equipped-casts-v1' else ['fire_bounds','fire_anchor_fixed','fire_mesh_stable','fire_visual_review','fire_live_draw','character_motion_unchanged']
 if revision=='medium-shield-v1':required=required[:4]+['shield_bounds','shield_visual_review','shield_live_draw','character_motion_unchanged']
 if revision in ('heavy-v1','heavy-colour-v2'):required=required[:4]+['heavy_bounds','heavy_head_clearance','heavy_visual_review','heavy_live_draw','heavy_material_roundtrip','character_motion_unchanged']
 if revision=='spell-effects-v2':required+=['lightning_growth','lightning_paths_fixed','lightning_geometry_held','lightning_visual_review']
 assert all(proof['checks'].get(k) for k in required)
 assert proof['executable_sha256']==exe_hash and proof['gpu_sprites']['pack_file_hashes']==assets['files']
 expected={f'w{a}{w}{s}' for a in 'lm' for w in 'abdhmstu' for s in ('fm','lm','qm')} if revision=='equipped-casts-v1' else {f'w{a}{w}{s}' for a in 'lm' for w in 'abdhmnstu' for s in (('fm','lm') if revision=='spell-effects-v2' else ('fm',))}
 if revision=='medium-shield-v1':expected={f'wm{w}{action}' for w in 'dhu' for action in ('as','at','aw','bl','fm','ht','lm','qm','st','wl')}
 if revision in ('heavy-v1','heavy-colour-v2'):
  expected={Path(n).stem for n in before['source_png_hashes'] if n.startswith('plrgfx/warrior/wh')};assert len(expected)==85
 assert set(art['sheets'])==expected
 assert json.loads(master.read_text())==json.loads(mirror.read_text())
 for name,digest in before['source_png_hashes'].items():assert sha(hd/name)==digest,('Installed PNG changed',name)
 for name,digest in before['files'].items():assert sha(hd/name)==digest,('Installed GPU file changed',name)
 assert sha(hd/'layouts.csv')==before['layout_sha256']
 for name,digest in assets['files'].items():assert sha(pack/'HD'/name)==digest
 changed={f'plrgfx/warrior/{n[:3]}/{n}.png' for n in expected}
 assert all(assets['source_png_hashes'][n]==h for n,h in before['source_png_hashes'].items() if n not in changed)
 assert not archive.exists() and not backup.exists();archive.mkdir(parents=True);backup.mkdir(parents=True)
 old_master=master.read_bytes();old_mirror=mirror.read_bytes();(backup/'previous-install-manifest.json').write_bytes(old_master)
 old={};written=[];temps=[]
 def replace(src,target,label):
  target=target.resolve()
  if target.exists() and sha(src)==sha(target):return
  if target.exists():
   saved=backup/'files'/label;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,saved);old[target]=saved
  written.append(target);target.parent.mkdir(parents=True,exist_ok=True);temp=target.with_name(target.name+'.cast-new');assert not temp.exists();temps.append(temp);shutil.copy2(src,temp);os.replace(temp,target);assert sha(src)==sha(target)
 try:
  updated=copy.deepcopy(json.loads(old_master));table=read_table(pack/'HD/layouts.csv')
  for name,record in sorted(art['sheets'].items()):
   assert name in expected
   rel=f'plrgfx/warrior/{name[:3]}/{name}.png';source=Path(record['source']);assert sha(source)==record['sha256']==assets['source_png_hashes'][rel] and table[rel]==record['layout']
   saved=archive/'Final'/name[:3]/(name+'.png');saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,saved)
   replace(saved,hd/rel,'game/'+rel);replace(saved,mirror.parent/(name+'.png'),'mirror/'+name+'.png')
   status='approved equipped Fanaticism cast; original effects; complete native motion' if revision=='equipped-casts-v1' else ('approved larger fire voids; fixed cast-start anchor; unchanged character motion' if name.endswith('fm') else 'approved staggered growing lightning; held fixed paths; unchanged character motion')
   if revision=='medium-shield-v1':status='approved medium kite shield; original character motion and installed spell effects retained'
   if revision in ('heavy-v1','heavy-colour-v2'):status='approved supplied black heavy warrior; approved native motion and equipment; southeast shadows'
   if revision=='heavy-colour-v2':status='approved Colour heavy warrior +1.0 EV; approved native motion and equipment; southeast shadows'
   updated['sheets'][name]={'source':str(saved.resolve()),'size':record['size'],'sha256':record['sha256'],'layout':record['layout'],'status':status}
  for name in assets['files']:
   assert name=='sprites.gpus' or name.endswith('.bc7')
   target=(hd/name).resolve();assert target.is_relative_to(hd)
   if name!='sprites.gpus':replace(pack/'HD'/name,target,'game/'+name)
  for target in (hd/'plrgfx/warrior').rglob('*.bc7'):
   rel=target.relative_to(hd).as_posix()
   if target.stem.split('.')[0] not in expected or rel in assets['files']:continue
   saved=backup/'files/game'/rel;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,saved);old[target.resolve()]=saved;written.append(target.resolve());target.unlink()
  replace(pack/'HD/layouts.csv',hd/'layouts.csv','game/layouts.csv');replace(pack/'HD/sprites.gpus',hd/'sprites.gpus','game/sprites.gpus')
  assert sha(game/'Diablo Reincarnated.exe')==exe_hash
  assert all(sha(hd/n)==h for n,h in assets['files'].items())
  assert all(sha(hd/n)==h for n,h in assets['source_png_hashes'].items())
  assert not list(hd.rglob('*.layout')) and len(list(hd.rglob('*.gpus')))==1
  receipt={'revision':revision,'sheets':len(expected),'unarmed_unchanged':revision in ('equipped-casts-v1','medium-shield-v1'),'unarmed_motion_unchanged':True,'noncasting_unchanged':revision not in ('medium-shield-v1','heavy-v1','heavy-colour-v2'),'heavy_unchanged':revision not in ('heavy-v1','heavy-colour-v2'),'executable_unchanged':exe_hash,'gpu_pages':assets['pages'],'gpu_texture_bytes':assets['texture_bytes'],'archive':str(archive.resolve()),'backup':str(backup.resolve()),'checks':proof['checks']}
  key={'equipped-casts-v1':'equipped_casting_revision','fire-bubble-v2':'fire_bubble_revision','spell-effects-v2':'spell_effects_revision','medium-shield-v1':'medium_shield_revision','heavy-v1':'heavy_warrior_revision','heavy-colour-v2':'heavy_warrior_revision'}[revision]
  updated[key]=receipt;updated['layout_table']={'path':str(hd/'layouts.csv'),'sha256':assets['layout_sha256'],'rows':len(table)}
  data=json.dumps(updated,indent=2).encode();master.write_bytes(data);mirror.write_bytes(data);(archive/'install-manifest.json').write_bytes(data);(archive/'install-receipt.json').write_text(json.dumps(receipt,indent=2));(backup/'install-receipt.json').write_text(json.dumps(receipt,indent=2));shutil.copy2(validation,backup/'validation.json')
 except BaseException:
  for target in reversed(written):
   if target in old:shutil.copy2(old[target],target)
   else:target.unlink(missing_ok=True)
  master.write_bytes(old_master);mirror.write_bytes(old_mirror);raise
 finally:
  for temp in temps:temp.unlink(missing_ok=True)
 print('Installed',len(expected),revision,'sheets; character motions, nonselected sheets, saves and executable preserved')

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for key in ('pack','art','baseline','game','master','mirror','archive','backup','validation'):p.add_argument(key)
 p.add_argument('--revision',choices=['equipped-casts-v1','fire-bubble-v2','spell-effects-v2','medium-shield-v1','heavy-v1','heavy-colour-v2'],default='equipped-casts-v1')
 a=p.parse_args();install(a.pack,a.art,a.baseline,a.game,a.master,a.mirror,a.archive,a.backup,a.validation,a.revision)
