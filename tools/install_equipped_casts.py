"""Transactionally install only validated light/medium equipped casting artwork."""
import argparse,copy,json,os,re,shutil
from pathlib import Path
from install_layout_table import sha
from hd_layouts import read_table

def install(pack,art,baseline,game,master,mirror,archive,backup,validation):
 pack,art,baseline,game,master,mirror,archive,backup,validation=map(Path,(pack,art,baseline,game,master,mirror,archive,backup,validation))
 assets=json.loads((pack/'validated-gpu-pack.json').read_text());before=json.loads((baseline/'validated-gpu-pack.json').read_text());art=json.loads(art.read_text());proof=json.loads(validation.read_text());hd=(game/'HD').resolve();exe_hash=sha(game/'Diablo Reincarnated.exe')
 required=['gpu_sprites','gameplay_reference_same','gameplay_reference_repeat_same','gpu_index_process_cache','casting_bounds','casting_head_clearance','casting_visual_review','casting_live_draw']
 assert all(proof['checks'].get(k) for k in required)
 assert proof['executable_sha256']==exe_hash and proof['gpu_sprites']['pack_file_hashes']==assets['files']
 expected={f'w{a}{w}{s}' for a in 'lm' for w in 'abdhmstu' for s in ('fm','lm','qm')}
 assert set(art['sheets'])==expected and len(expected)==48
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
   assert re.fullmatch(r'w[lm][abdhmstu](fm|lm|qm)',name)
   rel=f'plrgfx/warrior/{name[:3]}/{name}.png';source=Path(record['source']);assert sha(source)==record['sha256']==assets['source_png_hashes'][rel] and table[rel]==record['layout']
   saved=archive/'Final'/name[:3]/(name+'.png');saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,saved)
   replace(saved,hd/rel,'game/'+rel);replace(saved,mirror.parent/(name+'.png'),'mirror/'+name+'.png')
   updated['sheets'][name]={'source':str(saved.resolve()),'size':record['size'],'sha256':record['sha256'],'layout':record['layout'],'status':'approved equipped Fanaticism cast; original effects; complete native motion'}
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
  receipt={'revision':'equipped-casts-v1','sheets':48,'unarmed_unchanged':True,'noncasting_unchanged':True,'heavy_unchanged':True,'executable_unchanged':exe_hash,'gpu_pages':assets['pages'],'gpu_texture_bytes':assets['texture_bytes'],'archive':str(archive.resolve()),'backup':str(backup.resolve()),'checks':proof['checks']}
  updated['equipped_casting_revision']=receipt;updated['layout_table']={'path':str(hd/'layouts.csv'),'sha256':assets['layout_sha256'],'rows':len(table)}
  data=json.dumps(updated,indent=2).encode();master.write_bytes(data);mirror.write_bytes(data);(archive/'install-manifest.json').write_bytes(data);(archive/'install-receipt.json').write_text(json.dumps(receipt,indent=2));(backup/'install-receipt.json').write_text(json.dumps(receipt,indent=2));shutil.copy2(validation,backup/'validation.json')
 except BaseException:
  for target in reversed(written):
   if target in old:shutil.copy2(old[target],target)
   else:target.unlink(missing_ok=True)
  master.write_bytes(old_master);mirror.write_bytes(old_mirror);raise
 finally:
  for temp in temps:temp.unlink(missing_ok=True)
 print('Installed 48 equipped casts; unarmed, all other actions, heavy assets, saves and executable preserved')

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for key in ('pack','art','baseline','game','master','mirror','archive','backup','validation'):p.add_argument(key)
 a=p.parse_args();install(a.pack,a.art,a.baseline,a.game,a.master,a.mirror,a.archive,a.backup,a.validation)
