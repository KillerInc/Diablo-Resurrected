"""Project the animated body onto the ground using the sprite camera.

Blender --python SCRIPT -- RENDER_SCENE.blend RENDER.json OUTPUT_DIRECTORY
Only opaque anatomical/armor geometry casts this ground silhouette: alpha hair
cards and eye/face overlay planes are excluded. Body renders remain untouched.
"""
import bpy,sys,json,math
import numpy as np
from pathlib import Path
from mathutils import Vector
scene_file,metadata,out=map(Path,sys.argv[sys.argv.index('--')+1:]);out=out.resolve();out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(scene_file.resolve()))
scene=bpy.context.scene;rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');rig.rotation_mode='XYZ'
parts=[]
for o in list(bpy.data.objects):
 if o.type!='MESH':continue
 name=o.data.materials[0].name if o.data.materials else ''
 if any(t in name for t in ['base16_TRS','armor_skin','P00_HED','base01_GLV','base01_LEG','base05_BTS']):parts.append(o)
 o.hide_render=True
assert len(parts)==6,len(parts)
info=json.loads(metadata.read_text());times=info['source_frames']
overscan=info.get('shadow_overscan',0)
if overscan:
 old_size=scene.render.resolution_x;scene.render.resolution_x+=overscan;scene.render.resolution_y+=overscan;scene.camera.data.ortho_scale*=scene.render.resolution_x/old_size
redirect=None
if info.get('redirect_fall'):
 sys.path.insert(0,str(Path(__file__).resolve().parent))
 from redirect_paladin_fall import RedirectFall
 redirect=RedirectFall(rig,info['redirect_fall']['first_frame'])
sun=info.get('sun_position',[3,-4,6]);assert sun[2]>0
rig.location=(0,0,0);rig.rotation_euler=(0,0,0);scene.frame_set(1);bpy.context.view_layer.update();initial=(rig.matrix_world@rig.pose.bones['pelvis'].head).copy()
material=bpy.data.materials.new('Ground shadow silhouette');material.use_nodes=True;nodes=material.node_tree.nodes;nodes.clear();output=nodes.new('ShaderNodeOutputMaterial');emit=nodes.new('ShaderNodeEmission');emit.inputs['Color'].default_value=(0,0,0,1);material.node_tree.links.new(emit.outputs[0],output.inputs['Surface'])
mesh=bpy.data.meshes.new('Projected character');shadow=bpy.data.objects.new('Projected character',mesh);bpy.context.collection.objects.link(shadow);shadow.data.materials.append(material)
for d in info.get('render_directions',range(8)):
 for row,time in enumerate(times):
  rig.location=(0,0,0);rig.rotation_euler.z=-d*math.pi/4;scene.frame_set(int(time));bpy.context.view_layer.update();p=rig.matrix_world@rig.pose.bones['pelvis'].head;origin=rig.matrix_world.to_3x3()@initial
  if redirect:
   redirect.apply(int(time),info['redirect_fall']['angles'][d],info['redirect_fall'].get('modes',['pelvis']*8)[d]);p=rig.matrix_world@rig.pose.bones['pelvis'].head
  if info.get('horizontal_root_motion_removed',True):
   rig.location.x=origin.x-p.x;rig.location.y=origin.y-p.y
  if info.get('pose_offsets'):
   rig.location+=rig.matrix_world.to_3x3()@Vector(info['pose_offsets'][row])
  if info.get('direction_pose_offsets'):
   rig.location+=rig.matrix_world.to_3x3()@Vector(info['direction_pose_offsets'][d][row])
  bpy.context.view_layer.update()
  anchor=rig.matrix_world@rig.pose.bones['foot.L'].head
  gain=info.get('shadow_distance_gain',1)
  deps=bpy.context.evaluated_depsgraph_get();vertices=[];faces=[]
  for o in parts:
   ev=o.evaluated_get(deps);me=ev.to_mesh();offset=len(vertices);transform=ev.matrix_world
   for v in me.vertices:
    p=transform@v.co;h=max(0,p.z);x=p.x-sun[0]/sun[2]*h;y=p.y-sun[1]/sun[2]*h
    vertices.append((anchor.x+(x-anchor.x)*gain,anchor.y+(y-anchor.y)*gain,.002))
   faces.extend(tuple(offset+i for i in poly.vertices) for poly in me.polygons);ev.to_mesh_clear()
  mesh.clear_geometry();mesh.from_pydata(vertices,[],faces);mesh.update()
  scene.render.filepath=str(out/f'shadow-{d}-{row}.png');bpy.ops.render.render(write_still=True)
(out/'shadow.json').write_text(json.dumps({'method':'opaque body projected onto z=0','sun_position':sun,'cast_direction':[-sun[0]/sun[2],-sun[1]/sun[2],-1],'distance_gain_about_support_foot':info.get('shadow_distance_gain',1),'frames':len(times),'directions':len(info.get('render_directions',range(8))),'render_directions':list(info.get('render_directions',range(8))),'same_camera_as_body':True},indent=2))
