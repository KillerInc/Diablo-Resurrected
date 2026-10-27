"""Blender --python SCRIPT -- EXISTING_BOW_PLAN.json NEW_PRIVATE_WORK
Prepare T1 staff sheets from existing Paladin motions, without source edits.
"""
import bpy,json,copy,sys,struct,hashlib,math
from pathlib import Path
from mathutils import Matrix,Vector
sys.path.insert(0,str(Path(__file__).parent))
from author_equipped_motion import author
from bake_staff_equipment import bake
source,work=map(Path,sys.argv[sys.argv.index('--')+1:]);old=json.loads(source.read_text());work=work.resolve();assert not (work/'plan.json').exists();work.mkdir(exist_ok=True);prev=Path(old['previous']);assets=Path(old['assets']);manifest=json.loads((prev/'paladin-vanilla-dimensions/install-manifest.json').read_text());axe=json.loads((prev/'axe-sets/plan.json').read_text());town=json.loads((prev/'town-equipment/plan.json').read_text());equipped=json.loads((prev/'equipped-sets/plan.json').read_text());weapon=assets/'twoHandStaff_base01.glb';assert weapon.is_file()
plan=copy.deepcopy(old);plan.update(work=str(work),equipment_family='light-staff',selected_weapon='T1',selected_weapon_file=weapon.name,starting_custom_manifest=manifest,starting_game_hashes={},inventory={'wlt':{}},jobs=[],copies=[],motions=[],attack_action_frame=11,casting_action_frame=14,staff_scale=.8)
models=work/'models';models.mkdir(exist_ok=True);recipes=work/'recipes';recipes.mkdir(exist_ok=True);idle=prev/'axe-options/sources/idle.glb';back=Matrix(json.loads((Path(manifest['two_hand_back_stow_revision']['archive'])/'town-mounts.json').read_text())['back_two_hand_weapon']['local_transform'])
# Undo the axe-only haft roll, then normalize the staff grip and scale.
quarter=Matrix(((0,0,1,0),(0,1,0,0),(-1,0,0,0),(0,0,0,1)))
back=back@quarter.inverted()@Matrix.Translation((0,-.65,0))@Matrix.Scale(.8,4)@Matrix.Translation((0,.1625,0))@Matrix.Rotation(math.pi,4,'X')@Matrix.Translation((0,-.1625,0))
for png in sorted((Path(old['originals'])/'wlt').glob('*.png')):
 name=png.stem;a=name[3:];data=(Path(old['cl2'])/'wlt'/(name+'.cl2')).read_bytes();counts=[struct.unpack_from('<I',data,x)[0] for x in struct.unpack_from('<8I',data)];assert len(set(counts))==1;rows=counts[0]
 with png.open('rb') as f:f.seek(16);size=list(struct.unpack('>II',f.read(8)))
 inv={'original_size':size,'cell':size[0]//8,'rows':rows};plan['inventory']['wlt'][name]=inv;plan['starting_game_hashes'][name]=hashlib.sha256((Path(old['game'])/'HD/plrgfx/warrior/wlt'/png.name).read_bytes()).hexdigest().upper();root=work/'jobs'/name;root.mkdir(parents=True,exist_ok=True);rp=root/'reference.json'
 ref={'sheet':name+'.png','rows':rows,'cell':1536,'columns':['S','SW','W','NW','N','NE','E','SE'],'source_frames':list(range(rows)),'render_directions':list(range(8)),'sun_position':[3,-4,6],'shadow_distance_gain':1,'shadow_overscan':512,'canvas_logical':[256,192],'canvas_anchor':[128,176],'root_anchor_frame':0,'preview_prefix':name,'preview_anchor':False,'preview_contact_row':10 if a=='at' else rows//2,'preview_caption':name.upper()+' | T1 staff / impact frame 11'}
 gear={'path':str(weapon),'bone':'hand.R','orientation_socket':'weapon.R','axis_rotation_z':-90,'grip':[0,-.2,0],'hand_point':[.0425,.0825,-.002],'scale':.8,'town_role':'held_staff','allow_hand_grip_contact':True}
 if a in ['as','aw','ht']:
  donor=next(j for j in axe['jobs'] if j['action']==a);model=Path(donor['model'])
 elif a=='at':
  recipe={'name':'T1 full native two-handed staff strike','source':str(prev/'axe-options/sources/attack.glb'),'frames':[0,1.2,2.4,2.4,4.8,6,7.2,8.4,9.6,10.8,12]+[16,40,52,64,84],'arms':[],'idle':str(idle),'idle_weights':[1,.67,.33]+[0]*13,'preserve_attack_motion':True,'hand_offsets':{s:[[0,0,z] for z in [.2,.25,.35,.35,.5,.45,.35,.25]+[.2]*8] for s in ['R','L']}};p=recipes/(name+'.json');p.write_text(json.dumps(recipe,indent=2));model=models/(name+'.glb');author(p,model);fitted=work/'staff-attack.glb';bake(model,weapon,fitted,16);gear={'path':str(fitted),'bone':'hand.R','local_transform':[list(r) for r in Matrix.Identity(4)],'town_role':'held_staff','allow_hand_grip_contact':True}
 elif a in ['st','wl']:
  model=Path(next(j['model'] for j in town['jobs'] if j['sheet']=='wls'+a));gear={'path':str(weapon),'bone':'chest','local_transform':[list(r) for r in back],'town_role':'back_staff'}
 else:
  donor=next(j for j in equipped['jobs'] if j['sheet']=='wld'+a);ref.update(json.loads(Path(donor['reference']).read_text()));ref.update(sheet=name+'.png',rows=rows,cell=1536,render_directions=list(range(8)),source_frames=list(range(rows)),preview_prefix=name,preview_caption=name.upper()+' | T1 held staff / approved spell effect',preview_contact_row=13,root_anchor_frame=0);ref.pop('pose_offsets',None)
  recipe={'name':'T1 one-handed staff casting','source':str(prev/'paladin-fire-bubble/gizmo-final/Paladin-fire-cast.glb'),'frames':list(range(20)),'arms':[{'side':'R','source':str(next(j['model'] for j in town['jobs'] if j['sheet']=='wlsst')),'frames':[0]*20}],'idle':str(idle),'finger_grip':['R']};p=recipes/(name+'.json');p.write_text(json.dumps(recipe,indent=2));model=models/(name+'.glb');author(p,model)
  bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=str(model));rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');bpy.context.scene.frame_set(0);bpy.context.view_layer.update();basis=Matrix(((1,0,0),(0,0,1),(0,-1,0))).to_4x4()@Matrix.Scale(.8,4);point=rig.matrix_world@rig.pose.bones['hand.R'].matrix@Vector((.0425,.0825,-.002));basis.translation=point-basis@Vector((0,.4,0));gear={'path':str(weapon),'bone':'hand.R','local_transform':[list(r) for r in (rig.matrix_world@rig.pose.bones['hand.R'].matrix).inverted()@basis],'town_role':'held_staff','allow_hand_grip_contact':True}
 ref['equipment']=[gear];rp.write_text(json.dumps(ref,indent=2));plan['jobs'].append({'sheet':name,'code':'wlt','action':a,'model':str(model),'root':str(root),'reference':str(rp),'motion':name});plan['motions'].append({'name':name})
(work/'plan.json').write_text(json.dumps(plan,indent=2));print('Prepared all nine T1 staff sheets')
