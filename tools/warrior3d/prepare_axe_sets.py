"""Prepare selected A1 axe sheets with native two-handed body animation.

python SCRIPT EXISTING_EQUIPMENT_PLAN.json TWO_HAND_SOURCES NEW_PRIVATE_WORK
Render only after audit_axe_sets.py has fitted canvases and checked every pose.
"""
import copy,json,struct,sys,hashlib
from pathlib import Path
from PIL import Image
Image.MAX_IMAGE_PIXELS=None
old,sources,work=map(Path,sys.argv[1:]);plan=json.loads(old.read_text());work=work.resolve();work.mkdir(exist_ok=False);sources=sources.resolve();manifest=json.loads((Path(plan['previous'])/'paladin-vanilla-dimensions/install-manifest.json').read_text());plan.update(work=str(work),equipment_family='light-axe',selected_weapon='A1',selected_weapon_file='twoHandAxe_base01.glb',inventory={'wla':{}},jobs=[],copies=[],motions=[],starting_custom_manifest=manifest,starting_game_hashes={},attack_action_frame=10);models=work/'models';models.mkdir();recipes=work/'recipes';recipes.mkdir()
frames={'as':list(range(0,80,8)),'aw':list(range(0,40,5)),'at':[12*i/9 for i in range(10)]+[16,40,44,48,52,56,60,64,72,84],'ht':[0,4,8,13,19,25]};tags={'as':'idle','aw':'walk-short','at':'attack','ht':'hit'}
for png in sorted((Path(plan['originals'])/'wla').glob('*.png')):
 name=png.stem;action=name[3:];binary=(Path(plan['cl2'])/'wla'/(name+'.cl2')).read_bytes();counts=[struct.unpack_from('<I',binary,o)[0] for o in struct.unpack_from('<8I',binary)];assert len(set(counts))==1;rows=counts[0]
 with Image.open(png) as im:size=list(im.size)
 inv={'original_size':size,'cell':size[0]//8,'rows':rows};plan['inventory']['wla'][name]=inv;live=Path(plan['game'])/'HD/plrgfx/warrior/wla'/png.name;assert live.is_file();plan['starting_game_hashes'][name]=hashlib.sha256(live.read_bytes()).hexdigest().upper()
 if action in ['st','wl','fm','lm','qm']:
  donor=manifest['sheets'][name] if action in ['st','wl'] and manifest.get('town_equipment_revision') and name in manifest['sheets'] else manifest['sheets']['wls'+action];plan['copies'].append({'sheet':name,'path':donor['source']});inv.update(size=donor['size'],canvas_anchor=list(map(int,donor['layout'].split()[2:4])));continue
 assert len(frames[action])==rows;recipe={'name':'A1 native two-handed '+action,'source':str(sources/(tags[action]+'.glb')),'frames':frames[action],'arms':[],'idle':str(sources/'idle.glb'),'preserve_attack_motion':True}
 if action=='at':recipe['idle_weights']=[1,.67,.33]+[0]*17
 if action=='ht':recipe['idle_weights']=[1,0,0,0,0,1]
 rp=recipes/(name+'.json');rp.write_text(json.dumps(recipe,indent=2));model=models/(name+'.glb');root=work/'jobs'/name;root.mkdir(parents=True);ref={'sheet':name+'.png','rows':rows,'cell':1536,'columns':['S','SW','W','NW','N','NE','E','SE'],'source_frames':list(range(rows)),'render_directions':list(range(8)),'sun_position':[3,-4,6],'shadow_distance_gain':1,'shadow_overscan':512,'canvas_logical':[256,192],'canvas_anchor':[128,176],'capture_bounds':True,'preview_prefix':name,'preview_anchor':False,'preview_contact_row':9 if action=='at' else rows//2,'preview_caption':name.upper()+' | A1 native two-handed / contact game frame 10','equipment':[{'path':str(sources/'equipment/twoHandAxe_base01.glb'),'bone':'weapon.R','axis_rotation_z':-90,'local_basis':[[0,0,1],[0,1,0],[-1,0,0]],'scale':1.0}]};reference=root/'reference.json';reference.write_text(json.dumps(ref,indent=2));plan['jobs'].append({'sheet':name,'code':'wla','action':action,'model':str(model),'motion':name,'root':str(root),'reference':str(reference)});plan['motions'].append({'name':name,'model':str(model),'recipe':str(rp)})
assert len(plan['jobs'])==4 and len(plan['copies'])==5;(work/'plan.json').write_text(json.dumps(plan,indent=2));print('Prepared all nine A1 axe sheets with frame-10 attack contact')
