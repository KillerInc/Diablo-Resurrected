"""Blender --python SCRIPT -- PLAN.json QUIVER.glb
Consolidate the approved private quiver and attach its strap side inward.
Uses the existing town idle chest pose as a shared mounting reference.
"""
import bpy,json,sys
from pathlib import Path
from mathutils import Matrix,Vector
plan_file,asset=map(Path,sys.argv[sys.argv.index('--')+1:]);w=plan_file.resolve().parent;p=json.loads(plan_file.read_text());q=asset.resolve();bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(q));bpy.context.view_layer.update();meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];bpy.ops.object.select_all(action='DESELECT')
for o in meshes:o.select_set(True)
bpy.context.view_layer.objects.active=meshes[0];bpy.ops.object.join();o=bpy.context.object;o.name='Quiver six arrows';bpy.ops.object.transform_apply(location=True,rotation=True,scale=True);dest=w/'quiver-six-arrows.glb';bpy.ops.export_scene.gltf(filepath=str(dest),export_format='GLB',use_selection=True,export_extras=True)
bpy.ops.wm.read_factory_settings(use_empty=True);j=next(j for j in p['jobs'] if j['sheet']=='wlbst');bpy.ops.import_scene.gltf(filepath=j['model']);rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');bpy.context.scene.frame_set(0);bpy.context.view_layer.update();m=Matrix.Translation((0,.225,1.29))@Matrix.Scale(.8,4);local=rig.pose.bones['chest'].matrix.inverted()@rig.matrix_world.inverted()@m
gear={'path':str(dest),'bone':'chest','local_transform':[list(row) for row in local],'town_role':'back_quiver','strap_side_inward':True,'pouch_clearance_outward_metres':.03}
for j in p['jobs']:
 rp=Path(j['reference']);r=json.loads(rp.read_text());r['equipment']=[e for e in r['equipment'] if e.get('town_role')!='back_quiver'];r['equipment'].append(gear);rp.write_text(json.dumps(r,indent=2))
(w/'mount.json').write_text(json.dumps(gear,indent=2))
