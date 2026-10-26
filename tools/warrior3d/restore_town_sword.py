"""python SCRIPT CURRENT_TOWN_PLAN.json NEW_PRIVATE_WORK
Restore the complete original D4 sword in town, with no custom sheath/hanger.
"""
import json,copy,sys
from pathlib import Path
source,work=map(Path,sys.argv[1:]);old=json.loads(source.read_text());work=work.resolve();work.mkdir(exist_ok=False);manifest=json.loads((Path(old['previous'])/'paladin-vanilla-dimensions/install-manifest.json').read_text());sword=Path(old['assets'])/'sword_base00.glb';assert sword.is_file();plan=copy.deepcopy(old);plan.pop('town_hilt_only_revision',None);plan.update(work=str(work),starting_custom_manifest=manifest,jobs=[],motions=[],starting_game_hashes={},town_bare_sword_revision={'path':str(sword),'full_blade':True,'custom_sheath_and_hanger':False})
for j in old['jobs']:
 j=copy.deepcopy(j);name=j['sheet'];plan['starting_game_hashes'][name]=manifest['sheets'][name]['sha256']
 if j['code'] in ['wls','wld']:
  ref=json.loads(Path(j['reference']).read_text());ref['equipment']=[e for e in ref['equipment'] if e['town_role']!='sword_sheath']
  for e in ref['equipment']:
   if e['town_role'] in ['town_sword_hilt','sheathed_sword','town_sword']:e.update(path=str(sword),town_role='town_sword',town_sword_revision='complete-sword-no-sheath-v3')
  root=work/'jobs'/name;root.mkdir(parents=True);rp=root/'reference.json';ref['preview_caption']=name.upper()+' | complete D4 sword / no custom sheath';rp.write_text(json.dumps(ref,indent=2));j.update(root=str(root),reference=str(rp))
 plan['jobs'].append(j);plan['motions'].append({'name':j['motion']})
(work/'plan.json').write_text(json.dumps(plan,indent=2));print('Prepared four complete-sword updates; closer shields preserved')
