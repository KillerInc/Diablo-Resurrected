"""Render the compatible Paladin walk into vanilla's eight-direction/eight-row layout.

Blender --python SCRIPT -- ANIMATED.glb REFERENCE.json OUTPUT_DIRECTORY
Final fitting uses rendered alpha and body-only CL2 measurements.
Private artwork is not embedded.
"""
import bpy,sys,json,math
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
src,reference,out=map(Path,sys.argv[sys.argv.index('--')+1:]);out=out.resolve();out.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.context.scene.render.fps=30
bpy.ops.import_scene.gltf(filepath=str(src.resolve()))
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');rig.rotation_mode='XYZ';parts=[o for o in bpy.data.objects if o.type=='MESH']
assert rig.animation_data and rig.animation_data.action
scene=bpy.context.scene;scene.render.engine='BLENDER_EEVEE';scene.render.fps=30;scene.render.resolution_x=768;scene.render.resolution_y=768;scene.render.resolution_percentage=100;scene.render.film_transparent=True
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.world.color=(.13,.13,.13);scene.view_settings.view_transform='AgX'
ref=json.loads(reference.read_text());cell=ref.get('cell',768)
if ref.get('body_render_samples'):scene.eevee.taa_render_samples=ref['body_render_samples']
equipment=[]
if ref.get('equipment'):
 sys.path.insert(0,str(Path(__file__).resolve().parent))
 from paladin_equipment import attach_equipment
 equipment=attach_equipment(rig,ref['equipment'])
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
scene.frame_set(ref.get('root_anchor_frame',1));rig.rotation_euler=(0,0,0);rig.location=(0,0,0);bpy.context.view_layer.update();initial=(rig.matrix_world@rig.pose.bones['pelvis'].head).copy()
redirect=None
if ref.get('redirect_fall'):
 sys.path.insert(0,str(Path(__file__).resolve().parent))
 from redirect_paladin_fall import RedirectFall
 redirect=RedirectFall(rig,ref['redirect_fall']['first_frame'])
fire=None
if ref.get('fire_effect'):
 sys.path.insert(0,str(Path(__file__).resolve().parent))
 from paladin_fire_effect import FireEffect
 if ref['fire_effect'].get('style')=='lightning':
  from paladin_lightning_effect import LightningEffect
  fire=LightningEffect(scene,rig,out,ref['fire_effect'])
 elif ref['fire_effect'].get('style')=='magic':
  from paladin_magic_effect import MagicEffect
  fire=MagicEffect(scene,rig,out,ref['fire_effect'])
 else:fire=FireEffect(scene,rig,out,ref['fire_effect'])
def pose(direction,row):
 rig.location=(0,0,0);rig.rotation_euler.z=-direction*math.pi/4;scene.frame_set(times[row]);bpy.context.view_layer.update()
 if redirect:redirect.apply(times[row],ref['redirect_fall']['angles'][direction],ref['redirect_fall'].get('modes',['pelvis']*8)[direction])
 p=rig.matrix_world@rig.pose.bones['pelvis'].head
 origin=rig.matrix_world.to_3x3()@initial
 if not ref.get('preserve_horizontal_root_motion',False):
  rig.location.x=origin.x-p.x;rig.location.y=origin.y-p.y
 if ref.get('pose_offsets'):
  rig.location+=rig.matrix_world.to_3x3()@Vector(ref['pose_offsets'][row])
 if ref.get('direction_pose_offsets'):
  rig.location+=rig.matrix_world.to_3x3()@Vector(ref['direction_pose_offsets'][direction][row])
 bpy.context.view_layer.update()
 if fire:fire.update(direction,row,rows)
registrations=[[0.0,0.0] for _ in range(8)]
# Final scale and fixed per-direction registration use rendered alpha bounds
# in assemble_paladin_town_walk.py, excluding invisible material geometry.
for d in ref.get('render_directions',range(8)):
 camera.data.shift_x,camera.data.shift_y=registrations[d]
 for r in ref.get('render_rows',range(rows)):
  pose(d,r)
  if redirect:before={n:rig.pose.bones[n].matrix.copy() for n in ['pelvis','head','ankle.L','ankle.R']}
  scene.render.filepath=str(out/f'body-{d}-{r}.png');bpy.ops.render.render(write_still=True)
  if redirect:
   assert max(abs(before[n][i][j]-rig.pose.bones[n].matrix[i][j]) for n in before for i in range(4) for j in range(4))<1e-5,('Render replaced steered pose',d,r)
pose(0,0);camera.data.shift_x,camera.data.shift_y=registrations[0]
if redirect:
 rig.animation_data.action=redirect.action;scene.frame_set(times[0]);bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(out/'Paladin-town-walk-render.blend'))
ground=world_to_camera_view(scene,camera,Vector((0,0,0)))
metadata={'sheet':ref.get('sheet','wlnwl.png'),'source_frames':times,'output_rows':rows,'render_directions':ref.get('render_directions',list(range(8))),'direction_order':ref['columns'],'camera_elevation':30,'camera_ortho_scale':camera.data.ortho_scale,'ground_origin_pixel':[ground.x*cell,(1-ground.y)*cell],'direction_registration':registrations,'horizontal_root_motion_removed':not ref.get('preserve_horizontal_root_motion',False),'pose_offsets':ref.get('pose_offsets',[]),'direction_pose_offsets':ref.get('direction_pose_offsets',[]),'redirect_fall':ref.get('redirect_fall'),'shadow_overscan':ref.get('shadow_overscan',0),'fire_effect':ref.get('fire_effect'),'sun_position':sun_position,'shadow_distance_gain':ref.get('shadow_distance_gain',1),'ground_shadow':'composited separately from original sheet'}
for key in ['canvas_logical','canvas_anchor','preview_prefix','preview_anchor','preview_contact_row','preview_caption','pose_image_offsets','render_rows','direction_image_offsets','shadow_material_tokens','shadow_anatomy_count','shadow_render_samples']:
 if key in ref:metadata[key]=ref[key]
if equipment:metadata.update(equipment=ref['equipment'],equipment_mesh_count=len(equipment))
if 'root_anchor_frame' in ref:metadata['root_anchor_frame']=ref['root_anchor_frame']
(out/'render.json').write_text(json.dumps(metadata,indent=2))
