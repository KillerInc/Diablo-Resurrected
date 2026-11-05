"""Bake private bow/string/arrow morph animation, leaving source artwork intact.
Rigid and morph-only equipment needs no changes to the existing PNG renderer.
"""
import bpy,bmesh,math,json
from pathlib import Path
from mathutils import Matrix,Vector
from paladin_equipment import attach_equipment

def material(name,color,metal=0):
 m=bpy.data.materials.new(name);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=.7;return m
def cylinder(a,b,r=.002,sides=6):
 axis=(b-a).normalized();u=axis.cross(Vector((0,0,1)))
 if u.length<.001:u=axis.cross(Vector((0,1,0)))
 u.normalize();v=axis.cross(u);verts=[p+r*(math.cos(k*2*math.pi/sides)*u+math.sin(k*2*math.pi/sides)*v) for p in [a,b] for k in range(sides)];faces=[tuple(range(sides-1,-1,-1)),tuple(range(sides,2*sides))]+[(i,(i+1)%sides,(i+1)%sides+sides,i+sides) for i in range(sides)];return verts,faces
def string_geometry(top,nock,bottom):
 a,fa=cylinder(top,nock);b,fb=cylinder(nock,bottom);return a+b,fa+[tuple(i+len(a) for i in f) for f in fb]
def obj(name,verts,faces,mats):
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update();o=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(o)
 for m in mats:o.data.materials.append(m)
 return o
def remove_old_string(o):
 mesh=o.data;parents=list(range(len(mesh.vertices)))
 def root(i):
  while parents[i]!=i:parents[i]=parents[parents[i]];i=parents[i]
  return i
 for e in mesh.edges:a,b=map(root,e.vertices);parents[a]=b
 groups={}
 for v in mesh.vertices:groups.setdefault(root(v.index),[]).append(v)
 remove=set()
 for vs in groups.values():
  span=[max(v.co[k] for v in vs)-min(v.co[k] for v in vs) for k in range(3)]
  if span[1]>.5 and span[0]<.02 and span[2]<.02:remove.update(v.index for v in vs)
 assert len(remove)==126,('Unexpected selected bow string topology',len(remove));bm=bmesh.new();bm.from_mesh(mesh);bm.verts.ensure_lookup_table();bmesh.ops.delete(bm,geom=[bm.verts[i] for i in remove],context='VERTS');bm.to_mesh(mesh);bm.free();return len(remove)
def keys(o,positions):
 o.shape_key_add(name='Basis')
 for row,coords in enumerate(positions):
  k=o.shape_key_add(name='Pose%02d'%row)
  for v,co in zip(k.data,coords):v.co=co
  for frame in range(len(positions)):k.value=1 if row==frame else 0;k.keyframe_insert('value',frame=frame)
def bake(source,dest,model=None,rows=0,release_row=10,mode='shot',hold_tilt_degrees=0,hold_cant_degrees=0,hold_yaw_degrees=0):
 source,dest=map(Path,[source,dest]);bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;scene.render.fps=30;rig=None
 if model:
  bpy.ops.import_scene.gltf(filepath=str(Path(model).resolve()));rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');gear={'path':str(source.resolve()),'bone':'hand.L','orientation_socket':'weapon.L','grip':[0,0,0],'hand_point':[0,.05,0],'scale':1};wood=attach_equipment(rig,[gear])[0]
 else:
  bpy.ops.import_scene.gltf(filepath=str(source.resolve()));wood=next(o for o in bpy.data.objects if o.type=='MESH')
 assert all(abs(wood.data.vertices[0].co[k])<5 for k in range(3));removed=remove_old_string(wood);base=[v.co.copy() for v in wood.data.vertices];top=Vector((.108,.705,0));bottom=Vector((.108,-.677,0));rest=Vector((.108,.0216,0));verts,faces=string_geometry(top,rest,bottom);string=obj('Bow string',verts,faces,[material('Bow string hemp',(.32,.24,.13))]);objects=[wood,string]
 if model and mode in ['carry','town']:
  wp=[];sp=[]
  for row in range(rows):
   scene.frame_set(row);bpy.context.view_layer.update();w=wood.matrix_world.copy();draw=w.to_3x3().col[0];draw.z=0;draw.normalize();up=Vector((0,0,1))
   if mode=='town':
    tilt=math.radians(hold_tilt_degrees);cant=math.radians(hold_cant_degrees);draw=Vector((math.sin(cant),math.sin(tilt)*math.cos(cant),math.cos(tilt)*math.cos(cant)));up=Vector((0,math.cos(tilt),-math.sin(tilt)));rotation=Matrix.Rotation(math.radians(hold_yaw_degrees),3,'Z');draw=rotation@draw;up=rotation@up
   normal=draw.cross(up);posed=Matrix((draw,up,normal)).transposed().to_4x4();posed.translation=w.translation;local=w.inverted()@posed;wp.append([local@v for v in base]);sp.append(string_geometry(local@top,local@rest,local@bottom)[0])
  keys(wood,wp);keys(string,sp);scene.frame_start=0;scene.frame_end=rows-1
 elif model:
  av,af=cylinder(Vector((0,0,0)),Vector((.73,0,0)),.003,6);arrow=obj('Nocked arrow',av+[(.8,0,0),(.72,.018,0),(.72,-.018,0),(.08,0,0),(.2,0,.025),(.2,0,-.025)],af+[(len(av),len(av)+1,len(av)+2),(len(av)+3,len(av)+4,len(av)+5)],[material('Arrow wood',(.24,.12,.045)),material('Arrow tip',(.12,.13,.14),.6),material('Arrow feather',(.2,.16,.12))]);arrow.data.polygons[-2].material_index=1;arrow.data.polygons[-1].material_index=2;objects.append(arrow);raw_arrow=[v.co.copy() for v in arrow.data.vertices];wp=[];sp=[];ap=[];align=[0,.15,.3,.5,.65,.8,1,1,1,1,1,1,.75,.4,.15,0];tension=[0,0,0,0,.1,.2,.4,.6,.8,.95,1,.2,.05,0,0,0]
  for row in range(rows):
   scene.frame_set(row);bpy.context.view_layer.update();w=wood.matrix_world.copy();inv=w.inverted();grip=rig.matrix_world@rig.pose.bones['hand.L'].matrix@Vector((0,.05,0));pull=rig.matrix_world@rig.pose.bones['hand.R'].matrix@Vector((.0425,.0825,-.002));up=w.to_3x3().col[1].normalized();draw=Vector((0,1,0));up=(up-draw*up.dot(draw)).normalized();normal=draw.cross(up).normalized();desired=Matrix((draw,up,normal)).transposed().to_4x4();desired.translation=grip;carry_draw=w.to_3x3().col[0];carry_draw.z=0;carry_draw.normalize();carry=Matrix((carry_draw,Vector((0,0,1)),carry_draw.cross(Vector((0,0,1))))).transposed();rotation=carry.to_quaternion().slerp(desired.to_quaternion(),align[row]);posed=rotation.to_matrix().to_4x4();posed.translation=grip;local=inv@posed;flex=.045*tension[row];coords=[local@(v+Vector((flex*min(1,abs(v.y)/.7)**2,0,0))) for v in base];wp.append(coords);tt=local@(top+Vector((flex,0,0)));bb=local@(bottom+Vector((flex,0,0)));nn=inv@pull if 5<=row<=release_row else local@rest;sp.append(string_geometry(tt,nn,bb)[0])
   if 4<=row<=release_row:
    direction=(grip-pull).normalized();u=Vector((0,0,1));u=(u-direction*u.dot(direction)).normalized();z=direction.cross(u);a=Matrix((direction,u,z)).transposed().to_4x4();a.translation=pull;ap.append([inv@a@v for v in raw_arrow])
   else:ap.append([Vector((0,0,0)) for v in raw_arrow])
  keys(wood,wp);keys(string,sp);keys(arrow,ap);scene.frame_start=0;scene.frame_end=rows-1
 # Export only rigid/morph meshes in their common asset coordinates, no rig.
 for o in objects:o.parent=None;o.matrix_world=Matrix.Identity(4)
 bpy.ops.object.select_all(action='DESELECT')
 for o in objects:o.select_set(True)
 scene.frame_set(0);dest.parent.mkdir(parents=True,exist_ok=True);bpy.ops.export_scene.gltf(filepath=str(dest.resolve()),export_format='GLB',use_selection=True,export_animations=bool(model),export_animation_mode='SCENE',export_anim_scene_split_object=False,export_frame_range=bool(model),export_force_sampling=True,export_extras=True)
 dest.with_suffix('.fit.json').write_text(json.dumps({'source':str(source.resolve()),'source_string_vertices_replaced':removed,'dynamic_rows':rows,'hold_mode':mode,'hold_tilt_degrees':hold_tilt_degrees,'hold_cant_degrees':hold_cant_degrees,'hold_yaw_degrees':hold_yaw_degrees,'release_row':release_row if model else None,'original_limb_uv_and_materials_preserved':True,'authored_string_and_arrow':True},indent=2));return dest
