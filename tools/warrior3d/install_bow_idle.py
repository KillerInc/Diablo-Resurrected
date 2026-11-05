"""python SCRIPT VALIDATED_BOW_IDLE_PLAN.json NEW_PRIVATE_ARCHIVE
Replace only WLB AS/ST, preserving other sheets, body motion and executable.
"""
import copy,json,shutil,sys
from pathlib import Path
from build_equipped_sets import sha,fingerprint
def install(file,archive):
 plan=json.loads(Path(file).read_text());assert plan['equipment_family']=='light-bow-idle' and plan['bow_idle_revision'];work=Path(plan['work']);report=json.loads((work/'pack-validation.json').read_text());records=report['sheets'];assert set(records)=={'wlbas','wlbst'} and report['sheet_count']==2
 checks=json.loads((work/'preflight-progress.json').read_text());assert len(checks)==2 and all(r['safe'] for r in checks)
 audits=json.loads((work/'idle-hold-audit.json').read_text());assert {r['sheet'] for r in audits}==set(records) and all(not r['body_contacts'] for r in audits)
 if plan.get('bow_grip_revision'):assert all(r['max_geometric_grip_centre_error']<.005 and r['minimum_string_inward_metres']>.04 and r['non_left_arm_channel_error']<1e-5 and r['original_art_buffers_preserved'] for r in audits)
 else:assert all(r['max_grip_error_metres']<1e-5 for r in audits)
 if plan.get('bow_string_clearance_revision'):assert all(r['minimum_string_arm_gap_metres']>=.0015 and r['maximum_string_arm_gap_metres']<=.012 for r in audits)
 if plan.get('bow_elbow_revision'):assert all(r['minimum_elbow_outward_metres']>=.065 and r['minimum_elbow_drop_metres']>=.095 and r['maximum_elbow_hinge_error_degrees']<1 for r in audits)
 for j in plan['jobs']:
  ref=json.loads(Path(j['reference']).read_text());assert len(ref['equipment'])==2 and ref['equipment'][0]['town_role']=='held_bow' and ref['equipment'][1]['town_role']=='back_quiver'
  audit=next(r for r in audits if r['sheet']==j['sheet']);assert audit['bow_sha256']==sha(ref['equipment'][0]['path']) and audit['body_sha256']==sha(j['model'])
  mark=json.loads((Path(j['root'])/'completed.json').read_text());assert mark['fingerprint']==fingerprint(j)
 manifest=Path(plan['previous'])/'paladin-vanilla-dimensions/install-manifest.json';before=manifest.read_bytes();current=json.loads(before);assert current==plan['starting_custom_manifest'];live=Path(plan['game'])/'HD/plrgfx/warrior';mirror=Path(plan['assets'])/'Vanilla NN8 Dimensions';exe=Path(plan['game'])/'Diablo Reincarnated.exe';exe_hash=sha(exe)
 for n,r in current['sheets'].items():
  assert sha(live/n[:3]/(n+'.png'))==r['sha256'].upper(),n
  assert (live/n[:3]/(n+'.png.layout')).read_text().strip()==r['layout'],n
 for n,r in records.items():assert sha(r['path'])==r['sha256'] and Path(r['path']+'.layout').read_text().strip()==r['layout']
 archive=Path(archive);assert not archive.exists();archive.mkdir(parents=True);(archive/'previous-install-manifest.json').write_bytes(before)
 for n,r in records.items():
  for kind,p in [('Final',Path(r['path'])),('previous-game',live/n[:3]/(n+'.png')),('previous-mirror',mirror/(n+'.png'))]:
   dest=archive/kind/n[:3]/p.name;dest.parent.mkdir(parents=True,exist_ok=True)
   for suffix in ['', '.layout']:shutil.copy2(p.with_name(p.name+suffix),dest.with_name(dest.name+suffix))
 updated=copy.deepcopy(current);changed=[]
 try:
  for n,r in records.items():
   source=archive/'Final'/n[:3]/(n+'.png');changed.append(n)
   for p in [live/n[:3]/source.name,mirror/source.name]:
    for suffix in ['', '.layout']:shutil.copy2(source.with_name(source.name+suffix),p.with_name(p.name+suffix))
   updated['sheets'][n].update(source=str(source),size=r['size'],layout=r['layout'],sha256=r['sha256'],status='closed-palm bow grip, inward string, natural left forearm' if plan.get('bow_grip_revision') else 'corrected low idle bow angle, unchanged palm grip/body and back quiver')
  for n,r in updated['sheets'].items():assert sha(live/n[:3]/(n+'.png'))==r['sha256'].upper() and (live/n[:3]/(n+'.png.layout')).read_text().strip()==r['layout'],n
  assert len(updated['sheets'])==len(current['sheets']) and sha(exe)==exe_hash
  receipt={'changed_sheets':sorted(records),'other_custom_sheets_preserved':len(current['sheets'])-2,'custom_sheet_count':len(current['sheets']),'executable_sha256':exe_hash,'archive':str(archive),'hold_angles':plan['bow_hold_angles'],'version':current['version']};updated['bow_idle_revision']=receipt
  if plan.get('bow_grip_revision'):updated['bow_grip_revision']=receipt
  if plan.get('bow_string_clearance_revision'):
   receipt['string_arm_gaps']={r['sheet']:[r['minimum_string_arm_gap_metres'],r['maximum_string_arm_gap_metres']] for r in audits};updated['bow_string_clearance_revision']=receipt
  if plan.get('bow_elbow_revision'):
   receipt['elbow_hinge_checks']={r['sheet']:{k:r[k] for k in ['minimum_elbow_outward_metres','minimum_elbow_drop_metres','maximum_elbow_hinge_error_degrees']} for r in audits};updated['bow_elbow_revision']=receipt
  if plan.get('bow_reference_pose_revision'):updated['bow_reference_pose_revision']=receipt
  body=json.dumps(updated,indent=2);manifest.write_text(body);(mirror/'install-manifest.json').write_text(body);(archive/'install-manifest.json').write_text(body)
  for name in ['idle-hold-audit.json','preflight-progress.json','pack-validation.json','plan.json']:shutil.copy2(work/name,archive/name)
  if plan.get('bow_string_clearance_revision'):shutil.copy2(work/'string-clearance.json',archive/'string-clearance.json')
  for p in work.glob('*.glb'):shutil.copy2(p,archive/p.name)
  for p in work.glob('*recipe.json'):shutil.copy2(p,archive/p.name)
  for p in work.glob('*.fit.json'):shutil.copy2(p,archive/p.name)
  if (work/'closeups').is_dir():shutil.copytree(work/'closeups',archive/'Closeups')
  (archive/'Equipment').mkdir();(archive/'References').mkdir();(archive/'Models').mkdir()
  for j in plan['jobs']:
   shutil.copy2(j['model'],archive/'Models'/(j['sheet']+'-body.glb'));ref=Path(j['reference']);shutil.copy2(ref,archive/'References'/(j['sheet']+'.json'));asset=Path(json.loads(ref.read_text())['equipment'][0]['path'])
   shutil.copy2(asset,archive/'Equipment'/(j['sheet']+'-bow.glb'));fit=asset.with_suffix('.fit.json')
   if not fit.exists():fit=work/(j['sheet']+'-fit.json')
   shutil.copy2(fit,archive/'Equipment'/(j['sheet']+'-bow.fit.json'))
  shutil.copytree(work/'review',archive/'Review');(archive/'install-receipt.json').write_text(json.dumps(receipt,indent=2));(work/'install-receipt.json').write_text(json.dumps(receipt,indent=2))
 except BaseException:
  for n in changed:
   for kind,p in [('previous-game',live/n[:3]/(n+'.png')),('previous-mirror',mirror/(n+'.png'))]:
    source=archive/kind/n[:3]/p.name
    for suffix in ['', '.layout']:shutil.copy2(source.with_name(source.name+suffix),p.with_name(p.name+suffix))
  manifest.write_bytes(before);(mirror/'install-manifest.json').write_bytes(before);raise
 print('Installed two corrected bow idle sheets; 83 other sheets and executable preserved')
if __name__=='__main__':install(*sys.argv[1:])
