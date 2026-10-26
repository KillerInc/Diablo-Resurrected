"""Prepare a private 90-degree axe-head roll correction, retaining all body data.

python SCRIPT INSTALLED_AXE_PLAN.json NEW_PRIVATE_WORK
Run audit_axe_sets.py, full rendering/validation and install_axe_sets.py afterward.
"""
import copy,json,sys
from pathlib import Path
source,work=map(Path,sys.argv[1:]);old=json.loads(source.read_text());assert old['equipment_family']=='light-axe';work=work.resolve();work.mkdir(exist_ok=False);plan=copy.deepcopy(old);manifest=json.loads((Path(old['previous'])/'paladin-vanilla-dimensions/install-manifest.json').read_text());plan.update(work=str(work),starting_custom_manifest=manifest,axe_edge_revision=True,reuse_body_animation=True,jobs=[])
for j in old['jobs']:
 j=copy.deepcopy(j);ref=json.loads(Path(j['reference']).read_text());ref['equipment'][0]['local_basis']=[[0,0,1],[0,1,0],[-1,0,0]];ref['preview_caption']='A1 edge-first orientation | unchanged native body motion';root=work/'jobs'/j['sheet'];root.mkdir(parents=True);reference=root/'reference.json';reference.write_text(json.dumps(ref,indent=2));j.update(root=str(root),reference=str(reference));plan['jobs'].append(j)
plan['starting_game_hashes']={n:manifest['sheets'][n]['sha256'] for n in old['starting_game_hashes']};(work/'plan.json').write_text(json.dumps(plan,indent=2));print('Prepared equipment-only axe orientation revision')
