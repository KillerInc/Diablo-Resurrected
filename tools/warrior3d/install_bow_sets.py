"""python SCRIPT VALIDATED_BOW_PLAN.json NEW_PRIVATE_ARCHIVE
Install nine new light-warrior bow sheets with exact backups and rollback.
"""
import json,copy,shutil,sys
from pathlib import Path
from build_equipped_sets import sha,fingerprint
def install(plan_file,archive):
 plan=json.loads(Path(plan_file).read_text());assert plan['equipment_family']=='light-bow' and plan['selected_weapon']=='B1';work=Path(plan['work']);report=json.loads((work/'pack-validation.json').read_text());records=report['sheets'];expected={'wlb'+a for a in ['as','aw','at','ht','st','wl','fm','lm','qm']};assert set(records)==expected and report['sheet_count']==9 and report['attack_action_frame']==11
 checks=json.loads((work/'preflight-progress.json').read_text());audit=json.loads((work/'town-audit.json').read_text());assert len(checks)==6 and all(r['safe'] for r in checks);assert len(audit)==6 and all(not r['contact_rows'] for r in audit)
 grip=json.loads((work/'bow-draw-check.json').read_text());assert grip['all_grips_and_release_valid']
 for j in plan['jobs']:
  ref=json.loads(Path(j['reference']).read_text());assert ref['root_anchor_frame']==0;assert len(ref['equipment'])==1;mark=json.loads((Path(j['root'])/'completed.json').read_text());assert mark['fingerprint']==fingerprint(j)
 manifest=Path(plan['previous'])/'paladin-vanilla-dimensions/install-manifest.json';before=manifest.read_bytes();current=json.loads(before);assert current==plan['starting_custom_manifest'] and not (expected&set(current['sheets'])),'Use an explicit revision for existing bow sheets';live=Path(plan['game'])/'HD/plrgfx/warrior';mirror=Path(plan['assets'])/'Vanilla NN8 Dimensions';exe=Path(plan['game'])/'Diablo Reincarnated.exe';exe_hash=sha(exe)
 for n,r in current['sheets'].items():assert sha(live/n[:3]/(n+'.png'))==r['sha256'].upper(),n
 for n,r in records.items():assert sha(r['path'])==r['sha256'] and sha(live/n[:3]/(n+'.png'))==plan['starting_game_hashes'][n]
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
   updated['sheets'][n]={'source':str(source),'size':r['size'],'layout':r['layout'],'sha256':r['sha256'],'status':'B1 native Rogue bow retarget, game-frame-11 release, approved town back stow'}
  for n,r in updated['sheets'].items():assert sha(live/n[:3]/(n+'.png'))==r['sha256'].upper(),n
  assert len(updated['sheets'])==len(current['sheets'])+9 and sha(exe)==exe_hash
  receipt={'selected_weapon':'B1 twoHandBow_base01.glb','installed_sheets':sorted(records),'previous_custom_sheets_preserved':len(current['sheets']),'custom_sheet_count':len(updated['sheets']),'executable_sha256':exe_hash,'version':current['version'],'game_release_frame':11,'native_contact_frame':7,'archive':str(archive),'town_back_reference':plan['bow_back_reference']};updated['bow_sets']=receipt;body=json.dumps(updated,indent=2);manifest.write_text(body);(mirror/'install-manifest.json').write_text(body);(archive/'install-manifest.json').write_text(body)
  for name in ['pack-validation.json','town-audit.json','canvas-padding.json','preflight-progress.json','bow-draw-check.json']:shutil.copy2(work/name,archive/name)
  (archive/'Equipment').mkdir()
  for path in {e['path'] for j in plan['jobs'] for e in json.loads(Path(j['reference']).read_text())['equipment']}:
   p=Path(path);shutil.copy2(p,archive/'Equipment'/p.name);shutil.copy2(p.with_suffix('.fit.json'),archive/'Equipment'/p.with_suffix('.fit.json').name)
  shutil.copytree(work/'recipes',archive/'Recipes');shutil.copytree(work/'models',archive/'Models');shutil.copytree(work/'review',archive/'Review');(archive/'install-receipt.json').write_text(json.dumps(receipt,indent=2));(work/'install-receipt.json').write_text(json.dumps(receipt,indent=2));(archive/'previous-files.json').write_text(json.dumps(previous,indent=2))
 except BaseException:
  for n in changed:
   for kind,p in [('game',live/n[:3]/(n+'.png')),('mirror',mirror/(n+'.png'))]:
    for suffix in ['', '.layout']:
     target=p.with_name(p.name+suffix)
     if previous[kind+'/'+n+suffix]:shutil.copy2(archive/('previous-'+kind)/n[:3]/target.name,target)
     elif target.exists():target.unlink()
  manifest.write_bytes(before);(mirror/'install-manifest.json').write_bytes(before);raise
 print('Installed nine bow sheets;',len(current['sheets']),'existing custom sheets and executable preserved')
if __name__=='__main__':install(*sys.argv[1:])
