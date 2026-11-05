"""python SCRIPT VALIDATED_RESTORATION_PLAN.json NEW_PRIVATE_ARCHIVE
Install only audited full-motion revisions, preserving all other sheets/build.
"""
import copy,json,shutil,sys,datetime
from pathlib import Path
from build_equipped_sets import sha,fingerprint
def install(file,archive):
 plan=json.loads(Path(file).read_text());assert plan['equipment_family']=='full-motion-restoration' and plan['restore_unrestricted_motion'];work=Path(plan['work']);report=json.loads((work/'pack-validation.json').read_text());records=report['sheets'];expected=set(plan['restoration_targets']);assert set(records)==expected and report['sheet_count']==len(expected)==22
 checks=json.loads((work/'preflight-progress.json').read_text());contacts=json.loads((work/'native-contact-audit.json').read_text());assert len(checks)==len(contacts)==len(plan['jobs'])==16;assert all(r['safe'] and not r['pose_attenuation_applied'] for r in checks);assert all(not r['contact_rows'] for r in contacts)
 native=json.loads((work/'native-bone-audit.json').read_text());assert len(native)==4 and all(r['maximum_native_channel_error']<1e-5 for r in native)
 for j in plan['jobs']:
  ref=json.loads(Path(j['reference']).read_text());assert ref['sun_position']==[3,-4,6] and ref['shadow_distance_gain']==1 and not ref.get('redirect_fall');assert json.loads((Path(j['root'])/'completed.json').read_text())['fingerprint']==fingerprint(j)
  if j['sheet']=='wlndt':assert ref['preserve_horizontal_root_motion']
 for p in json.loads((work/'restoration-provenance.json').read_text()):
  if p.get('restored_recipe'):assert not (set(p['restored_recipe'])&{'arm_gain','motion_gain','wrist_gain','branch_gains','arm_tuck','weapon_envelope'})
 manifest=Path(plan['previous'])/'paladin-vanilla-dimensions/install-manifest.json';before=manifest.read_bytes();current=json.loads(before);assert current==plan['starting_custom_manifest'];live=Path(plan['game'])/'HD/plrgfx/warrior';mirror=Path(plan['assets'])/'Vanilla NN8 Dimensions';exe=Path(plan['game'])/'Diablo Reincarnated.exe';exe_hash=sha(exe);assert exe_hash==current['renderer_revision']['executable_sha256']
 def verify(data):
  for n,r in data['sheets'].items():
   p=live/n[:3]/(n+'.png');assert sha(p)==r['sha256'].upper(),n;assert p.with_name(p.name+'.layout').read_text().strip()==r['layout'],n
 verify(current)
 for n,r in records.items():assert sha(r['path'])==r['sha256'] and Path(r['path']+'.layout').read_text().strip()==r['layout']
 archive=Path(archive);assert not archive.exists();archive.mkdir(parents=True);(archive/'previous-install-manifest.json').write_bytes(before);mirror_before=(mirror/'install-manifest.json').read_bytes()
 for n,r in records.items():
  for kind,p in [('Final',Path(r['path'])),('previous-game',live/n[:3]/(n+'.png')),('previous-mirror',mirror/(n+'.png'))]:
   target=archive/kind/n[:3]/p.name;target.parent.mkdir(parents=True,exist_ok=True)
   for suffix in ['', '.layout']:shutil.copy2(p.with_name(p.name+suffix),target.with_name(target.name+suffix))
 updated=copy.deepcopy(current);changed=[]
 try:
  for n,r in records.items():
   source=archive/'Final'/n[:3]/(n+'.png');changed.append(n)
   for p in [live/n[:3]/source.name,mirror/source.name]:
    for suffix in ['', '.layout']:shutil.copy2(source.with_name(source.name+suffix),p.with_name(p.name+suffix))
   updated['sheets'][n].update(source=str(source),size=r['size'],layout=r['layout'],sha256=r['sha256'],status='full motion restored; transparent canvas expanded instead of pose attenuation')
  verify(updated);assert len(updated['sheets'])==len(current['sheets']) and sha(exe)==exe_hash
  receipt={'changed_sheets':sorted(records),'other_custom_sheets_preserved':len(current['sheets'])-len(records),'custom_sheet_count':len(current['sheets']),'directional_cells':report['stored_directional_frames'],'executable_sha256':exe_hash,'version':current['version'],'archive':str(archive),'approved_short_stride_preserved':True,'installed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()};updated['full_motion_restoration']=receipt;body=json.dumps(updated,indent=2);manifest.write_text(body);(mirror/'install-manifest.json').write_text(body);(archive/'install-manifest.json').write_text(body)
  for name in ['plan.json','restoration-provenance.json','pack-validation.json','preflight-progress.json','canvas-padding.json','native-contact-audit.json','native-bone-audit.json']:shutil.copy2(work/name,archive/name)
  shutil.copytree(work/'recipes',archive/'Recipes');shutil.copytree(work/'review',archive/'Review');inputs=[]
  for j in plan['jobs']:
   p=Path(j['model']);inputs.append({'sheet':j['sheet'],'model':str(p),'sha256':sha(p),'reference':json.loads(Path(j['reference']).read_text())})
  (archive/'render-inputs.json').write_text(json.dumps(inputs,indent=2));(archive/'install-receipt.json').write_text(json.dumps(receipt,indent=2));(work/'install-receipt.json').write_text(json.dumps(receipt,indent=2))
 except BaseException:
  for n in changed:
   for kind,p in [('previous-game',live/n[:3]/(n+'.png')),('previous-mirror',mirror/(n+'.png'))]:
    source=archive/kind/n[:3]/p.name
    for suffix in ['', '.layout']:shutil.copy2(source.with_name(source.name+suffix),p.with_name(p.name+suffix))
  manifest.write_bytes(before);(mirror/'install-manifest.json').write_bytes(mirror_before);raise
 print('Installed',len(records),'restored full-motion sheets;',receipt['other_custom_sheets_preserved'],'other sheets and executable preserved')
if __name__=='__main__':install(*sys.argv[1:])
