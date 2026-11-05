"""Blender --python SCRIPT -- CURRENT_TOWN_PLAN.json NEW_PRIVATE_WORK
Roll the sheathed sword broad-face inward and connect its hanger to the belt.
"""
import bpy,json,copy,sys
from pathlib import Path
from mathutils import Matrix,Vector
source,work=map(Path,sys.argv[sys.argv.index('--')+1:]);old=json.loads(source.read_text());work=work.resolve();work.mkdir(exist_ok=False);plan=copy.deepcopy(old);manifest=json.loads((Path(old['previous'])/'paladin-vanilla-dimensions/install-manifest.json').read_text());plan.update(work=str(work),starting_custom_manifest=manifest,jobs=[],motions=[],starting_game_hashes={})
j=next(j for j in old['jobs'] if j['sheet']=='wldst');ref=json.loads(Path(j['reference']).read_text());item=next(e for e in ref['equipment'] if e['town_role']=='sheathed_sword');bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=j['model']);rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');bpy.context.scene.frame_set(0);bpy.context.view_layer.update();pelvis=rig.matrix_world@rig.pose.bones['pelvis'].matrix;world=pelvis@Matrix(item['local_transform']);shaft=world.to_3x3().col[1].normalized();normal=Vector((1,0,0));normal=(normal-shaft*normal.dot(shaft)).normalized();cross=shaft.cross(normal).normalized();rotation=Matrix((cross,shaft,normal)).transposed()*.75;position=world.translation+Vector((0,0,-.03));world=rotation.to_4x4();world.translation=position;mount=pelvis.inverted()@world
if manifest.get('town_sword_roll_revision'):
 mount=Matrix(manifest['town_sword_roll_revision']['mount']);world=pelvis@mount
plan['town_sword_roll_revision']={'broad_face_normal':'outward from left thigh, perpendicular to native shaft','shaft_angle_preserved':True,'belt_height_adjustment':-.03,'mount':[list(r) for r in mount],'hanger_point_world':list(world@Vector((0,.015,-.09)))}
for j in old['jobs']:
 j=copy.deepcopy(j);name=j['sheet'];plan['starting_game_hashes'][name]=manifest['sheets'][name]['sha256']
 if j['code'] in ['wls','wld']:
  ref=json.loads(Path(j['reference']).read_text())
  for e in ref['equipment']:
   if e['town_role'] in ['sheathed_sword','sword_sheath']:e.update(local_transform=[list(r) for r in mount],town_sword_revision='broad-face-thigh-belt-hanger-v1')
  root=work/'jobs'/name;root.mkdir(parents=True);rp=root/'reference.json';ref['preview_caption']=name.upper()+' | broad face toward thigh / belt hanger';rp.write_text(json.dumps(ref,indent=2));j.update(root=str(root),reference=str(rp))
 plan['jobs'].append(j);plan['motions'].append({'name':j['motion']})
(work/'plan.json').write_text(json.dumps(plan,indent=2));print('Prepared four sword/sheath updates; four shield-only/mace-sheet renders reused')
