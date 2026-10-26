"""python SCRIPT CURRENT_TOWN_PLAN.json NEW_PRIVATE_WORK [METRES=0.05]
Slide the complete town sword toward its hilt along its existing shaft axis.
"""
import json,copy,sys,math,struct
from pathlib import Path
source,work=map(Path,sys.argv[1:3]);distance=float(sys.argv[3]) if len(sys.argv)>3 else .05;assert 0<distance<=.2;old=json.loads(source.read_text());work=work.resolve();work.mkdir(exist_ok=False);manifest=json.loads((Path(old['previous'])/'paladin-vanilla-dimensions/install-manifest.json').read_text());j=next(j for j in old['jobs'] if j['sheet']=='wldst');gear=json.loads(Path(j['reference']).read_text())['equipment'];mount=copy.deepcopy(next(e['local_transform'] for e in gear if e['town_role']=='town_sword'));length=math.sqrt(sum(mount[k][1]**2 for k in range(3)))
for k in range(3):mount[k][3]=struct.unpack('<f',struct.pack('<f',mount[k][3]+distance*mount[k][1]/length))[0]
recipe=copy.deepcopy(manifest['town_sword_roll_revision']);recipe.update(mount=mount,shaft_slide_from_input=distance);plan=copy.deepcopy(old);plan.update(work=str(work),starting_custom_manifest=manifest,town_sword_roll_revision=recipe,jobs=[],motions=[],starting_game_hashes={})
for j in old['jobs']:
 j=copy.deepcopy(j);name=j['sheet'];plan['starting_game_hashes'][name]=manifest['sheets'][name]['sha256']
 if j['code'] in ['wls','wld']:
  ref=json.loads(Path(j['reference']).read_text())
  for e in ref['equipment']:
   if e['town_role']=='town_sword':e.update(local_transform=mount,town_sword_revision='full-sword-raised-along-shaft-v4')
  root=work/'jobs'/name;root.mkdir(parents=True);rp=root/'reference.json';ref['preview_caption']=name.upper()+' | sword raised along arrow / unchanged angle';rp.write_text(json.dumps(ref,indent=2));j.update(root=str(root),reference=str(rp))
 plan['jobs'].append(j);plan['motions'].append({'name':j['motion']})
(work/'plan.json').write_text(json.dumps(plan,indent=2));print('Raised town sword',distance,'metres along its unchanged shaft; shield poses reused')
