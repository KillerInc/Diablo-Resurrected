"""python SCRIPT VALIDATED_TOWN_BOW_PLAN.json NEW_PRIVATE_ARCHIVE
Replace only WLB ST/WL, preserving every combat sheet and executable.
"""
import copy,json,shutil,sys
from pathlib import Path
from build_equipped_sets import sha,fingerprint
def install(file,archive):
 plan=json.loads(Path(file).read_text());assert plan['equipment_family']=='light-town-bow' and plan['town_bow_revision'];work=Path(plan['work']);report=json.loads((work/'pack-validation.json').read_text());records=report['sheets'];assert set(records)=={'wlbst','wlbwl'} and report['sheet_count']==2
 for filename,key in [('preflight-progress.json','safe'),('town-audit.json','contact_rows')]:
  checks=json.loads((work/filename).read_text());assert len(checks)==2 and all(r[key] if key=='safe' else not r[key] for r in checks)
 for j in plan['jobs']:
  ref=json.loads(Path(j['reference']).read_text());assert ref['root_anchor_frame']==0 and len(ref['equipment'])==1 and ref['equipment'][0]['town_role']=='held_bow';mark=json.loads((Path(j['root'])/'completed.json').read_text());assert mark['fingerprint']==fingerprint(j)
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
   updated['sheets'][n].update(source=str(source),size=r['size'],layout=r['layout'],sha256=r['sha256'],status='vanilla-style low left-hand bow town carry; back clear for future quiver')
  for n,r in updated['sheets'].items():assert sha(live/n[:3]/(n+'.png'))==r['sha256'].upper() and (live/n[:3]/(n+'.png.layout')).read_text().strip()==r['layout'],n
  assert len(updated['sheets'])==len(current['sheets']) and sha(exe)==exe_hash
  receipt={'changed_sheets':sorted(records),'other_custom_sheets_preserved':len(current['sheets'])-2,'custom_sheet_count':len(current['sheets']),'executable_sha256':exe_hash,'archive':str(archive),'bow_town_carry':plan['bow_town_carry']};updated['town_bow_revision']=receipt;body=json.dumps(updated,indent=2);manifest.write_text(body);(mirror/'install-manifest.json').write_text(body);(archive/'install-manifest.json').write_text(body)
  for name in ['town-audit.json','canvas-padding.json','preflight-progress.json','pack-validation.json','plan.json']:shutil.copy2(work/name,archive/name)
  for p in work.glob('*.glb'):shutil.copy2(p,archive/p.name)
  for p in work.glob('*recipe.json'):shutil.copy2(p,archive/p.name)
  for p in work.glob('*.fit.json'):shutil.copy2(p,archive/p.name)
  shutil.copytree(work/'review',archive/'Review');(archive/'install-receipt.json').write_text(json.dumps(receipt,indent=2));(work/'install-receipt.json').write_text(json.dumps(receipt,indent=2))
 except BaseException:
  for n in changed:
   for kind,p in [('previous-game',live/n[:3]/(n+'.png')),('previous-mirror',mirror/(n+'.png'))]:
    source=archive/kind/n[:3]/p.name
    for suffix in ['', '.layout']:shutil.copy2(source.with_name(source.name+suffix),p.with_name(p.name+suffix))
  manifest.write_bytes(before);(mirror/'install-manifest.json').write_bytes(before);raise
 print('Installed two town bow sheets; all other sheets and executable preserved')
if __name__=='__main__':install(*sys.argv[1:])
