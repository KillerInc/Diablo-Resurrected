"""Edit the private male Paladin candidate; no game assets belong in Git.

Blender CLI: --python paladin_candidate.py -- INPUT.glb OUTPUT_DIRECTORY
The source export is never overwritten. Component selectors are specific to
PalM_base16_TRS / PalM_base01_LEG in the user's skirt-free Candidate 1.
"""
import bpy,bmesh,sys,json,math,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

src=Path(sys.argv[sys.argv.index('--')+1]).resolve()
out=Path(sys.argv[sys.argv.index('--')+2]).resolve();out.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(src))
meshes=[o for o in list(bpy.data.objects) if o.type=='MESH']
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
def material_name(o):return o.data.materials[0].name if o.data.materials else ''
def find(token):
 found=[o for o in meshes if token in material_name(o)];assert len(found)==1,(token,len(found));return found[0]
torso=find('base16_TRS');skin=find('armor_skin');legs=find('base01_LEG')
for o in meshes:o.name=material_name(o)
def components(o):
 adj=[[] for v in o.data.vertices]
 for e in o.data.edges:
  a,b=e.vertices;adj[a].append(b);adj[b].append(a)
 seen=set();result=[]
 for v in o.data.vertices:
  if v.index in seen:continue
  todo=[v.index];seen.add(v.index);ids=[]
  while todo:
   k=todo.pop();ids.append(k)
   for q in adj[k]:
    if q not in seen:seen.add(q);todo.append(q)
  coords=[o.matrix_world@o.data.vertices[i].co for i in ids]
  result.append((ids,Vector(tuple(min(v[d] for v in coords) for d in range(3))),Vector(tuple(max(v[d] for v in coords) for d in range(3)))))
 return result
assert len(torso.data.vertices)==7738,'Source changed: inspect component selectors again'
assert len(legs.data.vertices)==3233,'Source changed: inspect knife components again'
bone_positions={b.name:rig.matrix_world@b.head_local for b in rig.data.bones}
def opposite(name):
 for a,b in [('.L','.R'),('.R','.L')]:
  if name.endswith(a) and name[:-2]+b in bone_positions:return name[:-2]+b
 if name not in bone_positions:return name
 pos=bone_positions[name].copy();pos.x=-pos.x
 if abs(pos.x)<.001:return name
 best=min(bone_positions,key=lambda n:(bone_positions[n]-pos).length)
 return best if (bone_positions[best]-pos).length<.005 else name
def mirror_vertices(o,ids):
 ids=set(ids);weights={i:[(o.vertex_groups[g.group].name,g.weight) for g in o.data.vertices[i].groups] for i in ids}
 for i in ids:
  v=o.data.vertices[i];p=o.matrix_world@v.co;p.x=-p.x;v.co=o.matrix_world.inverted()@p
 for g in list(o.vertex_groups):g.remove(list(ids))
 for i,ws in weights.items():
  for name,w in ws:
   name=opposite(name);g=o.vertex_groups.get(name) or o.vertex_groups.new(name=name);g.add([i],w,'REPLACE')
 bm=bmesh.new();bm.from_mesh(o.data);bm.verts.ensure_lookup_table()
 fs=[f for f in bm.faces if all(v.index in ids for v in f.verts)]
 bmesh.ops.reverse_faces(bm,faces=fs);bm.to_mesh(o.data);bm.free();o.data.update()
shoulder_ids=[]
for ids,mn,mx in components(torso):
 if ((mx.x<-.10 and mn.x<-.13) or mn.x>.17) and mx.z>1.16:
  shoulder_ids.extend(ids)
mirror_vertices(torso,shoulder_ids)
mirror_vertices(skin,range(len(skin.data.vertices)))
# These islands are the right-hip blade, sheath, hilt and its dedicated loops.
# The waist belt, pockets, trousers, knee straps and boots remain intact.
knife_roots={759,762,785,830,988,1061,1084,1099,1152,1191,1211,1243}
remove=[];found_roots=set()
for ids,mn,mx in components(legs):
 if ids[0] in knife_roots:remove+=ids;found_roots.add(ids[0])
assert found_roots==knife_roots,(knife_roots-found_roots)
bm=bmesh.new();bm.from_mesh(legs.data);bm.verts.ensure_lookup_table()
bmesh.ops.delete(bm,geom=[bm.verts[i] for i in remove],context='VERTS');bm.to_mesh(legs.data);bm.free();legs.data.update()

# A real, weighted ribbon fitted against the cuirass, rather than a flat overlay.
verts=[torso.matrix_world@v.co for v in torso.data.vertices]
bvh=BVHTree.FromPolygons(verts,[tuple(p.vertices) for p in torso.data.polygons],all_triangles=False)
leather=bpy.data.materials.new('D1 chest strap - dark brown leather');leather.diffuse_color=(.105,.045,.018,1);leather.use_nodes=True
bs=leather.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=leather.diffuse_color;bs.inputs['Roughness'].default_value=.72
edge=bpy.data.materials.new('D1 strap edge');edge.diffuse_color=(.23,.12,.055,1);edge.use_nodes=True;edge.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=edge.diffuse_color
metal=bpy.data.materials.new('D1 strap buckle - aged brass');metal.diffuse_color=(.26,.16,.065,1);metal.use_nodes=True
bs=metal.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=metal.diffuse_color;bs.inputs['Metallic'].default_value=.75;bs.inputs['Roughness'].default_value=.48
new=[]
def bind_surface(o):
 # Transfer the closest cuirass vertex's normalized deform weights.
 from mathutils.kdtree import KDTree
 kd=KDTree(len(verts))
 for i,v in enumerate(verts):kd.insert(v,i)
 kd.balance()
 for v in o.data.vertices:
  _,i,_=kd.find(o.matrix_world@v.co);ws=[(torso.vertex_groups[g.group].name,g.weight) for g in torso.data.vertices[i].groups];total=sum(w for _,w in ws)
  for n,w in ws:
   group=o.vertex_groups.get(n) or o.vertex_groups.new(name=n);group.add([v.index],w/total if total else 0,'REPLACE')
 mod=o.modifiers.new('Original Paladin skeleton','ARMATURE');mod.object=rig;o.parent=rig
def surface(x,z,back=False,offset=.008):
 p,n,_,_=bvh.ray_cast(Vector((x,1 if back else -1,z)),Vector((0,-1 if back else 1,0)),2)
 if p is None:raise RuntimeError(f'Strap misses chest at {x},{z},back={back}')
 p.y+=offset if back else -offset;return p
start=Vector((.158,1.53));end=Vector((-.145,1.13));d=(end-start).normalized();side=Vector((-d.y,d.x))
def ribbon(name,width,material,back=False,lateral=0,offset=.008):
 vs=[];faces=[]
 for i in range(49):
  p=start.lerp(end,i/48)+side*lateral
  for sign in [-1,1]:
   q=p+side*width*.5*sign;vs.append(surface(q.x,q.y,back,offset))
 for i in range(48):
  a=2*i;faces.append((a,a+1,a+3,a+2) if not back else (a+2,a+3,a+1,a))
 me=bpy.data.meshes.new(name);me.from_pydata(vs,[],faces);me.update();o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);o.data.materials.append(material)
 for p in me.polygons:p.use_smooth=True
 bind_surface(o);new.append(o);return o
for back in [False,True]:
 label='back' if back else 'front';o=ribbon('D1 diagonal strap '+label,.038,leather,back)
 solid=o.modifiers.new('Leather thickness','SOLIDIFY');solid.thickness=.003;solid.offset=0
 for shift in [-.016,.016]:ribbon('D1 strap stitched edge '+label,.0014,edge,back,shift,.010)
# Buckle as four narrow bars; sample every point to remain close to the chest.
center=start.lerp(end,.35)
for axis,length,delta in [(side,.046,d*.023),(side,.046,-d*.023),(d,.046,side*.023),(d,.046,-side*.023)]:
 vs=[]
 norm=Vector((-axis.y,axis.x))
 for l,w in [(-1,-1),(-1,1),(1,1),(1,-1)]:
  q=center+delta+axis*(length*.5*l)+norm*(.003*w);vs.append(surface(q.x,q.y,False,.015))
 me=bpy.data.meshes.new('Buckle bar');me.from_pydata(vs,[],[(0,1,2,3)]);me.update();o=bpy.data.objects.new('D1 buckle',me);bpy.context.collection.objects.link(o);o.data.materials.append(metal);bind_surface(o);new.append(o)
 solid=o.modifiers.new('Buckle depth','SOLIDIFY');solid.thickness=.003

report={'source':str(src),'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'source_skirt_absent':True,'mirrored_shoulder_vertices':len(shoulder_ids),'removed_blade_vertices':len(remove),'rig_joints':len(rig.data.bones),'original_forearm_mesh_unchanged':True,'new_weighted_parts':len(new),'note':'Static preview; game animations not supplied in input.'}
scene=bpy.context.scene;scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=800;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.world.color=(.11,.11,.11);scene.view_settings.view_transform='AgX'
center3=Vector((0,.1,.96));bpy.ops.object.camera_add();cam=bpy.context.object;cam.data.type='ORTHO';cam.data.ortho_scale=2.05;scene.camera=cam
for pos,power,size in [((2,-3,4),280,4),((-2,-2,2),160,3),((0,3,3),200,3)]:
 bpy.ops.object.light_add(type='AREA',location=pos);l=bpy.context.object;l.data.energy=power;l.data.size=size;l.rotation_euler=(center3-l.location).to_track_quat('-Z','Y').to_euler()
for name,pos in [('front',(0,-4,1.12)),('back',(0,4,1.12)),('side',(4,-.25,1.12))]:
 cam.location=pos;cam.rotation_euler=(center3-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'Paladin-D1-Candidate-1-edited.blend'))
bpy.ops.object.select_all(action='DESELECT')
for o in meshes+new+[rig]:o.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.gltf(filepath=str(out/'Paladin-D1-Candidate-1-edited.glb'),export_format='GLB',use_selection=True,export_animations=False)
(out/'validation.json').write_text(json.dumps(report,indent=2))
