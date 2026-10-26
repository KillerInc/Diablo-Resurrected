"""Blender --python SCRIPT -- CURRENT_TOWN_PLAN.json NEW_PRIVATE_WORK
Bring the town sword 3 cm inward and 2 cm forward; preserve height/rotation.
"""
import bpy,json,copy,sys
from pathlib import Path
from mathutils import Matrix,Vector
source,work=map(Path,sys.argv[sys.argv.index('--')+1:]);old=json.loads(source.read_text());work=work.resolve();work.mkdir(exist_ok=False);manifest=json.loads((Path(old['previous'])/'paladin-vanilla-dimensions/install-manifest.json').read_text());j=next(j for j in old['jobs'] if j['sheet']=='wldst');ref=json.loads(Path(j['reference']).read_text());mount=Matrix(next(e['local_transform'] for e in ref['equipment'] if e['town_role']=='town_sword'));bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=j['model']);rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');bpy.context.scene.frame_set(0);bpy.context.view_layer.update();pelvis=rig.matrix_world@rig.pose.bones['pelvis'].matrix;mount.translation+=pelvis.to_3x3().inverted()@Vector((-.03,-.02,0));mount=[list(r) for r in mount];recipe=copy.deepcopy(manifest['town_sword_roll_revision']);recipe.update(mount=mount,hip_fit_world_delta=[-.03,-.02,0]);plan=copy.deepcopy(old);plan.update(work=str(work),starting_custom_manifest=manifest,town_sword_roll_revision=recipe,jobs=[],motions=[],starting_game_hashes={})
for j in old['jobs']:
 j=copy.deepcopy(j);name=j['sheet'];plan['starting_game_hashes'][name]=manifest['sheets'][name]['sha256']
 if j['code'] in ['wls','wld']:
  ref=json.loads(Path(j['reference']).read_text())
  for e in ref['equipment']:
   if e['town_role']=='town_sword':e.update(local_transform=mount,town_sword_revision='close-hip-preserved-height-v5')
  root=work/'jobs'/name;root.mkdir(parents=True);rp=root/'reference.json';ref['preview_caption']=name.upper()+' | closer hip fit / unchanged height and angle';rp.write_text(json.dumps(ref,indent=2));j.update(root=str(root),reference=str(rp))
 plan['jobs'].append(j);plan['motions'].append({'name':j['motion']})
(work/'plan.json').write_text(json.dumps(plan,indent=2));print('Prepared closer hip fit; shield and sword height/rotation preserved')
