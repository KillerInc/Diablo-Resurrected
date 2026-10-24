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
bpy.context.scene.render.fps=30
bpy.ops.import_scene.gltf(filepath=str(src.resolve()))
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');rig.rotation_mode='XYZ';parts=[o for o in bpy.data.objects if o.type=='MESH']
assert rig.animation_data and rig.animation_data.action
scene=bpy.context.scene;scene.render.engine='BLENDER_EEVEE';scene.render.fps=30;scene.render.resolution_x=768;scene.render.resolution_y=768;scene.render.resolution_percentage=100;scene.render.film_transparent=True
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.world.color=(.13,.13,.13);scene.view_settings.view_transform='AgX'
ref=json.loads(reference.read_text());cell=ref.get('cell',768)
scene.render.resolution_x=cell;scene.render.resolution_y=cell
target=Vector((0,0,.9));bpy.ops.object.camera_add(location=(0,-6,.9+6*math.tan(math.radians(30))));camera=bpy.context.object;camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=2.75;scene.camera=camera
camera.data.ortho_scale=2.75*cell/768
sun_position=ref.get('sun_position',[3,-4,6])
for pos,power,size in [(sun_position,400,4),((-3,-1,3),140,3),((0,3,4),110,3)]:
 bpy.ops.object.light_add(type='AREA',location=pos);l=bpy.context.object;l.data.energy=power;l.data.size=size;l.rotation_euler=(target-l.location).to_track_quat('-Z','Y').to_euler()
# Direction order is controlled by rotating the character under a fixed camera.
# Remove horizontal root travel only; retain vertical bob and all limb motion.
ref=json.loads(reference.read_text());rows=ref['rows']
first,last=rig.animation_data.action.frame_range
scene.frame_start=int(round(first));scene.frame_end=int(round(last))
source_count=int(round(last-first))+1
times=[int(round(first))+int(i*source_count/rows) for i in range(rows)]
times=ref.get('source_frames',times)
scene.frame_set(1);rig.rotation_euler=(0,0,0);rig.location=(0,0,0);bpy.context.view_layer.update();initial=(rig.matrix_world@rig.pose.bones['pelvis'].head).copy()
def pose(direction,row):
 rig.location=(0,0,0);rig.rotation_euler.z=-direction*math.pi/4;scene.frame_set(times[row]);bpy.context.view_layer.update()
 p=rig.matrix_world@rig.pose.bones['pelvis'].head
 origin=rig.matrix_world.to_3x3()@initial
 if not ref.get('preserve_horizontal_root_motion',False):
  rig.location.x=origin.x-p.x;rig.location.y=origin.y-p.y
 bpy.context.view_layer.update()
registrations=[[0.0,0.0] for _ in range(8)]
# Final scale and fixed per-direction registration use rendered alpha bounds
# in assemble_paladin_town_walk.py, excluding invisible material geometry.
for d in range(8):
 camera.data.shift_x,camera.data.shift_y=registrations[d]
 for r in range(rows):
  pose(d,r);scene.render.filepath=str(out/f'body-{d}-{r}.png');bpy.ops.render.render(write_still=True)
pose(0,0);camera.data.shift_x,camera.data.shift_y=registrations[0]
bpy.ops.wm.save_as_mainfile(filepath=str(out/'Paladin-town-walk-render.blend'))
(out/'render.json').write_text(json.dumps({'source_frames':times,'output_rows':rows,'direction_order':ref['columns'],'camera_elevation':30,'camera_ortho_scale':camera.data.ortho_scale,'direction_registration':registrations,'horizontal_root_motion_removed':not ref.get('preserve_horizontal_root_motion',False),'sun_position':sun_position,'shadow_distance_gain':ref.get('shadow_distance_gain',1),'ground_shadow':'composited separately from original sheet'},indent=2))
