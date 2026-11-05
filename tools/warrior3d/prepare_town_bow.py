"""Blender --python SCRIPT -- INSTALLED_BOW_PLAN.json NEW_WORK
Replace only town ST/WL with vanilla-style low left-hand bow carry.
"""
import bpy,copy,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from author_equipped_motion import author
from merge_paladin_walk import read
from bake_bow_equipment import bake
source,work=map(Path,sys.argv[sys.argv.index('--')+1:]);old=json.loads(source.read_text());work=work.resolve();work.mkdir(exist_ok=False)
manifest=json.loads((Path(old['previous'])/'paladin-vanilla-dimensions/install-manifest.json').read_text())
finger_source=Path(old['previous'])/'paladin-sword-shield/Paladin-armed-idle-body.glb';g,_=read(finger_source);names={n.get('name'):i for i,n in enumerate(g['nodes'])}
def branch(i):return {i}|set().union(*(branch(c) for c in g['nodes'][i].get('children',[])))
fingers=[g['nodes'][i]['name'] for i in branch(names['hand.L']) if i not in [names['hand.L'],names['weapon.L']]]
plan=copy.deepcopy(old);plan.update(work=str(work),equipment_family='light-town-bow',town_bow_revision=True,starting_custom_manifest=manifest,jobs=[],motions=[],copies=[],inventory={'wlb':{}},starting_game_hashes={},bow_town_carry='low left hand, horizontal front-to-back; back reserved for future quiver')
for a in ['st','wl']:
 name='wlb'+a;donor=next(j for j in old['jobs'] if j['sheet']==name);root=work/'jobs'/name;root.mkdir(parents=True);ref=json.loads(Path(donor['reference']).read_text());rows=ref['rows'];recipe=work/(name+'-recipe.json');model=work/(name+'-body.glb')
 recipe.write_text(json.dumps({'name':name+'-hand-carry','source':donor['model'],'frames':list(range(rows)),'arms':[],'node_overlays':[{'source':str(finger_source),'nodes':fingers,'frames':[0]*rows}],'hand_offsets':{'L':[[.10,0,.02]]*rows}},indent=2));author(recipe,model)
 bow=bake(Path(old['assets'])/'twoHandBow_base01.glb',work/(name+'-bow.glb'),model,rows,mode='town')
 ref.update(equipment=[{'path':str(bow),'bone':'hand.L','orientation_socket':'weapon.L','grip':[0,0,0],'hand_point':[0,.05,0],'scale':1,'town_role':'held_bow','allow_bow_hand_contact':True}],preview_caption=name.upper()+' | vanilla-style low bow carry')
 rp=root/'reference.json';rp.write_text(json.dumps(ref,indent=2));j=copy.deepcopy(donor);j.update(model=str(model),root=str(root),reference=str(rp));plan['jobs'].append(j);plan['motions'].append({'name':j['motion']});plan['inventory']['wlb'][name]=copy.deepcopy(old['inventory']['wlb'][name]);plan['starting_game_hashes'][name]=manifest['sheets'][name]['sha256']
(work/'plan.json').write_text(json.dumps(plan,indent=2));print('Prepared two town bow carry sheets')
