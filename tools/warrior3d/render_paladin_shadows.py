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
rig.location=(0,0,0);rig.rotation_euler=(0,0,0);scene.frame_set(1);bpy.context.view_layer.update();initial=(rig.matrix_world@rig.pose.bones['pelvis'].head).copy()
material=bpy.data.materials.new('Ground shadow silhouette');material.use_nodes=True;nodes=material.node_tree.nodes;nodes.clear();output=nodes.new('ShaderNodeOutputMaterial');emit=nodes.new('ShaderNodeEmission');emit.inputs['Color'].default_value=(0,0,0,1);material.node_tree.links.new(emit.outputs[0],output.inputs['Surface'])
mesh=bpy.data.meshes.new('Projected character');shadow=bpy.data.objects.new('Projected character',mesh);bpy.context.collection.objects.link(shadow);shadow.data.materials.append(material)
for d in range(8):
 for row,time in enumerate(times):
  rig.location=(0,0,0);rig.rotation_euler.z=-d*math.pi/4;scene.frame_set(int(time));bpy.context.view_layer.update();p=rig.matrix_world@rig.pose.bones['pelvis'].head;origin=rig.matrix_world.to_3x3()@initial;rig.location.x=origin.x-p.x;rig.location.y=origin.y-p.y;bpy.context.view_layer.update()
  deps=bpy.context.evaluated_depsgraph_get();vertices=[];faces=[]
  for o in parts:
   ev=o.evaluated_get(deps);me=ev.to_mesh();offset=len(vertices);transform=ev.matrix_world
   for v in me.vertices:
    p=transform@v.co;h=max(0,p.z);vertices.append((p.x-.23*h,p.y-.32*h,.002))
   faces.extend(tuple(offset+i for i in poly.vertices) for poly in me.polygons);ev.to_mesh_clear()
  mesh.clear_geometry();mesh.from_pydata(vertices,[],faces);mesh.update()
  scene.render.filepath=str(out/f'shadow-{d}-{row}.png');bpy.ops.render.render(write_still=True)
(out/'shadow.json').write_text(json.dumps({'method':'opaque body projected onto z=0','light_direction':[.23,.32,1],'frames':len(times),'directions':8,'same_camera_as_body':True},indent=2))
