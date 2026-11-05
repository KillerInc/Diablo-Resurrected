"""Install one validated Sorcerer staff attack, with exact backups and rollback.
python SCRIPT PLAN.json NEW_PRIVATE_ARCHIVE
All other sheets and the executable are hash-preserved. Art stays local.
"""
import copy,json,shutil,sys
from datetime import datetime,timezone
from pathlib import Path
from build_equipped_sets import sha,fingerprint

def install(file,archive):
 plan=json.loads(Path(file).read_text());work=Path(plan['work']);archive=Path(archive);assert not archive.exists();assert plan['attack_only'] and plan['selected_native_clip']=='sorM_STF_attk_weaponAttack';assert plan['native_contact_frame']==9 and plan['attack_action_frame']==11
 assert len(plan['jobs'])==1;job=plan['jobs'][0];assert job['sheet']=='wltat' and job['action']=='at';root=Path(job['root']);ref=json.loads(Path(job['reference']).read_text());assert ref['render_directions']==list(range(8)) and ref['source_frames']==list(range(16)) and ref['sun_position']==[3,-4,6] and ref['root_anchor_frame']==0
 checks=json.loads((work/'preflight-progress.json').read_text());assert len(checks)==1 and checks[0]['safe'] and not checks[0]['pose_attenuation_applied'];contacts=json.loads((work/'native-contact-audit.json').read_text());assert len(contacts)==1 and contacts[0]['sheet']=='wltat' and not contacts[0]['contact_rows'];bones=json.loads((work/'native-bone-audit.json').read_text());assert len(bones)==1 and bones[0]['sheet']=='wltat' and bones[0]['comparisons']>0 and bones[0]['maximum_native_channel_error']<1e-5
 grips=json.loads((work/'staff-grip-check.json').read_text());assert grips['all_right_grips_valid'] and len(grips['profiles'])==1
 recipe=json.loads(Path(job['model']).with_suffix('.motion.json').read_text())['recipe'];assert recipe['native_source_clip']==plan['selected_native_clip'] and recipe['frames'][10]==9 and recipe['frames'][0]==0 and recipe['frames'][-1]==45
 assert not any(recipe.get(k) for k in ['arms','idle','hand_offsets','weapon_envelope','arm_gain','motion_gain','branch_gains','wrist_gain','arm_tuck'])
 record=json.loads((root/'output/validation.json').read_text());mark=json.loads((root/'completed.json').read_text());png=root/'output/wltat.png';assert mark['fingerprint']==fingerprint(job);assert sha(png)==mark['sha256']==record['sheet_sha256'].upper();assert record['size']==plan['inventory']['wlt']['wltat']['size'];assert len(record['body_cells'])==len(record['shadow_cells'])==128
 layout=f"D1R_SHEET_V1 8 {record['anchor'][0]} {record['anchor'][1]}";assert png.with_name('wltat.png.layout').read_text().strip()==layout
 manifest=Path(plan['previous'])/'paladin-vanilla-dimensions/install-manifest.json';before=manifest.read_bytes();current=json.loads(before);assert current==plan['starting_custom_manifest'];game=Path(plan['game']);live=game/'HD/plrgfx/warrior';mirror=Path(plan['assets'])/'Vanilla NN8 Dimensions';mirror_manifest=mirror/'install-manifest.json';mirror_before=mirror_manifest.read_bytes();exe=game/'Diablo Reincarnated.exe';exe_hash=sha(exe)
 snapshot={}
 for name,r in current['sheets'].items():
  path=live/name[:3]/(name+'.png');assert sha(path)==r['sha256'].upper(),name;snapshot[name]=(sha(path),path.with_name(path.name+'.layout').read_bytes())
 targets=[live/'wlt/wltat.png',mirror/'wltat.png'];archive.mkdir(parents=True);(archive/'previous-install-manifest.json').write_bytes(before);(archive/'previous-mirror-manifest.json').write_bytes(mirror_before)
 for i,target in enumerate(targets):
  out=archive/('previous-game' if i==0 else 'previous-mirror');out.mkdir()
  for suffix in ['','.layout']:shutil.copy2(target.with_name(target.name+suffix),out/('wltat.png'+suffix))
 final=archive/'Final';final.mkdir()
 for suffix in ['','.layout']:shutil.copy2(png.with_name(png.name+suffix),final/('wltat.png'+suffix))
 for name in ['plan.json','wltat-recipe.json','preflight-progress.json','canvas-padding.json','native-contact-audit.json','native-bone-audit.json','staff-grip-check.json']:shutil.copy2(work/name,archive/name)
 shutil.copy2(root/'output/validation.json',archive/'image-validation.json');inputs=archive/'Inputs';inputs.mkdir()
 for path in work.glob('*.glb'):shutil.copy2(path,inputs/path.name)
 for path in (root/'output').glob('*.gif'):shutil.copy2(path,archive/path.name)
 updated=copy.deepcopy(current)
 try:
  for target in targets:
   for suffix in ['','.layout']:shutil.copy2(final/('wltat.png'+suffix),target.with_name(target.name+suffix))
  updated['sheets']['wltat'].update(source=str(final/'wltat.png'),sha256=sha(png),size=record['size'],layout=layout,status='Sorcerer native staff weaponAttack; frame-11 impact; staff-only 5-degree clearance tilt')
  for name,r in updated['sheets'].items():
   path=live/name[:3]/(name+'.png');assert sha(path)==r['sha256'].upper(),name
   if name!='wltat':assert (sha(path),path.with_name(path.name+'.layout').read_bytes())==snapshot[name],name
  assert sha(exe)==exe_hash and len(updated['sheets'])==len(current['sheets']);assert sha(targets[0])==sha(targets[1])
  receipt={'installed_utc':datetime.now(timezone.utc).isoformat(),'changed_sheets':['wltat'],'native_clip':plan['selected_native_clip'],'native_contact_frame':9,'game_impact_frame':11,'staff_scale':.8,'staff_grip_local':[0,.4,0],'staff_only_tilt_degrees':5,'native_body_preserved':True,'left_hand':'native free-hand motion; no two-hand staff steering','other_custom_sheets_preserved':len(current['sheets'])-1,'custom_sheet_count':len(current['sheets']),'executable_sha256':exe_hash,'version':current['version'],'short_town_stride_preserved':True,'archive':str(archive)}
  updated['staff_attack_revision']=receipt;text=json.dumps(updated,indent=2);manifest.write_text(text);mirror_manifest.write_text(text);(archive/'install-manifest.json').write_text(text);(archive/'install-receipt.json').write_text(json.dumps(receipt,indent=2));(work/'install-receipt.json').write_text(json.dumps(receipt,indent=2))
 except BaseException:
  for i,target in enumerate(targets):
   for suffix in ['','.layout']:shutil.copy2(archive/('previous-game' if i==0 else 'previous-mirror')/('wltat.png'+suffix),target.with_name(target.name+suffix))
  manifest.write_bytes(before);mirror_manifest.write_bytes(mirror_before);raise
 print('Installed Sorcerer staff attack; preserved',len(current['sheets'])-1,'other sheets and executable',flush=True)
if __name__=='__main__':install(*sys.argv[1:])
