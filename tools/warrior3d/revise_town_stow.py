"""Blender --python SCRIPT -- TOWN_PLAN.json MERGED_SHEATHE.glb BACK_SHIELD.glb NEW_WORK
Use the exact native sheathe endpoint socket; mount town shields on the back.
Private clips, models, props and rendered artwork stay outside Git.
"""
import bpy,copy,json,sys,math
from pathlib import Path
from mathutils import Matrix,Vector
old,native,back_shield,work=map(Path,sys.argv[sys.argv.index('--')+1:]);assert back_shield.is_file();base=json.loads(old.read_text());work=work.resolve();work.mkdir(exist_ok=False);previous=Path(base['previous']);manifest=json.loads((previous/'paladin-vanilla-dimensions/install-manifest.json').read_text())
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=str(native.resolve()));rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');end=round(rig.animation_data.action.frame_range[1]);bpy.context.scene.frame_set(end);bpy.context.view_layer.update()
assert rig.animation_data.action.name.startswith('palM_1hsShd_event_sheathe')
sword=rig.pose.bones['pelvis'].matrix.inverted()@rig.pose.bones['weapon.R'].matrix@Matrix.Rotation(-math.pi/2,4,'Z')@Matrix.Scale(.75,4)
jobs={j['sheet']:j for j in base['jobs']};unarmed={a:jobs['wls'+a]['model'] for a in ['st','wl']}
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=unarmed['st']);rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');bpy.context.scene.frame_set(0);bpy.context.view_layer.update();chest=rig.matrix_world@rig.pose.bones['chest'].matrix
# Chest X points backward, Y follows the spine, Z points across the shoulders.
# Center on that anatomical frame instead of the world axes of the twisted idle.
# Compensate the source rim's small local-X center offset (0.005992).
shield=Matrix(((0,0,.92,.14),(0,.92,0,-.025),(-.92,0,0,.92*.0059919655),(0,0,0,1)))
# Native endpoint puts this different, wider outfit's sheath into its leg.
# Preserve the native angle; fit the rigid assembly around outfit and hand.
sword.translation+=(rig.matrix_world@rig.pose.bones['pelvis'].matrix).to_3x3().inverted()@Vector((.10,.18,-.08))
if manifest.get('town_sword_roll_revision'):sword=Matrix(manifest['town_sword_roll_revision']['mount'])
plan=copy.deepcopy(base);plan.update(work=str(work),equipment_family='light-town-stow',town_back_stow_revision=True,native_sheathe_reference={'path':str(native.resolve()),'clip':'palM_1hsShd_event_sheathe','last_frame':end,'socket':'weapon.R','mount_relative_to':'pelvis','outfit_clearance_offset_world':[.10,.18,-.08]},starting_custom_manifest=manifest,starting_game_hashes={},jobs=[],motions=[],copies=[],inventory={})
for code in ['wls','wld','wlh','wlu']:
 plan['inventory'][code]={}
 for action in ['st','wl']:
  name=code+action;donor=jobs[('wls' if code=='wlu' else code)+action];j=copy.deepcopy(donor);ref=json.loads(Path(j['reference']).read_text());gear=[]
  for item in ref['equipment']:
   if (manifest.get('town_hilt_only_revision') or manifest.get('town_bare_sword_revision')) and item['town_role']=='sword_sheath':continue
   if item['town_role']=='carried_shield' or code=='wlu':continue
   item=copy.deepcopy(item)
   if item['town_role'] in ['sheathed_sword','sword_sheath']:item['local_transform']=[list(r) for r in sword]
   if manifest.get('town_hilt_only_revision') and item['town_role']=='sheathed_sword':item.update(path=manifest['town_hilt_only_revision']['path'],town_role='town_sword_hilt')
   if manifest.get('town_bare_sword_revision') and item['town_role'] in ['sheathed_sword','town_sword_hilt']:item.update(path=manifest['town_bare_sword_revision']['path'],town_role='town_sword')
   gear.append(item)
  if code!='wls':gear.append({'path':str(back_shield.resolve()),'bone':'chest','local_transform':[list(r) for r in shield],'town_role':'back_shield','shield_grip_revision':'small-handgrip-180-v1','town_stow_revision':'centered-close-chest-frame-v4','allow_rear_band_body_overlap':True})
  root=work/'jobs'/name;root.mkdir(parents=True);rp=root/'reference.json';ref.update(sheet=name+'.png',equipment=gear,preview_prefix=name,preview_caption=name.upper()+' | native final-frame sword / back shield',root_anchor_frame=0);rp.write_text(json.dumps(ref,indent=2));j.update(sheet=name,code=code,action=action,model=unarmed[action],motion=name,root=str(root),reference=str(rp));plan['jobs'].append(j);plan['motions'].append({'name':name});inv=copy.deepcopy(base['inventory'][donor['code']][donor['sheet']]);plan['inventory'][code][name]=inv;plan['starting_game_hashes'][name]=manifest['sheets'][name]['sha256']
if manifest.get('town_hilt_only_revision'):plan['town_hilt_only_revision']=manifest['town_hilt_only_revision']
if manifest.get('town_bare_sword_revision'):plan['town_bare_sword_revision']=manifest['town_bare_sword_revision'];plan.pop('town_hilt_only_revision',None)
(work/'plan.json').write_text(json.dumps(plan,indent=2));print('Prepared eight town revisions from native sheathe final frame',end)
