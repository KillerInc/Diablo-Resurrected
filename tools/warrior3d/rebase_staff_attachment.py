"""Blender --python SCRIPT -- PREVIOUS_PLAN NEW_FITTED_PLAN
Rebase a right-hand-attached staff onto a fitted wrist while preserving every
previous world-space vertex at each of the 16 stored poses. Does not install.
"""
import bpy,json,sys
from pathlib import Path
from mathutils import Matrix
tools=Path(__file__).resolve().parent;sys.path.insert(0,str(tools));from paladin_equipment import attach_equipment;from bake_bow_equipment import keys
args=sys.argv[sys.argv.index('--')+1:];old_file,new_file=map(Path,args);work=new_file.resolve().parent;oldplan=json.loads(old_file.read_text());ref=json.loads(Path(oldplan['jobs'][0]['reference']).read_text());bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=oldplan['jobs'][0]['model']);rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');staff=attach_equipment(rig,ref['equipment'])[0];positions=[]
for row in range(16):
 scene.frame_set(row);bpy.context.view_layer.update();ev=staff.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh();positions.append([ev.matrix_world@v.co for v in mesh.vertices]);ev.to_mesh_clear()
bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=str(work/'sorcerer.glb'));rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');local=[]
for row in range(16):
 scene.frame_set(row);bpy.context.view_layer.update();inverse=(rig.matrix_world@rig.pose.bones['hand.R'].matrix).inverted();local.append([inverse@p for p in positions[row]])
before=set(bpy.data.objects);bpy.ops.import_scene.gltf(filepath=ref['equipment'][0]['path']);o=next(o for o in set(bpy.data.objects)-before if o.type=='MESH');o.shape_key_clear();o.animation_data_clear();keys(o,local);o.parent=None;o.matrix_world=Matrix.Identity(4);bpy.ops.object.select_all(action='DESELECT');o.select_set(True);scene.frame_start=0;scene.frame_end=15;scene.frame_set(0);dest=work/'staff-fixed-path.glb';bpy.ops.export_scene.gltf(filepath=str(dest),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='SCENE',export_anim_scene_split_object=False,export_frame_range=True,export_force_sampling=True)
plan=json.loads(new_file.read_text());reference=Path(plan['jobs'][0]['reference']);newref=json.loads(reference.read_text());newref['equipment'][0]['path']=str(dest);reference.write_text(json.dumps(newref,indent=2));print('Rebased attachment to preserve the exact original world-space staff vertices',flush=True)
