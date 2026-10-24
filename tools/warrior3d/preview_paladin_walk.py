"""Blender: import the merged walk GLB and render 40 frames in three views."""
import bpy,sys,json
from pathlib import Path
from mathutils import Vector
src=Path(sys.argv[sys.argv.index('--')+1]).resolve();out=Path(sys.argv[sys.argv.index('--')+2]).resolve();out.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(src))
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
assert rig.animation_data and rig.animation_data.action,'Imported walk action missing'
scene=bpy.context.scene;scene.render.engine='BLENDER_EEVEE';scene.render.fps=30;scene.frame_start=1;scene.frame_end=40
scene.render.resolution_x=400;scene.render.resolution_y=600;scene.render.resolution_percentage=100;scene.world.color=(.09,.09,.09);scene.view_settings.view_transform='AgX'
center=Vector((0,.1,.95));bpy.ops.object.camera_add();cam=bpy.context.object;cam.data.type='ORTHO';cam.data.ortho_scale=2.08;scene.camera=cam
for pos,power,size in [((2,-3,4),280,4),((-2,-2,2),160,3),((0,3,3),200,3)]:
 bpy.ops.object.light_add(type='AREA',location=pos);o=bpy.context.object;o.data.energy=power;o.data.size=size;o.rotation_euler=(center-o.location).to_track_quat('-Z','Y').to_euler()
pelvis=rig.pose.bones['pelvis'];scene.frame_set(1);start=rig.matrix_world@pelvis.head
positions=[]
for frame in range(1,41):
 scene.frame_set(frame);pos=rig.matrix_world@pelvis.head;delta=pos-start;delta.z=0;target=center+delta;positions.append(list(pos))
 for view,offset in [('front',Vector((0,-4,.16))),('side',Vector((4,0,.16))),('back',Vector((0,4,.16)))]:
  cam.location=target+offset;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(out/f'{view}-{frame:02}.png');bpy.ops.render.render(write_still=True)
scene.frame_set(1);cam.location=center+Vector((0,-4,.16));cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.wm.save_as_mainfile(filepath=str(out/'Paladin-D1-walk.blend'))
(out/'preview.json').write_text(json.dumps({'action':rig.animation_data.action.name,'frames':[1,40],'fps':30,'pelvis_positions':positions,'camera_tracks_horizontal_motion':True},indent=2))
