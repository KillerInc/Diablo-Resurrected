"""Install a validated medium artwork revision transactionally, preserving the executable."""
import argparse,copy,json,os,re,shutil
from pathlib import Path
from install_layout_table import sha
from hd_layouts import read_table

def install(pack,art,baseline,game,master,mirror,archive,backup,validation):
 pack,art,baseline,game,master,mirror,archive,backup,validation=map(Path,(pack,art,baseline,game,master,mirror,archive,backup,validation))
 assets=json.loads((pack/'validated-gpu-pack.json').read_text());before_assets=json.loads((baseline/'validated-gpu-pack.json').read_text());art=json.loads(art.read_text());proof=json.loads(validation.read_text());hd=(game/'HD').resolve();exe=game/'Diablo Reincarnated.exe';exe_hash=sha(exe)
 assert proof['executable_sha256']==exe_hash and proof['checks']['gpu_sprites'] and proof['checks']['medium_visual_review'] and proof['checks']['medium_live_draw']
 assert proof['checks']['gameplay_reference_same'] and proof['checks']['gameplay_reference_repeat_same'] and proof['checks']['gpu_index_process_cache']
 assert art['model_sha256']==proof['medium_model_sha256'] and len(art['sheets'])==85
 assert proof['gpu_sprites']['pack_file_hashes']==assets['files']
 assert json.loads(master.read_text())==json.loads(mirror.read_text())
 for name,digest in before_assets['source_png_hashes'].items():assert sha(hd/name)==digest,('Installed PNG changed since baseline',name)
 for name,digest in before_assets['files'].items():assert sha(hd/name)==digest,('Installed GPU resource changed since baseline',name)
 assert sha(hd/'layouts.csv')==before_assets['layout_sha256']
 for name,digest in assets['files'].items():assert sha(pack/'HD'/name)==digest
 # A complete medium rebuild must preserve every non-medium pack resource.
 assert all(assets['source_png_hashes'][n]==h for n,h in before_assets['source_png_hashes'].items() if not n.startswith('plrgfx/warrior/wm'))
 assert all(assets['files'].get(n)==h for n,h in before_assets['files'].items() if n!='sprites.gpus' and not n.startswith('plrgfx/warrior/wm'))
 assert not backup.exists() and not archive.exists();backup.mkdir(parents=True);archive.mkdir(parents=True)
 old_master,old_mirror=master.read_bytes(),mirror.read_bytes();(backup/'previous-install-manifest.json').write_bytes(old_master);(backup/'previous-mirror-manifest.json').write_bytes(old_mirror)
 written=[];old={};temps=[]
 def replace(source,target,label):
  target=target.resolve()
  if target.exists() and sha(source)==sha(target):return
  if target.exists():
   saved=backup/'files'/label;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,saved);old[target]=saved
  written.append(target);target.parent.mkdir(parents=True,exist_ok=True);temporary=target.with_name(target.name+'.medium-new');assert not temporary.exists();temps.append(temporary);shutil.copy2(source,temporary);os.replace(temporary,target);assert sha(source)==sha(target)
 try:
  updated=copy.deepcopy(json.loads(old_master));table=read_table(pack/'HD/layouts.csv')
  for name,record in sorted(art['sheets'].items()):
   assert re.fullmatch('wm[a-z]{3}',name)
   relative=f'plrgfx/warrior/{name[:3]}/{name}.png';source=Path(record['source']);assert sha(source)==record['sha256']==assets['source_png_hashes'][relative];assert table[relative]==record['layout']
   saved=archive/'Final'/name[:3]/(name+'.png');saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,saved)
   target=(hd/relative).resolve();assert target.is_relative_to(hd)
   replace(saved,target,'game/'+relative);replace(saved,mirror.parent/(name+'.png'),'mirror/'+name+'.png')
   updated['sheets'][name]={'source':str(saved.resolve()),'size':record['size'],'sha256':record['sha256'],'layout':record['layout'],'status':'approved medium armor; approved complete motion; native 4x GPU resource available'}
  for name,digest in assets['files'].items():
   assert name=='sprites.gpus' or name.endswith('.bc7')
   target=(hd/name).resolve();assert target.is_relative_to(hd)
   if name=='sprites.gpus':continue
   replace(pack/'HD'/name,target,'game/'+name)
  # Retire only obsolete medium pages. Their exact prior bytes remain in backup.
  for target in sorted((hd/'plrgfx/warrior').rglob('*.bc7')):
   relative=target.relative_to(hd).as_posix()
   if not relative.startswith('plrgfx/warrior/wm') or relative in assets['files']:continue
   target=target.resolve();assert target.is_relative_to(hd);saved=backup/'files/game'/relative;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,saved);old[target]=saved;written.append(target);target.unlink()
  replace(pack/'HD/layouts.csv',hd/'layouts.csv','game/layouts.csv');replace(pack/'HD/sprites.gpus',hd/'sprites.gpus','game/sprites.gpus')
  assert sha(exe)==exe_hash and all(sha(hd/n)==h for n,h in assets['files'].items())
  assert all(sha(hd/n)==h for n,h in assets['source_png_hashes'].items())
  assert sha(hd/'layouts.csv')==assets['layout_sha256'] and not list(hd.rglob('*.layout'))
  receipt={'revision':art.get('revision','medium-v1'),'model_sha256':art['model_sha256'],'sheets':85,'custom_sheet_count':len(updated['sheets']),'gpu_sheets':assets['sheets'],'gpu_pages':assets['pages'],'gpu_texture_bytes':assets['texture_bytes'],'executable_unchanged':exe_hash,'layout_sha256':assets['layout_sha256'],'validation':proof['checks'],'archive':str(archive.resolve()),'backup':str(backup.resolve())}
  updated['medium_armor_revision']=receipt;updated['layout_table']={'path':str(hd/'layouts.csv'),'sha256':assets['layout_sha256'],'rows':len(table)}
  data=json.dumps(updated,indent=2).encode();master.write_bytes(data);mirror.write_bytes(data);(archive/'install-manifest.json').write_bytes(data);(archive/'install-receipt.json').write_text(json.dumps(receipt,indent=2));(backup/'install-receipt.json').write_text(json.dumps(receipt,indent=2));shutil.copy2(validation,backup/'validation.json')
 except BaseException:
  for target in reversed(written):
   if target in old:shutil.copy2(old[target],target)
   else:target.unlink(missing_ok=True)
  master.write_bytes(old_master);mirror.write_bytes(old_mirror);raise
 finally:
  for temporary in temps:temporary.unlink(missing_ok=True)
 print('Installed 85 medium sheets and GPU resources; light/heavy, engine and saves preserved')

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('pack','art','baseline','game','master','mirror','archive','backup','validation'):p.add_argument(name,type=Path)
 a=p.parse_args();install(a.pack,a.art,a.baseline,a.game,a.master,a.mirror,a.archive,a.backup,a.validation)
