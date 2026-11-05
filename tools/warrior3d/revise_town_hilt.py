"""python SCRIPT CURRENT_TOWN_PLAN.json PRIVATE_HILT.glb NEW_PRIVATE_WORK
Remove the custom sheath/hanger; town shows only the selected sword's hilt.
"""
import json,copy,sys
from pathlib import Path
source,hilt,work=map(Path,sys.argv[1:]);assert hilt.is_file();old=json.loads(source.read_text());work=work.resolve();work.mkdir(exist_ok=False);manifest=json.loads((Path(old['previous'])/'paladin-vanilla-dimensions/install-manifest.json').read_text());plan=copy.deepcopy(old);plan.update(work=str(work),starting_custom_manifest=manifest,jobs=[],motions=[],starting_game_hashes={},town_hilt_only_revision={'path':str(hilt.resolve()),'sheath_and_hanger_removed':True,'blade_hidden_in_town':True})
for j in old['jobs']:
 j=copy.deepcopy(j);ref=json.loads(Path(j['reference']).read_text());gear=[]
 for e in ref['equipment']:
  if e['town_role']=='sword_sheath':continue
  e=copy.deepcopy(e)
  if e['town_role']=='sheathed_sword':e.update(path=str(hilt.resolve()),town_role='town_sword_hilt',town_sword_revision='hilt-guard-only-v2')
  gear.append(e)
 name=j['sheet'];root=work/'jobs'/name;root.mkdir(parents=True);rp=root/'reference.json';ref.update(equipment=gear,preview_caption=name.upper()+' | hilt/guard at hip / closer centered shield');rp.write_text(json.dumps(ref,indent=2));j.update(reference=str(rp),root=str(root));plan['jobs'].append(j);plan['motions'].append({'name':j['motion']});plan['starting_game_hashes'][name]=manifest['sheets'][name]['sha256']
(work/'plan.json').write_text(json.dumps(plan,indent=2));print('Prepared eight town updates with no custom sheath or hanger')
