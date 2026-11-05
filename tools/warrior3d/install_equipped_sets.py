"""Install a validated private equipment pack, with exact backups and receipts.

python SCRIPT PLAN.json ARCHIVE_DIRECTORY
Requires the complete pack report and unchanged starting game sheets. Does not
modify the executable or remove existing unarmed/custom assets.
"""
import copy,datetime,hashlib,json,shutil,sys
from pathlib import Path

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()

def install(plan_path,archive):
 plan=json.loads(Path(plan_path).read_text());work=Path(plan['work']);report=json.loads((work/'pack-validation.json').read_text());assert report['sheet_count']==29 and len(report['sheets'])==29
 game=Path(plan['game']);live=game/'HD/plrgfx/warrior';manifest=Path(plan['previous'])/'paladin-vanilla-dimensions/install-manifest.json';original_manifest=manifest.read_bytes();current=json.loads(original_manifest);assert current==plan['starting_custom_manifest'],'Custom manifest changed during build'
 for name,record in current['sheets'].items():assert sha(live/name[:3]/(name+'.png'))==record['sha256'].upper(),('Previously approved sheet changed',name)
 for name,expected in plan['starting_game_hashes'].items():assert sha(live/name[:3]/(name+'.png'))==expected,('Live sheet changed during build',name)
 for name,record in report['sheets'].items():
  p=Path(record['path']);assert sha(p)==record['sha256'];assert p.with_name(p.name+'.layout').read_text().strip()==record['layout']
 executable=game/'Diablo Reincarnated.exe';exe_before=sha(executable);stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S');archive=Path(archive);assert not archive.exists(),'Use a new archive directory';backup=archive/'previous-installed';final=archive/'Final/plrgfx/warrior';receipt={'date':stamp,'executable_sha256':exe_before,'version':current['version'],'sheet_count':29,'sheets':report['sheets'],'unarmed_preserved':True,'shared_death_preserved':True}
 archive.mkdir(parents=True);(archive/'previous-install-manifest.json').write_bytes(original_manifest)
 for name,record in report['sheets'].items():
  target=live/name[:3]/(name+'.png');b=backup/name[:3]/target.name;f=final/name[:3]/target.name;b.parent.mkdir(parents=True,exist_ok=True);f.parent.mkdir(parents=True,exist_ok=True)
  for suffix in ['', '.layout']:
   old=target.with_name(target.name+suffix)
   if old.exists():shutil.copy2(old,b.with_name(b.name+suffix))
   source=Path(record['path']).with_name(Path(record['path']).name+suffix);shutil.copy2(source,f.with_name(f.name+suffix))
 shutil.copytree(work/'review',archive/'Review');shutil.copy2(work/'pack-validation.json',archive/'pack-validation.json');shutil.copy2(work/'preflight-progress.json',archive/'pose-validation.json')
 changed=[]
 try:
  for name,record in report['sheets'].items():
   target=live/name[:3]/(name+'.png');source=final/name[:3]/target.name
   if sha(target)!=record['sha256']:
    changed.append(name)
    for suffix in ['', '.layout']:shutil.copy2(source.with_name(source.name+suffix),target.with_name(target.name+suffix))
   assert sha(target)==record['sha256'];assert target.with_name(target.name+'.layout').read_text().strip()==record['layout']
  for name,record in current['sheets'].items():assert sha(live/name[:3]/(name+'.png'))==record['sha256'].upper(),('Approved sheet unexpectedly changed',name)
  assert sha(executable)==exe_before
  updated=copy.deepcopy(current)
  for name,record in report['sheets'].items():
   if name not in updated['sheets']:updated['sheets'][name]={'source':str(final/name[:3]/(name+'.png')),'size':record['size'],'sha256':record['sha256'],'layout':record['layout']}
  assert len(updated['sheets'])==39
  updated['equipped_sets']={'archive':str(archive),'sheet_count':29,'selected_sword':'S1','selected_shield':'H3 Red','existing_approved_mounts_preserved':True,'death':'shared unarmed','report':str(archive/'pack-validation.json')}
  mirror=Path(plan['assets'])/'Vanilla NN8 Dimensions';mirror.mkdir(exist_ok=True)
  for name in report['sheets']:
   source=final/name[:3]/(name+'.png')
   for suffix in ['', '.layout']:shutil.copy2(source.with_name(source.name+suffix),mirror/(source.name+suffix))
  (mirror/'install-manifest.json').write_text(json.dumps(updated,indent=2))
  manifest.write_text(json.dumps(updated,indent=2));(archive/'install-manifest.json').write_text(json.dumps(updated,indent=2));receipt['changed_sheets']=changed;receipt['custom_sheet_count']=39;(archive/'install-receipt.json').write_text(json.dumps(receipt,indent=2));(work/'install-receipt.json').write_text(json.dumps(receipt,indent=2))
 except BaseException:
  for name in changed:
   target=live/name[:3]/(name+'.png');source=backup/name[:3]/target.name
   for suffix in ['', '.layout']:
    old=source.with_name(source.name+suffix)
    if old.exists():shutil.copy2(old,target.with_name(target.name+suffix))
  manifest.write_bytes(original_manifest);raise
 print('Installed 29 equipment sheets; 39 custom sheets verified; executable and approved unarmed sheets unchanged')

if __name__=='__main__':install(*sys.argv[1:])
