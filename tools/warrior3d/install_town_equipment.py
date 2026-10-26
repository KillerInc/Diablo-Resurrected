"""Install ten validated town-equipment updates with exact backups/rollback.

python SCRIPT TOWN_PLAN.json NEW_PRIVATE_ARCHIVE_DIRECTORY
Only ST/WL sheets for sword, mace, their shield variants and axe may change.
"""
import copy,json,shutil,sys
from pathlib import Path
from build_equipped_sets import sha,fingerprint

def install(plan_file,archive):
 plan=json.loads(Path(plan_file).read_text());assert plan.get('town_equipment_revision') and plan['equipment_family']=='light-town';work=Path(plan['work']);report=json.loads((work/'pack-validation.json').read_text());records=report['sheets'];expected={c+a for c in ['wls','wld','wlm','wlh','wla'] for a in ['st','wl']};assert report['sheet_count']==10 and set(records)==expected
 audit=json.loads((work/'town-audit.json').read_text());assert len(audit)==10 and all(not a['contact_rows'] for a in audit)
 checks=json.loads((work/'preflight-progress.json').read_text());assert len(checks)==10 and all(c['safe'] for c in checks)
 for j in plan['jobs']:
  ref=json.loads(Path(j['reference']).read_text());assert ref['root_anchor_frame']==0;mark=json.loads((Path(j['root'])/'completed.json').read_text());assert mark['fingerprint']==fingerprint(j)
  roles={e['town_role'] for e in ref['equipment']};required={'wls':{'sheathed_sword','sword_sheath'},'wld':{'sheathed_sword','sword_sheath','carried_shield'},'wlm':{'holstered_mace','mace_frog'},'wlh':{'holstered_mace','mace_frog','carried_shield'},'wla':{'carried_axe'}}[j['code']];assert required<=roles
 manifest=Path(plan['previous'])/'paladin-vanilla-dimensions/install-manifest.json';before=manifest.read_bytes();current=json.loads(before);assert current==plan['starting_custom_manifest'] and expected<=set(current['sheets']);live=Path(plan['game'])/'HD/plrgfx/warrior';mirror=Path(plan['assets'])/'Vanilla NN8 Dimensions';exe=Path(plan['game'])/'Diablo Reincarnated.exe';exe_hash=sha(exe)
 for n,r in current['sheets'].items():assert sha(live/n[:3]/(n+'.png'))==r['sha256'].upper(),n
 for n,r in records.items():assert sha(r['path'])==r['sha256'];assert Path(r['path']+'.layout').read_text().strip()==r['layout']
 archive=Path(archive);assert not archive.exists();archive.mkdir(parents=True);(archive/'previous-install-manifest.json').write_bytes(before)
 for n,r in records.items():
  for kind,source in [('previous-installed',live/n[:3]/(n+'.png')),('Final',Path(r['path']))]:
   dest=archive/kind/n[:3]/source.name;dest.parent.mkdir(parents=True,exist_ok=True)
   for suffix in ['', '.layout']:shutil.copy2(source.with_name(source.name+suffix),dest.with_name(dest.name+suffix))
 updated=copy.deepcopy(current);changed=[]
 try:
  for n,r in records.items():
   source=archive/'Final'/n[:3]/(n+'.png');changed.append(n)
   for target in [live/n[:3]/source.name,mirror/source.name]:
    for suffix in ['', '.layout']:shutil.copy2(source.with_name(source.name+suffix),target.with_name(target.name+suffix))
   updated['sheets'][n].update(source=str(source),size=r['size'],layout=r['layout'],sha256=r['sha256'],status='vanilla-style equipment-specific town carry/stow')
  for n,r in updated['sheets'].items():assert sha(live/n[:3]/(n+'.png'))==r['sha256'].upper(),n
  assert len(updated['sheets'])==len(current['sheets']) and sha(exe)==exe_hash
  receipt={'changed_sheets':sorted(records),'other_custom_sheets_preserved':len(current['sheets'])-10,'custom_sheet_count':len(updated['sheets']),'executable_sha256':exe_hash,'version':current['version'],'archive':str(archive),'unchanged_shield_only_town':['wlust','wluwl'],'unchanged_unarmed_town':['wlnst','wlnwl'],'original_bow_staff_and_other_armor_preserved':True};updated['town_equipment_revision']=receipt;text=json.dumps(updated,indent=2);manifest.write_text(text);(mirror/'install-manifest.json').write_text(text);(archive/'install-manifest.json').write_text(text)
  for name in ['town-audit.json','canvas-padding.json','preflight-progress.json','pack-validation.json']:shutil.copy2(work/name,archive/name)
  mounts={}
  for j in plan['jobs']:
   for e in json.loads(Path(j['reference']).read_text())['equipment']:
    mounts[e['town_role']]={k:v for k,v in e.items() if k!='path'};equipment=Path(e['path']);(archive/'Equipment').mkdir(exist_ok=True);shutil.copy2(equipment,archive/'Equipment'/equipment.name)
  (archive/'town-mounts.json').write_text(json.dumps(mounts,indent=2));shutil.copytree(work/'review',archive/'Review');(archive/'install-receipt.json').write_text(json.dumps(receipt,indent=2));(work/'install-receipt.json').write_text(json.dumps(receipt,indent=2))
 except BaseException:
  for n in changed:
   source=archive/'previous-installed'/n[:3]/(n+'.png')
   for target in [live/n[:3]/source.name,mirror/source.name]:
    for suffix in ['', '.layout']:shutil.copy2(source.with_name(source.name+suffix),target.with_name(target.name+suffix))
  manifest.write_bytes(before);(mirror/'install-manifest.json').write_bytes(before);raise
 print('Installed ten equipment-specific town sheets; all other custom sheets and executable unchanged')

if __name__=='__main__':install(*sys.argv[1:])
