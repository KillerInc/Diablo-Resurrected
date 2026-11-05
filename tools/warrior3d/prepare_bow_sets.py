"""Blender --python SCRIPT -- EXISTING_EQUIPMENT_PLAN.json PRIVATE_BOW_WORK [PREPARED_SOURCES]
Requires selected and anatomically aligned local Rogue clips in WORK/sources or PREPARED_SOURCES.
Preserve existing warrior body, art scale, tile stride and approved spell sheets.
"""
import bpy,json,copy,struct,sys,math
from pathlib import Path
from mathutils import Matrix,Vector
sys.path.insert(0,str(Path(__file__).parent));from author_equipped_motion import author
from merge_paladin_walk import read
from bake_bow_equipment import bake
basefile,work=map(Path,sys.argv[sys.argv.index('--')+1:sys.argv.index('--')+3]);base=json.loads(basefile.read_text());work=work.resolve();sources=Path(sys.argv[sys.argv.index('--')+3]).resolve() if len(sys.argv)>sys.argv.index('--')+3 else work/'sources';assert not (work/'plan.json').exists();previous=Path(base['previous']);assets=Path(base['assets']);manifest=json.loads((previous/'paladin-vanilla-dimensions/install-manifest.json').read_text());models=work/'models';recipes=work/'recipes';equipment=work/'equipment'
for p in [models,recipes,equipment]:p.mkdir(parents=True,exist_ok=True)
for name in ['idle','walk','heartseeker','hit']:assert (sources/(name+'-aligned.glb')).is_file(),name
g,_=read(previous/'paladin-sword-shield/Paladin-armed-idle-body.glb');names={n.get('name'):i for i,n in enumerate(g['nodes'])}
def branch(i):return {i}|set().union(*(branch(c) for c in g['nodes'][i].get('children',[])))
finger_names=[g['nodes'][i]['name'] for i in branch(names['hand.L']) if i not in [names['hand.L'],names['weapon.L']]];overlay={'source':str(previous/'paladin-sword-shield/Paladin-armed-idle-body.glb'),'nodes':finger_names}
def motion(name,source,frames,**extra):
 spec={'name':name,'source':str(source),'frames':list(frames),'arms':[],'node_overlays':[{**overlay,'frames':[0]*len(frames)}],**extra};rp=recipes/(name+'.json');rp.write_text(json.dumps(spec,indent=2));model=models/(name+'.glb');author(rp,model);return model
idle0=motion('bow-idle-raw',sources/'idle-aligned.glb',range(0,40,5));idle=motion('bow-idle',idle0,range(8),hand_offsets={'L':[[.12,.12,.20]]*8},node_overlays=[])
walk0=motion('bow-short-walk-raw',previous/'paladin-short-stride-final/Paladin-short-stride.glb',range(0,40,5),arms=[{'side':s,'source':str(sources/'walk-aligned.glb'),'frames':list(range(0,32,4))} for s in ['L','R']]);walk=motion('bow-short-walk',walk0,range(8),hand_offsets={'L':[[.12,.12,.20]]*8},node_overlays=[])
hit=motion('bow-hit',previous/'paladin-hit/Paladin-hit.glb',[0,4,8,13,19,25],arms=[{'side':'L','source':str(sources/'idle-aligned.glb'),'frames':[0]*6}])
frames=[0,.5,1,2,3,4,5,5.5,6,6.5,7,9,13,22,34,40];weights=[1,.8,.6,.35,.15,0,0,0,0,0,0,.2,.45,.7,.9,1];attack0=motion('bow-shot-base',sources/'heartseeker-aligned.glb',frames,idle=str(idle),idle_weights=weights,align_horizontal_root=True)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=str(attack0));rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');offsets=[];amount=[0,0,0,0,0,.2,.4,.6,.8,1,1,.5,.1,0,0,0]
for row in range(16):
 bpy.context.scene.frame_set(row);bpy.context.view_layer.update();l=rig.matrix_world@rig.pose.bones['hand.L'].matrix@Vector((0,.05,0));r=rig.matrix_world@rig.pose.bones['hand.R'].matrix@Vector((.0425,.0825,-.002));offsets.append([(l.x-r.x)*amount[row],(l.z-r.z)*amount[row],0])
attack=motion('bow-shot',attack0,range(16),hand_offsets={'R':offsets},node_overlays=[])
static=bake(assets/'twoHandBow_base01.glb',equipment/'Bow_B1_Static.glb');carry_idle=bake(assets/'twoHandBow_base01.glb',equipment/'Bow_B1_AS.glb',idle,8,mode='carry');carry_walk=bake(assets/'twoHandBow_base01.glb',equipment/'Bow_B1_AW.glb',walk,8,mode='carry');shot=bake(assets/'twoHandBow_base01.glb',equipment/'Bow_B1_Shot.glb',attack,16,10)
town=json.loads((previous/'town-equipment/plan.json').read_text());town_models={a:next(j['model'] for j in town['jobs'] if j['sheet']=='wls'+a) for a in ['st','wl']};back_profile=json.loads((Path(manifest['two_hand_back_stow_revision']['archive'])/'town-mounts.json').read_text())['back_two_hand_weapon'];back=Matrix(back_profile['local_transform'])@Matrix.Translation((0,-.85,0))
plan=copy.deepcopy(base);plan.update(work=str(work),equipment_family='light-bow',selected_weapon='B1',selected_weapon_file='twoHandBow_base01.glb',starting_custom_manifest=manifest,starting_game_hashes={},inventory={'wlb':{}},jobs=[],copies=[],motions=[],attack_action_frame=11,casting_action_frame=14,bow_release_native_frame=7,bow_shot_clip='rogM_bow_attk_heartSeeker',bow_back_reference={'clip':'palM_2HM_event_sheathe','last_frame':49,'grip_origin_correction':[0,-.85,0]});plan.pop('two_hand_back_stow_revision',None);plan.pop('town_hilt_only_revision',None);plan.pop('town_bare_sword_revision',None);plan.pop('town_sword_roll_revision',None)
for png in sorted((Path(base['originals'])/'wlb').glob('*.png')):
 name=png.stem;action=name[3:];data=(Path(base['cl2'])/'wlb'/(name+'.cl2')).read_bytes();counts=[struct.unpack_from('<I',data,x)[0] for x in struct.unpack_from('<8I',data)];assert len(set(counts))==1;rows=counts[0]
 with png.open('rb') as f:f.seek(16);size=list(struct.unpack('>II',f.read(8)))
 inv={'original_size':size,'cell':size[0]//8,'rows':rows};plan['inventory']['wlb'][name]=inv;live=Path(base['game'])/'HD/plrgfx/warrior/wlb'/png.name;assert live.is_file();import hashlib;plan['starting_game_hashes'][name]=hashlib.sha256(live.read_bytes()).hexdigest().upper()
 if action in ['fm','lm','qm']:
  donor=manifest['sheets']['wls'+action];assert donor['size'][1]%(rows*8)==0;plan['copies'].append({'sheet':name,'path':donor['source']});inv.update(size=donor['size'],canvas_anchor=list(map(int,donor['layout'].split()[2:4])));continue
 model={'as':str(idle),'aw':str(walk),'at':str(attack),'ht':str(hit),'st':town_models['st'],'wl':town_models['wl']}[action];root=work/'jobs'/name;root.mkdir(parents=True);rp=root/'reference.json';held=action not in ['st','wl'];chosen={'as':carry_idle,'aw':carry_walk,'at':shot}.get(action,static);gear=[{'path':str(chosen),'bone':'hand.L','orientation_socket':'weapon.L','grip':[0,0,0],'hand_point':[0,.05,0],'scale':1,'town_role':'held_bow','allow_bow_hand_contact':True}] if held else [{'path':str(static),'bone':'chest','local_transform':[list(r) for r in back],'town_role':'back_bow'}]
 ref={'sheet':name+'.png','rows':rows,'cell':1536,'columns':['S','SW','W','NW','N','NE','E','SE'],'source_frames':list(range(rows)),'render_directions':list(range(8)),'sun_position':[3,-4,6],'shadow_distance_gain':1,'shadow_overscan':512,'canvas_logical':[256,192],'canvas_anchor':[128,176],'root_anchor_frame':0,'preview_prefix':name,'preview_anchor':False,'preview_contact_row':10 if action=='at' else rows//2,'preview_caption':name.upper()+' | B1 bow / release frame 11','equipment':gear};rp.write_text(json.dumps(ref,indent=2));plan['jobs'].append({'sheet':name,'code':'wlb','action':action,'model':model,'motion':name,'reference':str(rp),'root':str(root)});plan['motions'].append({'name':name})
assert len(plan['jobs'])==6 and len(plan['copies'])==3;(work/'plan.json').write_text(json.dumps(plan,indent=2));print('Prepared nine bow sheets; native contact 7 maps to game frame 11')
