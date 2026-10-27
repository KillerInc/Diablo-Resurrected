"""python SCRIPT VALIDATED_STAFF_PLAN.json NEW_PRIVATE_ARCHIVE
Install nine new light-warrior staff sheets with exact backups and rollback.
"""
import json,copy,shutil,sys
from pathlib import Path
from build_equipped_sets import sha,fingerprint
def install(plan_file,archive):
 plan=json.loads(Path(plan_file).read_text());assert plan['equipment_family']=='light-staff' and plan['selected_weapon']=='T1';work=Path(plan['work']);report=json.loads((work/'pack-validation.json').read_text());records=report['sheets'];expected={'wlt'+a for a in ['as','aw','at','ht','st','wl','fm','lm','qm']};assert set(records)==expected and report['sheet_count']==9 and report['attack_action_frame']==11
 checks=json.loads((work/'preflight-progress.json').read_text());audit=json.loads((work/'town-audit.json').read_text());assert len(checks)==9 and all(r['safe'] for r in checks);assert len(audit)==9 and all(not r['contact_rows'] for r in audit)
 grip=json.loads((work/'staff-grip-check.json').read_text());assert grip['all_right_grips_valid'];assert all(r['max_left_shaft_distance']<.08 for r in grip['profiles'] if r['sheet'] in ['wltas','wltaw','wltat','wltht'])
 for j in plan['jobs']:
  ref=json.loads(Path(j['reference']).read_text());assert ref['root_anchor_frame']==0;assert len(ref['equipment'])==1;mark=json.loads((Path(j['root'])/'completed.json').read_text());assert mark['fingerprint']==fingerprint(j)
 manifest=Path(plan['previous'])/'paladin-vanilla-dimensions/install-manifest.json';before=manifest.read_bytes();current=json.loads(before);assert current==plan['starting_custom_manifest'] and not (expected&set(current['sheets'])),'Use an explicit revision for existing staff sheets';live=Path(plan['game'])/'HD/plrgfx/warrior';mirror=Path(plan['assets'])/'Vanilla NN8 Dimensions';exe=Path(plan['game'])/'Diablo Reincarnated.exe';exe_hash=sha(exe)
 for n,r in current['sheets'].items():assert sha(live/n[:3]/(n+'.png'))==r['sha256'].upper(),n
 for n,r in records.items():assert sha(r['path'])==r['sha256'] and sha(live/n[:3]/(n+'.png'))==plan['starting_game_hashes'][n]
 for n,r in records.items():
  if r['size'][0]*r['size'][1]/4>=96*1024**2:print('PNG memory warning (continue):',n,r['size'][0]*r['size'][1]/4/1024**2,'MiB retained')
 archive=Path(archive);assert not archive.exists();archive.mkdir(parents=True);(archive/'previous-install-manifest.json').write_bytes(before);previous={}
 for n,r in records.items():
  dest=archive/'Final'/n[:3]/(n+'.png');dest.parent.mkdir(parents=True,exist_ok=True)
  for suffix in ['', '.layout']:shutil.copy2(Path(r['path']).with_name(n+'.png'+suffix),dest.with_name(dest.name+suffix))
  for kind,p in [('game',live/n[:3]/(n+'.png')),('mirror',mirror/(n+'.png'))]:
   for suffix in ['', '.layout']:
    old=p.with_name(p.name+suffix);previous[kind+'/'+n+suffix]=old.exists()
    if old.exists():d=archive/('previous-'+kind)/n[:3]/old.name;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(old,d)
 updated=copy.deepcopy(current);changed=[]
 try:
  for n,r in records.items():
   source=archive/'Final'/n[:3]/(n+'.png');changed.append(n)
   for p in [live/n[:3]/source.name,mirror/source.name]:
    for suffix in ['', '.layout']:shutil.copy2(source.with_name(source.name+suffix),p.with_name(p.name+suffix))
   updated['sheets'][n]={'source':str(source),'size':r['size'],'layout':r['layout'],'sha256':r['sha256'],'status':'T1 Paladin two-handed staff, frame-11 impact, staff visible during casting'}
  for n,r in updated['sheets'].items():assert sha(live/n[:3]/(n+'.png'))==r['sha256'].upper(),n
  assert len(updated['sheets'])==len(current['sheets'])+9 and sha(exe)==exe_hash
  receipt={'selected_weapon':'T1 twoHandStaff_base01.glb','installed_sheets':sorted(records),'previous_custom_sheets_preserved':len(current['sheets']),'custom_sheet_count':len(updated['sheets']),'executable_sha256':exe_hash,'version':current['version'],'game_impact_frame':11,'native_contact_frame':12,'archive':str(archive),'staff_scale':plan['staff_scale']};updated['staff_sets']=receipt;body=json.dumps(updated,indent=2);manifest.write_text(body);(mirror/'install-manifest.json').write_text(body);(archive/'install-manifest.json').write_text(body)
  for name in ['pack-validation.json','town-audit.json','canvas-padding.json','preflight-progress.json','staff-grip-check.json']:shutil.copy2(work/name,archive/name)
  (archive/'Equipment').mkdir()
  for path in {e['path'] for j in plan['jobs'] for e in json.loads(Path(j['reference']).read_text())['equipment']}:
   p=Path(path);shutil.copy2(p,archive/'Equipment'/p.name)
  shutil.copytree(work/'recipes',archive/'Recipes');shutil.copytree(work/'models',archive/'Models');shutil.copytree(work/'review',archive/'Review');(archive/'install-receipt.json').write_text(json.dumps(receipt,indent=2));(work/'install-receipt.json').write_text(json.dumps(receipt,indent=2));(archive/'previous-files.json').write_text(json.dumps(previous,indent=2))
 except BaseException:
  for n in changed:
   for kind,p in [('game',live/n[:3]/(n+'.png')),('mirror',mirror/(n+'.png'))]:
    for suffix in ['', '.layout']:
     target=p.with_name(p.name+suffix)
     if previous[kind+'/'+n+suffix]:shutil.copy2(archive/('previous-'+kind)/n[:3]/target.name,target)
     elif target.exists():target.unlink()
  manifest.write_bytes(before);(mirror/'install-manifest.json').write_bytes(before);raise
 print('Installed nine staff sheets;',len(current['sheets']),'existing custom sheets and executable preserved')
if __name__=='__main__':install(*sys.argv[1:])
