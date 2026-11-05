"""Install the selected M1 mace-only and mace/shield sheets with exact backups.

python SCRIPT VALIDATED_MACE_PLAN.json NEW_PRIVATE_ARCHIVE_DIRECTORY
Preserves every existing custom sheet and the modified executable.
"""
import copy,json,shutil,sys
from pathlib import Path
from build_equipped_sets import sha,fingerprint

def install(plan_file,archive):
 plan=json.loads(Path(plan_file).read_text());assert plan.get('equipment_family')=='light-mace' and plan.get('selected_weapon')=='M1';work=Path(plan['work']);report=json.loads((work/'pack-validation.json').read_text());records=report['sheets'];assert report['sheet_count']==len(records)==19 and all(n.startswith(('wlm','wlh')) for n in records)
 audits=json.loads((work/'mace-audit.json').read_text());assert len(audits)==9 and all(not a['contact_rows'] and a['max_grip_error']<.001 for a in audits)
 checks=json.loads((work/'preflight-progress.json').read_text());assert len(checks)==9 and all(c['safe'] for c in checks)
 for j in plan['jobs']:
  mark=json.loads((Path(j['root'])/'completed.json').read_text());assert mark['fingerprint']==fingerprint(j)
 manifest=Path(plan['previous'])/'paladin-vanilla-dimensions/install-manifest.json';before=manifest.read_bytes();current=json.loads(before);assert current==plan['starting_custom_manifest'];assert not set(records)&set(current['sheets']),'Mace sheets already installed; create a revision plan instead'
 live=Path(plan['game'])/'HD/plrgfx/warrior';mirror=Path(plan['assets'])/'Vanilla NN8 Dimensions';exe=Path(plan['game'])/'Diablo Reincarnated.exe';exe_hash=sha(exe)
 for name,r in current['sheets'].items():assert sha(live/name[:3]/(name+'.png'))==r['sha256'].upper(),name
 for name,r in records.items():
  p=Path(r['path']);assert sha(p)==r['sha256'];assert p.with_name(p.name+'.layout').read_text().strip()==r['layout'];assert sha(live/name[:3]/p.name)==plan['starting_game_hashes'][name],('Target changed',name)
 archive=Path(archive);assert not archive.exists();archive.mkdir(parents=True);(archive/'previous-install-manifest.json').write_bytes(before);previous={}
 for name,r in records.items():
  source=Path(r['path']);target=archive/'Final'/name[:3]/source.name;target.parent.mkdir(parents=True,exist_ok=True)
  for suffix in ['', '.layout']:shutil.copy2(source.with_name(source.name+suffix),target.with_name(target.name+suffix))
  for kind,path in [('game',live/name[:3]/source.name),('mirror',mirror/source.name)]:
   for suffix in ['', '.layout']:
    old=path.with_name(path.name+suffix);key=kind+'/'+name+suffix;previous[key]=old.exists()
    if old.exists():dest=archive/('previous-'+kind)/name[:3]/old.name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(old,dest)
 updated=copy.deepcopy(current);changed=[]
 try:
  for name,r in records.items():
   source=archive/'Final'/name[:3]/(name+'.png');changed.append(name)
   for target in [live/name[:3]/source.name,mirror/source.name]:
    for suffix in ['', '.layout']:shutil.copy2(source.with_name(source.name+suffix),target.with_name(target.name+suffix))
   updated['sheets'][name]={'source':str(source),'size':r['size'],'layout':r['layout'],'sha256':r['sha256'],'status':'M1 mace, complete native motion; approved body/shield/SE shadows'}
  for name,r in updated['sheets'].items():assert sha(live/name[:3]/(name+'.png'))==r['sha256'].upper(),name
  assert len(updated['sheets'])==len(current['sheets'])+19 and sha(exe)==exe_hash
  receipt={'selected_weapon':'M1 mace_base03.glb','installed_sheets':sorted(records),'previous_custom_sheets_preserved':len(current['sheets']),'custom_sheet_count':len(updated['sheets']),'executable_sha256':exe_hash,'version':current['version'],'archive':str(archive),'game_contact_frame':9,'full_native_body_motion_preserved':True};updated['mace_sets']=receipt;text=json.dumps(updated,indent=2);manifest.write_text(text);(mirror/'install-manifest.json').write_text(text);(archive/'install-manifest.json').write_text(text)
  for name in ['pack-validation.json','mace-audit.json','preflight-progress.json']:shutil.copy2(work/name,archive/name)
  shutil.copytree(work/'review',archive/'Review');(archive/'previous-files.json').write_text(json.dumps(previous,indent=2));(archive/'install-receipt.json').write_text(json.dumps(receipt,indent=2));(work/'install-receipt.json').write_text(json.dumps(receipt,indent=2))
 except BaseException:
  for name in changed:
   for kind,path in [('game',live/name[:3]/(name+'.png')),('mirror',mirror/(name+'.png'))]:
    for suffix in ['', '.layout']:
     target=path.with_name(path.name+suffix)
     if previous[kind+'/'+name+suffix]:shutil.copy2(archive/('previous-'+kind)/name[:3]/target.name,target)
     elif target.exists():target.unlink()
  manifest.write_bytes(before);(mirror/'install-manifest.json').write_bytes(before);raise
 print('Installed 19 M1 mace sheets; '+str(len(current['sheets']))+' earlier custom sheets and executable unchanged')

if __name__=='__main__':install(*sys.argv[1:])
