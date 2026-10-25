"""Install only the three reviewed, validated light-warrior attack updates.

python SCRIPT REFINEMENT_PLAN.json NEW_ARCHIVE_DIRECTORY
Checks the complete current custom manifest, keeps exact backups, and preserves
all non-attack sheets and the executable. Copyrighted art remains local.
"""
import copy,json,shutil,sys
from pathlib import Path
from build_equipped_sets import sha,fingerprint

def install(plan_file,archive):
 plan=json.loads(Path(plan_file).read_text());assert not plan.get('superseded'),'This revision was superseded'
 work=Path(plan['work']);archive=Path(archive);assert not archive.exists(),'Use a new archive directory';jobs={j['sheet']:j for j in plan['jobs']};assert set(jobs)=={'wldat','wlsat','wluat'};checks=json.loads((work/'refinement-checks.json').read_text());assert len(checks)==3 and all(c['safe'] for c in checks)
 manifest=Path(plan['previous'])/'paladin-vanilla-dimensions/install-manifest.json';before_bytes=manifest.read_bytes();current=json.loads(before_bytes);assert current==plan['starting_custom_manifest'],'Manifest changed during revision';game=Path(plan['game']);live=game/'HD/plrgfx/warrior';mirror=Path(plan['assets'])/'Vanilla NN8 Dimensions';exe=game/'Diablo Reincarnated.exe';exe_before=sha(exe)
 for name,record in current['sheets'].items():assert sha(live/name[:3]/(name+'.png'))==record['sha256'].upper(),('Installed custom sheet changed',name)
 reports={}
 for name,job in jobs.items():
  root=Path(job['root']);recipe=json.loads(Path(job['model']).with_suffix('.motion.json').read_text())['recipe']
  if name!='wluat':
   assert recipe.get('align_horizontal_root') and recipe.get('arm_gain',1)==1 and recipe.get('motion_gain',1)==1
   assert not any(recipe.get(k) for k in ['arms','node_overlays','world_arm_sources','weapon_envelope','hand_offsets','branch_gains','wrist_gain','arm_tuck','finger_grip']) and not any(recipe.get('idle_weights',[])),'Sword motion must remain fully native'
  else:assert recipe.get('hand_offsets',{}).get('L'),'Shield attack must drive forward, not just hold a guard'
  png=root/'output'/(name+'.png');report=json.loads((root/'output/validation.json').read_text());mark=json.loads((root/'completed.json').read_text());assert mark['fingerprint']==fingerprint(job);assert sha(png)==mark['sha256']==report['sheet_sha256'].upper();assert report['size']==plan['inventory'][name[:3]][name]['size'];assert png.with_name(png.name+'.layout').read_text().strip()==f"D1R_SHEET_V1 8 {report['anchor'][0]} {report['anchor'][1]}";reports[name]=report
 archive.mkdir(parents=True);backup=archive/'previous-installed';final=archive/'Final';(archive/'previous-install-manifest.json').write_bytes(before_bytes)
 for name,job in jobs.items():
  b=backup/name[:3]/(name+'.png');f=final/name[:3]/b.name;b.parent.mkdir(parents=True,exist_ok=True);f.parent.mkdir(parents=True,exist_ok=True)
  for suffix in ['', '.layout']:shutil.copy2((live/name[:3]/b.name).with_name(b.name+suffix),b.with_name(b.name+suffix));shutil.copy2((Path(job['root'])/'output'/b.name).with_name(b.name+suffix),f.with_name(f.name+suffix))
 if (work/'comparisons').exists():shutil.copytree(work/'comparisons',archive/'Comparisons')
 (archive/'pose-checks.json').write_text(json.dumps(checks,indent=2));(archive/'image-validation.json').write_text(json.dumps(reports,indent=2));updated=copy.deepcopy(current)
 try:
  for name in jobs:
   source=final/name[:3]/(name+'.png');target=live/name[:3]/source.name
   for suffix in ['', '.layout']:shutil.copy2(source.with_name(source.name+suffix),target.with_name(target.name+suffix));shutil.copy2(source.with_name(source.name+suffix),mirror/(source.name+suffix))
   updated['sheets'][name].update(source=str(source),sha256=sha(source),size=reports[name]['size'],layout=f"D1R_SHEET_V1 8 {reports[name]['anchor'][0]} {reports[name]['anchor'][1]}",status='full native sword attack, timing/alignment only' if name!='wluat' else 'shield-face smash')
  for name,record in updated['sheets'].items():assert sha(live/name[:3]/(name+'.png'))==record['sha256'].upper(),name
  assert len(updated['sheets'])==len(current['sheets']) and sha(exe)==exe_before
  updated['equipped_attack_revision']={'archive':str(archive),'sword':'full native swordAndBoard, timing/alignment only','shield_only':'shield-face smash','game_contact_frame':9,'sheets':list(jobs),'executable_unchanged':True};text=json.dumps(updated,indent=2);manifest.write_text(text);(mirror/'install-manifest.json').write_text(text);(archive/'install-manifest.json').write_text(text);receipt={'changed_sheets':{n:updated['sheets'][n]['sha256'] for n in jobs},'other_custom_sheets_preserved':len(current['sheets'])-3,'executable_sha256':exe_before,'version':current['version'],'archive':str(archive)};(work/'install-receipt.json').write_text(json.dumps(receipt,indent=2));(archive/'install-receipt.json').write_text(json.dumps(receipt,indent=2))
 except BaseException:
  for name in jobs:
   old=backup/name[:3]/(name+'.png')
   for suffix in ['', '.layout']:shutil.copy2(old.with_name(old.name+suffix),(live/name[:3]/old.name).with_name(old.name+suffix));shutil.copy2(old.with_name(old.name+suffix),mirror/(old.name+suffix))
  manifest.write_bytes(before_bytes);(mirror/'install-manifest.json').write_bytes(before_bytes);raise
 print('Installed 3 revised attacks; all other custom sheets and executable preserved')

if __name__=='__main__':install(*sys.argv[1:])
