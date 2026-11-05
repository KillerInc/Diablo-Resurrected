"""Blender-only material pass on a private medium Warrior scene; writes a new copy."""
import argparse,sys,json,math,hashlib
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('scene',type=Path);p.add_argument('components',type=Path);p.add_argument('output',type=Path)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
source=a.scene.resolve();components=a.components.resolve();out=a.output.resolve()
assert not out.exists(),'Use a new output directory';out.mkdir(parents=True)
bpy.ops.wm.open_mainfile(filepath=str(source))
body_ids=set(next(x['components'][0]['ids'] for x in json.loads(components.read_text()) if x['name']=='Mesh_9'))
assert len(bpy.data.objects['Mesh_9'].data.vertices)==7443,'Re-audit a changed source mesh'
def geometry_hash():
 h=hashlib.sha256()
 for o in sorted((o for o in bpy.context.scene.objects if o.type=='MESH'),key=lambda o:o.name):
  for v in o.data.vertices:
   h.update(np.asarray(v.co,dtype=np.float32).tobytes())
   h.update(str([(g.group,g.weight) for g in v.groups]).encode())
  for layer in o.data.uv_layers:
   for uv in layer.data:h.update(np.asarray(uv.uv,dtype=np.float32).tobytes())
 return h.hexdigest()
before=geometry_hash();s=bpy.context.scene;s.render.engine='BLENDER_EEVEE';s.eevee.taa_render_samples=32
s.render.resolution_x=700;s.render.resolution_y=760;s.render.resolution_percentage=100
s.view_settings.view_transform='Standard';cam=s.camera

def render(name,angle,close=False):
 center=Vector((0,.13,1.48 if close else .94));cam.data.ortho_scale=.85 if close else 2.12
 theta=math.radians(angle);cam.location=center+Vector((math.sin(theta)*3,math.cos(theta)*3,.35 if close else .12));cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
 s.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
render('front-before',180)
render('detail-before',135,True)
receipts=[]
def recolor_material(original,name,kind):
 m=original.copy();m.name=name
 bsdf=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
 socket=bsdf.inputs['Base Color'];node=socket.links[0].from_node
 assert node.type=='TEX_IMAGE' and node.image,'Expected a direct base-color texture'
 image=node.image.copy();image.name=name+' base color'
 pixels=np.empty(len(image.pixels),dtype=np.float32);image.pixels.foreach_get(pixels);rgba=pixels.reshape((-1,4));rgb=rgba[:,:3]
 high=rgb.max(axis=1);low=rgb.min(axis=1);sat=(high-low)/np.maximum(high,1e-6)
 # Protect warm leather, rusty mail details and gold trim. Work only in RGB;
 # preserve every original alpha value and all UVs, geometry and skin weights.
 neutral=np.clip((.48-sat)/.22,0,1)
 warm=(rgb[:,0]>rgb[:,2]*1.14)&(rgb[:,0]>rgb[:,1]*1.035)&(sat>.22)
 mask=neutral*(~warm)
 if kind=='blue':
  mask*=np.clip((high-.015)/.05,0,1)
  target=rgb*np.array((.53,.68,1.04),dtype=np.float32)
 else:target=rgb*np.array((.50,.52,.55),dtype=np.float32)
 rgb[:]=np.clip(rgb*(1-mask[:,None])+target*mask[:,None],0,1)
 image.pixels.foreach_set(pixels);image.update();image.filepath_raw=str(out/(name+'.png'));image.file_format='PNG';image.save();image.pack();node.image=image
 receipts.append({'material':name,'pass':kind,'affected_texels':int((mask>.01).sum())})
 return m
for object_name in ('Mesh_9','Mesh_15'):
 o=bpy.data.objects[object_name];m=recolor_material(o.data.materials[0],object_name+' muted blue mail','blue');slot=len(o.data.materials);o.data.materials.append(m)
 for face in o.data.polygons:
  points=[o.matrix_world@o.data.vertices[i].co for i in face.vertices];center=sum(points,Vector())/len(points)
  selected=(all(i in body_ids for i in face.vertices) and 1.30<center.z<1.65 and abs(center.x)<.23) if object_name=='Mesh_9' else (.50<center.z<.93)
  if selected:face.material_index=slot
helm=bpy.data.objects['Mesh_6'];helm.data.materials[0]=recolor_material(helm.data.materials[0],'Helmet dark gray metal','gray')
assert geometry_hash()==before,'Material changes must not change geometry/UVs/weights'
(out/'material-pass.json').write_text(json.dumps({'passes':receipts,'geometry_uv_weights_sha256':before,'geometry_unchanged':True,'source_scene_preserved':True},indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(out/'D1 Warrior Medium - blue gray.blend'))
bpy.ops.object.select_all(action='DESELECT')
for o in bpy.context.scene.objects:
 if o.type in ('MESH','ARMATURE') and not o.hide_render and not o.hide_get():o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(out/'D1 Warrior Medium - blue gray.glb'),export_format='GLB',use_selection=True,export_animations=False)
render('front-after',180);render('detail-after',135,True);render('back-after',0)
print('PASS: blue mail and dark gray helmet; original geometry, UVs, skin weights and scene preserved')
