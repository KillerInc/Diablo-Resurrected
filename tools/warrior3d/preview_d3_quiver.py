"""Blender --python SCRIPT -- PRIVATE_INSPECTION_DIRECTORY
Preview the parsed D3 quiver mesh as neutral, explicitly untextured geometry.
No original game files are changed. Output media remain private.
"""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Vector
out=Path(sys.argv[sys.argv.index('--')+1]).resolve();data=json.loads((out/'geometry-private.json').read_text());bpy.ops.wm.read_factory_settings(use_empty=True);objects=[]
for record in data:
 mesh=bpy.data.meshes.new(record['name']);mesh.from_pydata(record['positions'],[],record['triangles']);mesh.update();uv=mesh.uv_layers.new(name='UVMap')
 for poly in mesh.polygons:
  for li in poly.loop_indices:
   p=record['uv'][mesh.loops[li].vertex_index];uv.data[li].uv=(p[0],1-p[1])
 obj=bpy.data.objects.new(record['name'],mesh);bpy.context.collection.objects.link(obj);objects.append(obj);mat=bpy.data.materials.new('UNtextured inspection clay');mat.diffuse_color=(.38,.38,.38,1);mat.use_nodes=True;mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.38,.38,.38,1);mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.85;mesh.materials.append(mat)
bpy.ops.object.select_all(action='DESELECT')
for o in objects:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(out/'Quiver-untextured.glb'),export_format='GLB',use_selection=True,export_animations=False)
vertices=[Vector(p) for m in data for p in m['positions']];lo=Vector([min(p[k] for p in vertices) for k in range(3)]);hi=Vector([max(p[k] for p in vertices) for k in range(3)]);center=(lo+hi)/2;span=max(hi-lo);print('Native bounds',list(lo),list(hi),flush=True);scene=bpy.context.scene;scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=640;scene.render.resolution_y=640;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.world=bpy.data.worlds.new('Inspection world');scene.world.color=(.06,.06,.06);scene.view_settings.view_transform='AgX'
for offset,power,size in [((3,-4,6),700,4),((-3,-1,3),400,3),((0,4,3),500,3)]:
 bpy.ops.object.light_add(type='AREA',location=center+Vector(offset)*span/3);light=bpy.context.object;light.data.energy=power;light.data.size=size*span/3;light.rotation_euler=(center-light.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add();cam=bpy.context.object;cam.data.type='ORTHO';cam.data.ortho_scale=span*1.2;scene.camera=cam
for i,angle in enumerate([0,45,90,180]):
 a=math.radians(angle);cam.location=center+Vector((math.sin(a)*span*3,-math.cos(a)*span*3,span*.35));cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(out/('untextured-view-'+str(i)+'.png'));bpy.ops.render.render(write_still=True)

