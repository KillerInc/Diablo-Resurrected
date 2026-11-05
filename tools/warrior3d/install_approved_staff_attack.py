"""python SCRIPT VALIDATED_APPROVED_PLAN NEW_PRIVATE_ARCHIVE
Install the reviewed staff attack, preserving every other sheet and executable.
Requires an explicit timing selection recorded in the plan.
"""
import copy,json,shutil,sys
from datetime import datetime,timezone
from pathlib import Path
from build_equipped_sets import sha,fingerprint

def install(file,archive):
 plan=json.loads(Path(file).read_text());work=Path(plan['work']);archive=Path(archive);assert not archive.exists();assert plan['approved_profile']=='sorcerer-natural-right-30cm' and plan['attack_only'];assert plan['timing_choice']=='aligned_hit' and plan['visual_thrust_frame']==plan['engine_impact_frame']==11
 assert len(plan['jobs'])==1;job=plan['jobs'][0];assert job['sheet']=='wltat';root=Path(job['root']);ref=json.loads(Path(job['reference']).read_text());assert ref['rows']==16 and ref['render_directions']==list(range(8)) and ref['source_frames']==list(range(16)) and ref['sun_position']==[3,-4,6]
 inputs=json.loads((work/'approved-inputs.json').read_text())
 for r in inputs.values():assert sha(r['approved_path'])==r['sha256'] and sha(r['path'])==r['sha256']
 aligned=json.loads((work/'aligned-verification.json').read_text());timing=json.loads((work/'timing-fit.json').read_text());assert aligned['derived_body_sha256']==sha(job['model']) and aligned['derived_staff_sha256']==sha(ref['equipment'][0]['path']);assert aligned['visual_hit_frame']==aligned['engine_impact_frame']==11 and aligned['frame_map']==plan['approved_frame_map']==timing['frame_map'] and aligned['frame_map'][10]==3
 assert aligned['maximum_exact_pose_error']<1e-5 and aligned['maximum_exact_staff_vertex_error']<1e-5 and aligned['maximum_right_wrist_degrees']<26 and aligned['maximum_grip_axis_error_degrees']<6 and aligned['maximum_grip_vertex_distance']<.06 and aligned['geometry_materials_nodes_bindings_unchanged'] and timing['whole_staff_scale_preserved'] and timing['source_rigidity_error']<1e-5
 spec=json.loads(Path(job['model']).with_suffix('.motion.json').read_text())['recipe'];assert spec['frames']==aligned['frame_map'] and sha(spec['source'])==inputs['body']['sha256']
 checks=json.loads((work/'preflight-progress.json').read_text());contacts=json.loads((work/'native-contact-audit.json').read_text());assert len(checks)==len(contacts)==1 and checks[0]['safe'] and not checks[0]['pose_attenuation_applied'] and not contacts[0]['contact_rows']
 grips=json.loads((work/'both-grip-path-audit.json').read_text());wrist=json.loads((work/'wrist-comparison-audit.json').read_text())[-1];assert grips['maximum_right_centre_error_metres']<.002 and grips['maximum_axis_error_degrees']<.1 and grips['maximum_staff_vertex_error_metres']<1e-5 and grips['maximum_left_grip_error_metres']<1e-5 and grips['maximum_other_channel_error']<1e-5 and wrist['maximum']<26
 png=root/'output/wltat.png';record=json.loads((root/'output/validation.json').read_text());mark=json.loads((root/'completed.json').read_text());assert mark['fingerprint']==fingerprint(job);assert sha(png)==mark['sha256']==record['sheet_sha256'].upper();assert record['size']==plan['inventory']['wlt']['wltat']['size'];assert len(record['body_cells'])==len(record['shadow_cells'])==128;layout=f"D1R_SHEET_V1 8 {record['anchor'][0]} {record['anchor'][1]}";assert png.with_name(png.name+'.layout').read_text().strip()==layout
 manifest=Path(plan['previous'])/'paladin-vanilla-dimensions/install-manifest.json';before=manifest.read_bytes();current=json.loads(before);assert current==plan['starting_custom_manifest'];live=Path(plan['game'])/'HD/plrgfx/warrior';mirror=Path(plan['assets'])/'Vanilla NN8 Dimensions';mirror_manifest=mirror/'install-manifest.json';mirror_before=mirror_manifest.read_bytes();exe=Path(plan['game'])/'Diablo Reincarnated.exe';exe_hash=sha(exe);snapshot={}
 for n,r in current['sheets'].items():
  p=live/n[:3]/(n+'.png');assert sha(p)==r['sha256'].upper(),n;snapshot[n]=(sha(p),p.with_name(p.name+'.layout').read_bytes())
 archive.mkdir(parents=True);(archive/'previous-install-manifest.json').write_bytes(before);(archive/'previous-mirror-manifest.json').write_bytes(mirror_before);targets=[live/'wlt/wltat.png',mirror/'wltat.png']
 for kind,target in zip(['previous-game','previous-mirror'],targets):
  out=archive/kind;out.mkdir()
  for suffix in ['','.layout']:shutil.copy2(target.with_name(target.name+suffix),out/('wltat.png'+suffix))
 final=archive/'Final';final.mkdir()
 for suffix in ['','.layout']:shutil.copy2(png.with_name(png.name+suffix),final/('wltat.png'+suffix))
 for name in ['plan.json','approved-inputs.json','preflight-progress.json','canvas-padding.json','native-contact-audit.json','both-grip-path-audit.json','wrist-comparison-audit.json','natural-arm-fit.json','aligned-verification.json','timing-fit.json','aligned-recipe.json']:shutil.copy2(work/name,archive/name)
 shutil.copy2(root/'output/validation.json',archive/'image-validation.json');inputs_dir=archive/'Inputs';inputs_dir.mkdir()
 approved_dir=inputs_dir/'Approved';approved_dir.mkdir()
 for role,r in inputs.items():shutil.copy2(r['path'],approved_dir/('approved-'+role+'.glb'))
 for path in work.glob('*.glb'):shutil.copy2(path,inputs_dir/path.name)
 for path in work.glob('*.motion.json'):shutil.copy2(path,inputs_dir/path.name)
 for path in (root/'output').glob('*.gif'):shutil.copy2(path,archive/path.name)
 updated=copy.deepcopy(current)
 try:
  for target in targets:
   for suffix in ['','.layout']:shutil.copy2(final/('wltat.png'+suffix),target.with_name(target.name+suffix))
  updated['sheets']['wltat'].update(source=str(final/'wltat.png'),sha256=sha(png),size=record['size'],layout=layout,status='Approved Sorcerer attack, two centred grips, natural right elbow/forearm, 30cm staff slide')
  for n,r in updated['sheets'].items():
   p=live/n[:3]/(n+'.png');assert sha(p)==r['sha256'].upper(),n
   if n!='wltat':assert (sha(p),p.with_name(p.name+'.layout').read_bytes())==snapshot[n],n
  assert len(updated['sheets'])==len(current['sheets']) and sha(exe)==exe_hash and sha(targets[0])==sha(targets[1])
  receipt={'installed_utc':datetime.now(timezone.utc).isoformat(),'changed_sheets':['wltat'],'other_custom_sheets_preserved':len(current['sheets'])-1,'custom_sheet_count':len(current['sheets']),'executable_sha256':exe_hash,'version':current['version'],'profile':plan['approved_profile'],'timing_choice':plan['timing_choice'],'visual_thrust_frame':plan['visual_thrust_frame'],'engine_impact_frame':plan['engine_impact_frame'],'archive':str(archive),'town_staff_carry_preserved':True,'approved_motion_and_grips_preserved':True,'retimed_to_engine_hit_frame':True};updated['staff_attack_revision']=receipt;text=json.dumps(updated,indent=2);manifest.write_text(text);mirror_manifest.write_text(text);(archive/'install-manifest.json').write_text(text);(archive/'install-receipt.json').write_text(json.dumps(receipt,indent=2));(work/'install-receipt.json').write_text(json.dumps(receipt,indent=2))
 except BaseException:
  for kind,target in zip(['previous-game','previous-mirror'],targets):
   for suffix in ['','.layout']:shutil.copy2(archive/kind/('wltat.png'+suffix),target.with_name(target.name+suffix))
  manifest.write_bytes(before);mirror_manifest.write_bytes(mirror_before);raise
 print('Installed approved staff attack; all other sheets and executable preserved')
if __name__=='__main__':install(*sys.argv[1:])
