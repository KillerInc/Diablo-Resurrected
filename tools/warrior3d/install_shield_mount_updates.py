"""Install the validated 20-sheet shield mount correction; preserve all other art.

python SCRIPT CORRECTED_PLAN.json NEW_PRIVATE_ARCHIVE_DIRECTORY
Copyrighted art and backups stay in the supplied private directories.
"""
import copy,json,shutil,sys
from pathlib import Path
from build_equipped_sets import sha
from shield_mount import REVISION


def install(plan_file,archive):
 plan=json.loads(Path(plan_file).read_text());assert plan.get('shield_grip_correction')
 work=Path(plan['work']);report=json.loads((work/'pack-validation.json').read_text());assert report['sheet_count']==29
 selected={n:r for n,r in report['sheets'].items() if n.startswith(('wld','wlu'))};assert len(selected)==20
 audit=json.loads((work/'strap-audit.json').read_text());assert len(audit)==14 and not any(r['head_contact_rows'] or r['elbow_strap_wrong_rows'] or r['maximum_grip_error']>.012 for r in audit)
 checks=json.loads((work/'preflight-progress.json').read_text());assert len(checks)==14 and all(r['safe'] for r in checks)
 manifest=Path(plan['previous'])/'paladin-vanilla-dimensions/install-manifest.json';original=manifest.read_bytes();current=json.loads(original);assert current==plan['starting_custom_manifest']
 live=Path(plan['game'])/'HD/plrgfx/warrior';mirror=Path(plan['assets'])/'Vanilla NN8 Dimensions';exe=Path(plan['game'])/'Diablo Reincarnated.exe';exe_hash=sha(exe)
 for n,r in current['sheets'].items():assert sha(live/n[:3]/(n+'.png'))==r['sha256'].upper(),('Installed sheet changed',n)
 for n,r in report['sheets'].items():
  source=Path(r['path']);assert sha(source)==r['sha256'];assert source.with_name(source.name+'.layout').read_text().strip()==r['layout']
  if n not in selected:assert r['sha256']==current['sheets'][n]['sha256'].upper(),('Non-shield sheet changed',n)
 archive=Path(archive);assert not archive.exists();archive.mkdir(parents=True);(archive/'previous-install-manifest.json').write_bytes(original)
 for n,r in selected.items():
  for directory,source in [('previous-installed',live/n[:3]/(n+'.png')),('Final',Path(r['path']))]:
   target=archive/directory/n[:3]/(n+'.png');target.parent.mkdir(parents=True,exist_ok=True)
   for suffix in ['', '.layout']:shutil.copy2(source.with_name(source.name+suffix),target.with_name(target.name+suffix))
 updated=copy.deepcopy(current);changed=[]
 try:
  for n,r in selected.items():
   source=archive/'Final'/n[:3]/(n+'.png');target=live/n[:3]/source.name;changed.append(n)
   for suffix in ['', '.layout']:shutil.copy2(source.with_name(source.name+suffix),target.with_name(target.name+suffix));shutil.copy2(source.with_name(source.name+suffix),mirror/(source.name+suffix))
   updated['sheets'][n].update(source=str(source),size=r['size'],layout=r['layout'],sha256=r['sha256'],shield_grip_revision=REVISION)
  for n,r in updated['sheets'].items():assert sha(live/n[:3]/(n+'.png'))==r['sha256'].upper(),n
  assert len(updated['sheets'])==39 and sha(exe)==exe_hash
  receipt={'revision':REVISION,'changed_sheets':sorted(selected),'other_custom_sheets_preserved':19,'executable_sha256':exe_hash,'version':current['version'],'archive':str(archive),'shadow_border':plan.get('shadow_border'),'all_body_animation_preserved_except_previously_requested_shield_bash_wrist_tilt':True}
  updated['shield_mount_revision']=receipt;text=json.dumps(updated,indent=2);manifest.write_text(text);(mirror/'install-manifest.json').write_text(text);(archive/'install-manifest.json').write_text(text)
  for name in ['strap-audit.json','preflight-progress.json','pack-validation.json']:shutil.copy2(work/name,archive/name)
  shutil.copytree(work/'review',archive/'Review');(archive/'install-receipt.json').write_text(json.dumps(receipt,indent=2));(work/'install-receipt.json').write_text(json.dumps(receipt,indent=2))
 except BaseException:
  for n in changed:
   source=archive/'previous-installed'/n[:3]/(n+'.png');target=live/n[:3]/source.name
   for suffix in ['', '.layout']:shutil.copy2(source.with_name(source.name+suffix),target.with_name(target.name+suffix));shutil.copy2(source.with_name(source.name+suffix),mirror/(source.name+suffix))
  manifest.write_bytes(original);(mirror/'install-manifest.json').write_bytes(original);raise
 print('Installed 20 corrected shield sheets; 19 other custom sheets and executable unchanged')

if __name__=='__main__':install(*sys.argv[1:])
