"""Render the compatible Paladin walk into vanilla's eight-direction/eight-row layout.

Blender --python SCRIPT -- ANIMATED.glb REFERENCE.json OUTPUT_DIRECTORY
Final fitting uses rendered alpha and body-only CL2 measurements.
Private artwork is not embedded.
"""
import bpy,sys,json,math
from pathlib import Path
from mathutils import Vector
src,reference,out=map(Path,sys.argv[sys.argv.index('--')+1:]);out=out.resolve();out.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(src.resolve()))
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');rig.rotation_mode='XYZ';parts=[o for o in bpy.data.objects if o.type=='MESH']
assert rig.animation_data and rig.animation_data.action
scene=bpy.context.scene;scene.render.engine='BLENDER_EEVEE';scene.render.fps=30;scene.render.resolution_x=768;scene.render.resolution_y=768;scene.render.resolution_percentage=100;scene.render.film_transparent=True
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.world.color=(.13,.13,.13);scene.view_settings.view_transform='AgX'
target=Vector((0,0,.9));bpy.ops.object.camera_add(location=(0,-6,.9+6*math.tan(math.radians(30))));camera=bpy.context.object;camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=2.75;scene.camera=camera
for pos,power,size in [((-3,-4,6),400,4),((3,-1,3),140,3),((0,3,4),110,3)]:
 bpy.ops.object.light_add(type='AREA',location=pos);l=bpy.context.object;l.data.energy=power;l.data.size=size;l.rotation_euler=(target-l.location).to_track_quat('-Z','Y').to_euler()
# Direction order is controlled by rotating the character under a fixed camera.
# Remove horizontal root travel only; retain vertical bob and all limb motion.
times=[1,6,11,16,21,26,31,36]
scene.frame_set(1);rig.rotation_euler=(0,0,0);rig.location=(0,0,0);bpy.context.view_layer.update();initial=(rig.matrix_world@rig.pose.bones['pelvis'].head).copy()
def pose(direction,row):
 rig.location=(0,0,0);rig.rotation_euler.z=-direction*math.pi/4;scene.frame_set(times[row]);bpy.context.view_layer.update()
 p=rig.matrix_world@rig.pose.bones['pelvis'].head
 origin=rig.matrix_world.to_3x3()@initial
 rig.location.x=origin.x-p.x;rig.location.y=origin.y-p.y;bpy.context.view_layer.update()
ref=json.loads(reference.read_text());registrations=[[0.0,0.0] for _ in range(8)]
# Final scale and fixed per-direction registration use rendered alpha bounds
# in assemble_paladin_town_walk.py, excluding invisible material geometry.
for d in range(8):
 camera.data.shift_x,camera.data.shift_y=registrations[d]
 for r in range(8):
  pose(d,r);scene.render.filepath=str(out/f'body-{d}-{r}.png');bpy.ops.render.render(write_still=True)
pose(0,0);camera.data.shift_x,camera.data.shift_y=registrations[0]
bpy.ops.wm.save_as_mainfile(filepath=str(out/'Paladin-town-walk-render.blend'))
(out/'render.json').write_text(json.dumps({'source_frames':times,'output_rows':8,'direction_order':ref['columns'],'camera_elevation':30,'camera_ortho_scale':camera.data.ortho_scale,'direction_registration':registrations,'horizontal_root_motion_removed':True,'ground_shadow':'composited separately from original WLNWL'},indent=2))
