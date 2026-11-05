"""Blender --python SCRIPT -- TOWN_PLAN.json MERGED_2HM_SHEATHE.glb NEW_WORK
Stow A1 on the back using the exact native sheathe endpoint relative to chest.
"""
import bpy,json,copy,sys,math,struct
from pathlib import Path
from mathutils import Matrix
source,native,work=map(Path,sys.argv[sys.argv.index('--')+1:]);old=json.loads(source.read_text());work=work.resolve();work.mkdir(exist_ok=False);manifest=json.loads((Path(old['previous'])/'paladin-vanilla-dimensions/install-manifest.json').read_text());axe=Path(manifest['axe_sets']['archive'])/'Equipment/twoHandAxe_base01.glb';assert axe.is_file()
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=str(native.resolve()));rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');assert rig.animation_data.action.name.startswith('palM_2HM_event_sheathe');last=round(rig.animation_data.action.frame_range[1]);bpy.context.scene.frame_set(last);bpy.context.view_layer.update();mount=rig.pose.bones['chest'].matrix.inverted()@rig.pose.bones['weapon.R'].matrix@Matrix.Rotation(-math.pi/2,4,'Z')
# The selected axe's broad face needs the same 90-degree haft roll as combat.
mount=mount@Matrix(((0,0,1,0),(0,1,0,0),(-1,0,0,0),(0,0,0,1)))
plan=copy.deepcopy(old);plan.update(work=str(work),equipment_family='light-town-two-hand-back',two_hand_back_stow_revision=True,jobs=[],motions=[],copies=[],inventory={'wla':{}},starting_game_hashes={},starting_custom_manifest=manifest,attack_action_frame=None,native_sheathe_reference={'path':str(native.resolve()),'clip':'palM_2HM_event_sheathe','last_frame':last,'socket':'weapon.R','relative_to':'chest','axe_haft_roll_degrees':90});plan.pop('town_hilt_only_revision',None);plan.pop('town_bare_sword_revision',None);plan.pop('town_sword_roll_revision',None)
for action in ['st','wl']:
 donor=next(j for j in old['jobs'] if j['sheet']=='wls'+action);name='wla'+action;root=work/'jobs'/name;root.mkdir(parents=True);rp=root/'reference.json';ref=json.loads(Path(donor['reference']).read_text());ref.update(sheet=name+'.png',preview_prefix=name,preview_caption=name.upper()+' | native 2HM final-frame back stow',equipment=[{'path':str(axe),'bone':'chest','local_transform':[list(r) for r in mount],'town_role':'back_two_hand_weapon'}],root_anchor_frame=0)
 png=Path(old['originals'])/'wla'/(name+'.png');binary=(Path(old['cl2'])/'wla'/(name+'.cl2')).read_bytes();rows=[struct.unpack_from('<I',binary,o)[0] for o in struct.unpack_from('<8I',binary)];assert len(set(rows))==1 and rows[0]==ref['rows']
 with png.open('rb') as f:f.seek(16);size=list(struct.unpack('>II',f.read(8)))
 plan['inventory']['wla'][name]={'original_size':size,'cell':size[0]//8,'rows':rows[0]};rp.write_text(json.dumps(ref,indent=2));j=copy.deepcopy(donor);j.update(sheet=name,code='wla',action=action,motion=name,root=str(root),reference=str(rp));plan['jobs'].append(j);plan['motions'].append({'name':name});plan['starting_game_hashes'][name]=manifest['sheets'][name]['sha256']
(work/'plan.json').write_text(json.dumps(plan,indent=2));print('Native 2HM sheathe last frame:',last,'; prepared axe town idle/walk')
