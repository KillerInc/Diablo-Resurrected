"""python SCRIPT VALIDATED_QUIVER_PLAN.json NEW_PRIVATE_ARCHIVE
Install the closer quiver mount in nine bow sheets; preserve other art and executable.
"""
import copy,json,shutil,sys
from pathlib import Path
from build_equipped_sets import sha,fingerprint
def install(file,archive):
 plan=json.loads(Path(file).read_text());assert plan['equipment_family']=='light-bow' and plan['quiver_fit_revision'];work=Path(plan['work']);report=json.loads((work/'pack-validation.json').read_text());records=report['sheets'];assert set(records)=={'wlb'+a for a in ['as','aw','at','ht','st','wl','fm','lm','qm']} and report['sheet_count']==9
 checks=json.loads((work/'preflight-progress.json').read_text());assert len(checks)==9 and all(r['safe'] for r in checks)
 final=json.loads((work/'final-clearance.json').read_text());assert {r['sheet'] for r in final}==set(records) and all((not r['tests'][-1]['contacts'] or plan['quiver_fit'].get('approved_minor_back_overlap') and 0<plan['quiver_fit']['additional_inward_metres']<=(.04 if plan['quiver_fit'].get('endpoint_fit') else .02)) and (not r['tests'][-1].get('arrow_contacts',[]) or plan['quiver_fit'].get('approved_minor_arrow_overlap') and plan['quiver_fit'].get('endpoint_fit')) and r['tests'][-1]['outward_metres']==0 for r in final)
 if plan.get('quiver_arrow_wall_revision'):
  wall=json.loads((work/'quiver-wall-clearance.json').read_text());assert wall['arrow_wall_intersections']==0 and wall['wall_geometry_preserved'] and wall['arrows']==6 and wall['shafts_inside_pouch'] and wall['shaft_containment_samples']==24
 for j in plan['jobs']:
  ref=json.loads(Path(j['reference']).read_text());q=[e for e in ref['equipment'] if e.get('town_role')=='back_quiver'];assert len(q)==1 and q[0]['bone']=='chest' and q[0]['strap_side_inward'] and abs(q[0]['quiver_inward_revision_metres']-plan['quiver_fit']['selected_inward_metres'])<1e-9
  if plan.get('quiver_arrow_wall_revision'):assert wall['quiver_sha256']==sha(q[0]['path'])
  audit=next(a for a in final if a['sheet']==j['sheet']);assert audit['model_sha256']==sha(j['model']) and audit['reference_sha256']==sha(j['reference']) and audit['quiver_sha256']==sha(q[0]['path'])
  mark=json.loads((Path(j['root'])/'completed.json').read_text());assert mark['fingerprint']==fingerprint(j)
 manifest=Path(plan['previous'])/'paladin-vanilla-dimensions/install-manifest.json';before=manifest.read_bytes();current=json.loads(before);assert current==plan['starting_custom_manifest'];live=Path(plan['game'])/'HD/plrgfx/warrior';mirror=Path(plan['assets'])/'Vanilla NN8 Dimensions';exe=Path(plan['game'])/'Diablo Reincarnated.exe';exe_hash=sha(exe)
 for n,r in current['sheets'].items():
  assert sha(live/n[:3]/(n+'.png'))==r['sha256'].upper(),n
  assert (live/n[:3]/(n+'.png.layout')).read_text().strip()==r['layout'],n
 for n,r in records.items():assert sha(r['path'])==r['sha256'] and Path(r['path']+'.layout').read_text().strip()==r['layout']
 archive=Path(archive);assert not archive.exists();archive.mkdir(parents=True);(archive/'ASSET_ATTRIBUTION.txt').write_text('Bow Quiver And Arrow by Egor Surin (stark.egor), CC BY 4.0\nhttps://sketchfab.com/3d-models/bow-quiver-and-arrow-100a1bfeb3f947d6bafe22945d9c754e\nChanges: removed bow, seated six arrows, normalized units and fitted quiver to warrior back. Arrow-wall revisions also remove hidden heads and seat shafts inside the pouch.\n');(archive/'previous-install-manifest.json').write_bytes(before)
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
   updated['sheets'][n].update(source=str(source),size=r['size'],layout=r['layout'],sha256=r['sha256'],status='closer chest-mounted six-arrow quiver; approved minor back overlap' if plan['quiver_fit'].get('approved_minor_back_overlap') else 'closer chest-mounted six-arrow quiver; approved pose, grips and effects retained')
  for n,r in updated['sheets'].items():assert sha(live/n[:3]/(n+'.png'))==r['sha256'].upper() and (live/n[:3]/(n+'.png.layout')).read_text().strip()==r['layout'],n
  assert len(updated['sheets'])==len(current['sheets']) and sha(exe)==exe_hash
  receipt={'version':current['version'],'changed_sheets':sorted(records),'other_custom_sheets_preserved':len(current['sheets'])-9,'custom_sheet_count':len(current['sheets']),'executable_sha256':exe_hash,'archive':str(archive),'bow_town_carry':'approved reference resting hold','quiver':'six arrows, chest attachment, strap side inward','quiver_source_attribution':'Bow Quiver And Arrow by Egor Surin (stark.egor), CC BY 4.0; modified quiver only'};receipt['quiver_fit']=plan['quiver_fit'];updated['bow_quiver_revision']=receipt;updated['quiver_close_fit_revision']=receipt;
  if plan.get('quiver_arrow_wall_revision'):updated['quiver_arrow_wall_revision']=receipt
  body=json.dumps(updated,indent=2);manifest.write_text(body);(mirror/'install-manifest.json').write_text(body);(archive/'install-manifest.json').write_text(body)
  for name in ['final-clearance.json','quiver-fit-search.json','triangle-parts.json','preflight-progress.json','pack-validation.json','plan.json']:shutil.copy2(work/name,archive/name)
  (archive/'Models').mkdir();(archive/'Equipment').mkdir();(archive/'References').mkdir();models={Path(j['model']) for j in plan['jobs']};assert len({m.name for m in models})==len(models)
  for model in models:shutil.copy2(model,archive/'Models'/model.name)
  equipment={Path(e['path']) for j in plan['jobs'] for e in json.loads(Path(j['reference']).read_text())['equipment']};assert len({e.name for e in equipment})==len(equipment)
  for asset in equipment:
   shutil.copy2(asset,archive/'Equipment'/asset.name)
   if asset.with_suffix('.fit.json').exists():shutil.copy2(asset.with_suffix('.fit.json'),archive/'Equipment'/asset.with_suffix('.fit.json').name)
  if plan.get('quiver_arrow_wall_revision'):
   previous_assets={Path(e['previous_asset_path']) for j in plan['jobs'] for e in json.loads(Path(j['reference']).read_text())['equipment'] if e.get('previous_asset_path')};previous_assets.add(Path(wall['source']));(archive/'PreviousEquipment').mkdir()
   for asset in previous_assets:shutil.copy2(asset,archive/'PreviousEquipment'/asset.name)
  for j in plan['jobs']:
   ref=json.loads(Path(j['reference']).read_text())
   for e in ref['equipment']:
    e['path']=str(archive/'Equipment'/Path(e['path']).name)
    if plan.get('quiver_arrow_wall_revision') and e.get('previous_asset_path'):e['previous_asset_path']=str(archive/'PreviousEquipment'/Path(e['previous_asset_path']).name)
   (archive/'References'/(j['sheet']+'.json')).write_text(json.dumps(ref,indent=2))
  if plan['quiver_fit'].get('contour'):shutil.copy2(work/'quiver-contour-search.json',archive/'quiver-contour-search.json')
  if plan.get('quiver_arrow_wall_revision'):
   for name in ['arrow-fit.json','quiver-wall-clearance.json','shaft-containment.json']:shutil.copy2(work/name,archive/name)
  if (work/'endpoint-fit.json').exists():shutil.copy2(work/'endpoint-fit.json',archive/'endpoint-fit.json')
  for p in work.glob('*recipe.json'):shutil.copy2(p,archive/p.name)
  for p in work.glob('*.fit.json'):shutil.copy2(p,archive/p.name)
  shutil.copytree(work/'review',archive/'Review');(archive/'install-receipt.json').write_text(json.dumps(receipt,indent=2));(work/'install-receipt.json').write_text(json.dumps(receipt,indent=2))
 except BaseException:
  for n in changed:
   for kind,p in [('previous-game',live/n[:3]/(n+'.png')),('previous-mirror',mirror/(n+'.png'))]:
    source=archive/kind/n[:3]/p.name
    for suffix in ['', '.layout']:shutil.copy2(source.with_name(source.name+suffix),p.with_name(p.name+suffix))
  manifest.write_bytes(before);(mirror/'install-manifest.json').write_bytes(before);raise
 print('Installed nine completed bow sheets; 76 other sheets and executable preserved')
if __name__=='__main__':install(*sys.argv[1:])
