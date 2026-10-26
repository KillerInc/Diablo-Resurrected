"""Install the selected A1 two-handed axe sheets with exact backups.

python SCRIPT VALIDATED_AXE_PLAN.json NEW_PRIVATE_ARCHIVE_DIRECTORY
Preserves every existing custom sheet and the modified executable.
"""
import copy,json,shutil,sys
from pathlib import Path
from build_equipped_sets import sha,fingerprint

def install(plan_file,archive):
 plan=json.loads(Path(plan_file).read_text());assert plan.get('equipment_family')=='light-axe' and plan.get('selected_weapon')=='A1';work=Path(plan['work']);report=json.loads((work/'pack-validation.json').read_text());records=report['sheets'];assert report['sheet_count']==len(records)==9 and all(n.startswith('wla') for n in records)
 audits=json.loads((work/'axe-audit.json').read_text());assert len(audits)==4 and all(not a['contact_rows'] and a['max_right_grip_error']<.04 and a['max_left_shaft_error']<.22 for a in audits)
 if plan.get('axe_edge_revision'):
  edge=json.loads((work/'edge-orientation-check.json').read_text())['samples'];assert len(edge)==7 and sum(r['new_broad_face_alignment'] for r in edge)<sum(r['old_broad_face_alignment'] for r in edge)/2,'Edge orientation not verified'
 checks=json.loads((work/'preflight-progress.json').read_text());assert len(checks)==4 and all(c['safe'] for c in checks)
 for j in plan['jobs']:
  equipment=json.loads(Path(j['reference']).read_text())['equipment'];assert len(equipment)==1 and equipment[0]['bone']=='weapon.R' and equipment[0]['scale']==1.0,'Use the native two-hand socket and fitted A1'
  mark=json.loads((Path(j['root'])/'completed.json').read_text());assert mark['fingerprint']==fingerprint(j)
 manifest=Path(plan['previous'])/'paladin-vanilla-dimensions/install-manifest.json';before=manifest.read_bytes();current=json.loads(before);assert current==plan['starting_custom_manifest'];assert (set(records)<=set(current['sheets'])) if plan.get('axe_edge_revision') else not (set(records)&set(current['sheets'])),'Use an explicit axe revision plan for installed sheets'
 live=Path(plan['game'])/'HD/plrgfx/warrior';mirror=Path(plan['assets'])/'Vanilla NN8 Dimensions';exe=Path(plan['game'])/'Diablo Reincarnated.exe';exe_hash=sha(exe)
 for name,r in current['sheets'].items():assert sha(live/name[:3]/(name+'.png'))==r['sha256'].upper(),name
 for name,r in records.items():
  p=Path(r['path']);assert sha(p)==r['sha256'];assert p.with_name(p.name+'.layout').read_text().strip()==r['layout'];assert sha(live/name[:3]/p.name)==plan['starting_game_hashes'][name],('Target changed',name)
 archive=Path(archive);assert not archive.exists();archive.mkdir(parents=True);(archive/'previous-install-manifest.json').write_bytes(before);previous={}
 for name,r in records.items():
  source=Path(r['path']);target=archive/'Final'/name[:3]/source.name;target.parent.mkdir(parents=True,exist_ok=True)
  for suffix in ['', '.layout']:shutil.copy2(source.with_name(source.name+suffix),target.with_name(target.name+suffix))
  for kind,path in [('game',live/name[:3]/source.name),('mirror',mirror/source.name)]:
   for suffix in ['', '.layout']:
    old=path.with_name(path.name+suffix);key=kind+'/'+name+suffix;previous[key]=old.exists()
    if old.exists():dest=archive/('previous-'+kind)/name[:3]/old.name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(old,dest)
 updated=copy.deepcopy(current);changed=[]
 try:
  for name,r in records.items():
   source=archive/'Final'/name[:3]/(name+'.png');changed.append(name)
   for target in [live/name[:3]/source.name,mirror/source.name]:
    for suffix in ['', '.layout']:shutil.copy2(source.with_name(source.name+suffix),target.with_name(target.name+suffix))
   updated['sheets'][name]={'source':str(source),'size':r['size'],'layout':r['layout'],'sha256':r['sha256'],'status':'A1 native two-handed axe/socket; approved body and SE shadows'}
  for name,r in updated['sheets'].items():assert sha(live/name[:3]/(name+'.png'))==r['sha256'].upper(),name
  assert len(updated['sheets'])==len(current['sheets'])+(0 if plan.get('axe_edge_revision') else 9) and sha(exe)==exe_hash
  receipt={'selected_weapon':'A1 twoHandAxe_base01.glb','installed_sheets':sorted(records),'changed_sheets':sorted(n for n in records if n not in current['sheets'] or current['sheets'][n]['sha256'].upper()!=records[n]['sha256'].upper()),'previous_custom_sheets_preserved':sum(n not in records or current['sheets'][n]['sha256'].upper()==records[n]['sha256'].upper() for n in current['sheets']),'custom_sheet_count':len(updated['sheets']),'executable_sha256':exe_hash,'version':current['version'],'archive':str(archive),'game_contact_frame':10,'native_motion_with_idle_start_blend':True,'edge_first_revision':bool(plan.get('axe_edge_revision'))};updated['axe_sets']=receipt;text=json.dumps(updated,indent=2);manifest.write_text(text);(mirror/'install-manifest.json').write_text(text);(archive/'install-manifest.json').write_text(text)
  for name in ['pack-validation.json','axe-audit.json','preflight-progress.json']:shutil.copy2(work/name,archive/name)
  if (work/'edge-orientation-check.json').exists():shutil.copy2(work/'edge-orientation-check.json',archive/'edge-orientation-check.json')
  equipment=Path(json.loads(Path(plan['jobs'][0]['reference']).read_text())['equipment'][0]['path']);(archive/'Equipment').mkdir();shutil.copy2(equipment,archive/'Equipment'/equipment.name);shutil.copy2(equipment.with_suffix('.fit.json'),archive/'Equipment'/equipment.with_suffix('.fit.json').name);shutil.copy2(work/'canvas-padding.json',archive/'canvas-padding.json')
  shutil.copytree(work/'review',archive/'Review');(archive/'previous-files.json').write_text(json.dumps(previous,indent=2));(archive/'install-receipt.json').write_text(json.dumps(receipt,indent=2));(work/'install-receipt.json').write_text(json.dumps(receipt,indent=2))
 except BaseException:
  for name in changed:
   for kind,path in [('game',live/name[:3]/(name+'.png')),('mirror',mirror/(name+'.png'))]:
    for suffix in ['', '.layout']:
     target=path.with_name(path.name+suffix)
     if previous[kind+'/'+name+suffix]:shutil.copy2(archive/('previous-'+kind)/name[:3]/target.name,target)
     elif target.exists():target.unlink()
  manifest.write_bytes(before);(mirror/'install-manifest.json').write_bytes(before);raise
 print('Installed nine A1 axe sheets; '+str(receipt['previous_custom_sheets_preserved'])+' existing custom sheets and executable unchanged')

if __name__=='__main__':install(*sys.argv[1:])
