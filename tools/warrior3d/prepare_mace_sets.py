"""Prepare all 19 light-warrior mace sheets from existing approved body animations.

python SCRIPT SHIELD_PLAN.json EQUIPPED_PLAN.json SWORD_ATTACK_PLAN.json MOUNTS.json NEW_WORK
Only the rigid right-hand weapon is replaced; existing action timing is retained.
"""
import copy,json,struct,sys,hashlib
from pathlib import Path
import numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS=None
shield_file,equipped_file,attack_file,mounts_file,work=map(Path,sys.argv[1:]);shield=json.loads(shield_file.read_text());equipped=json.loads(equipped_file.read_text());attack=json.loads(attack_file.read_text());mounts=json.loads(mounts_file.read_text());work=work.resolve();work.mkdir(exist_ok=False)
plan=copy.deepcopy(shield);manifest=json.loads((Path(plan['previous'])/'paladin-vanilla-dimensions/install-manifest.json').read_text());plan.update(work=str(work),equipment_family='light-mace',selected_weapon='M1',selected_weapon_file='mace_base03.glb',inventory={},jobs=[],copies=[],motions=[],starting_custom_manifest=manifest,starting_game_hashes={});plan.pop('shield_grip_correction',None);plan.pop('author_once',None);plan.pop('shadow_border',None)
source_jobs={j['sheet']:j for j in equipped['jobs']};source_jobs.update({j['sheet']:j for j in shield['jobs']});source_jobs.update({j['sheet']:j for j in attack['jobs'] if j['sheet']=='wlsat'})
for code,donor_code in [('wlm','wls'),('wlh','wld')]:
 plan['inventory'][code]={}
 for image in sorted((Path(plan['originals'])/code).glob('*.png')):
  name=image.stem;action=name[3:];donor=donor_code+action;binary=(Path(plan['cl2'])/code/(name+'.cl2')).read_bytes();counts=[struct.unpack_from('<I',binary,o)[0] for o in struct.unpack_from('<8I',binary)];assert len(set(counts))==1;rows=counts[0]
  with Image.open(image) as im:size=list(im.size)
  assert size==[size[0],size[0]//8*rows];inventory={'original_size':size,'cell':size[0]//8,'rows':rows};plan['inventory'][code][name]=inventory;live=Path(plan['game'])/'HD/plrgfx/warrior'/code/image.name;assert live.is_file();plan['starting_game_hashes'][name]=hashlib.sha256(live.read_bytes()).hexdigest().upper()
  if action in ['st','wl','fm','lm','qm']:
   record=manifest['sheets'][donor];plan['copies'].append({'sheet':name,'path':record['source']});inventory.update(size=record['size'],canvas_anchor=list(map(int,record['layout'].split()[2:4])));continue
  job=copy.deepcopy(source_jobs[donor]);ref=json.loads(Path(job['reference']).read_text());assert rows==ref['rows'];item=next(e for e in ref['equipment'] if Path(e['path']).name=='sword_base00.glb');matrix=np.array(item.get('local_transform',mounts[0]['local_transform']),dtype=float);point=matrix[:3,:3]@np.array(item['grip'])+matrix[:3,3];grip=np.array([0,.18,0]);matrix[:3,3]=point-matrix[:3,:3]@grip;item.update(path=str(Path(plan['assets'])/'mace_base03.glb'),grip=grip.tolist(),local_transform=matrix.tolist());ref.update(sheet=name+'.png',preview_prefix=name,preview_caption=name.upper()+' | selected M1 / approved shield / full native attack',render_directions=list(range(8)))
  root=work/'jobs'/name;root.mkdir(parents=True);reference=root/'reference.json';reference.write_text(json.dumps(ref,indent=2));job.update(sheet=name,code=code,action=action,reference=str(reference),root=str(root),motion=name);plan['jobs'].append(job);plan['motions'].append({'name':name});logical=ref['canvas_logical'];width,height=[logical,logical] if isinstance(logical,int) else logical;inventory.update(size=[width*64,height*8*rows],canvas_logical=[width,height],canvas_anchor=ref['canvas_anchor'])
assert len(plan['jobs'])==9 and len(plan['copies'])==10 and sum(map(len,plan['inventory'].values()))==19
(work/'plan.json').write_text(json.dumps(plan,indent=2));print('Prepared 19 mace sheets: 9 existing body animations and 10 approved town/cast copies')
