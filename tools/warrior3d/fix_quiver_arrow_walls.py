"""Blender --python SCRIPT -- PREVIOUS_PLAN WORK_WITH_ARROW_FIT
Remove hidden arrowheads, seat shafts and verify rigid quiver wall clearance.
"""
import bpy,json,copy,hashlib,shutil,sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
old,w=map(Path,sys.argv[sys.argv.index('--')+1:]);w=w.resolve();p=json.loads(old.read_text());previous=Path(p['work']);fit=json.loads((w/'arrow-fit.json').read_text());r=json.loads(Path(p['jobs'][0]['reference']).read_text());q=next(e for e in r['equipment'] if e.get('town_role')=='back_quiver');source=Path(q['path']);bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(source));obj=next(o for o in bpy.data.objects if o.type=='MESH');m=obj.data;m.calc_loop_triangles();names=json.loads((previous/'triangle-parts.json').read_text());assert not m.color_attributes;uvs=list(m.uv_layers);positions=[];triangles=[];normals=[];texcoords=[[] for u in uvs];labels=[];materials=[];original_wall=[]
def key(vs):return tuple(sorted(tuple(round(float(x),5) for x in v) for v in vs))
for i,t in enumerate(m.loop_triangles):
 name=names[i];arrow=name.startswith('Quiver arrow');number=name.split()[2] if arrow else None
 poly=[(m.vertices[k].co.copy(),m.corner_normals[l].vector.copy(),[u.data[l].uv.copy() for u in uvs]) for k,l in zip(t.vertices,t.loops)]
 if arrow:
  out=[];z=fit['cut_z']
  for a,b in zip(poly,poly[1:]+poly[:1]):
   if a[0].z>=z:out.append(a)
   if (a[0].z>=z)!=(b[0].z>=z):
    f=(z-a[0].z)/(b[0].z-a[0].z);out.append((a[0].lerp(b[0],f),a[1].lerp(b[1],f).normalized(),[x.lerp(y,f) for x,y in zip(a[2],b[2])]))
  shift=Vector((*fit['translations_mesh_local'][number],0));poly=[(v+shift,n,uv) for v,n,uv in out];name='Quiver arrow '+number
 else:original_wall.append(key([a[0] for a in poly]))
 for k in range(1,len(poly)-1):
  face=[poly[0],poly[k],poly[k+1]];base=len(positions);triangles.append((base,base+1,base+2));labels.append(name);materials.append(t.material_index)
  for v,n,uv in face:
   positions.append(v);normals.append(n)
   for j,coord in enumerate(uv):texcoords[j].append(coord)
new=bpy.data.meshes.new('Quiver wall-safe arrows');new.from_pydata(positions,[],triangles);new.update()
for mat in m.materials:new.materials.append(mat)
for i,face in enumerate(new.polygons):face.material_index=materials[i];face.use_smooth=True
for i,u in enumerate(uvs):
 layer=new.uv_layers.new(name=u.name)
 for j,uv in enumerate(texcoords[i]):layer.data[j].uv=uv
new.normals_split_custom_set(normals);obj.data=new;obj.name='Quiver six seated arrows';lookup={}
for face,name in zip(new.polygons,labels):lookup[key([new.vertices[k].co for k in face.vertices])]=name
bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj;dest=w/'quiver-six-arrows-wall-safe.glb';bpy.ops.export_scene.gltf(filepath=str(dest),export_format='GLB',use_selection=True,export_extras=True)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(dest));mesh=next(o.data for o in bpy.data.objects if o.type=='MESH');mesh.calc_loop_triangles();v=[a.co.copy() for a in mesh.vertices];mapped=[lookup[key([v[k] for k in t.vertices])] for t in mesh.loop_triangles];wall=[tuple(t.vertices) for i,t in enumerate(mesh.loop_triangles) if not mapped[i].startswith('Quiver arrow')];arrows=[tuple(t.vertices) for i,t in enumerate(mesh.loop_triangles) if mapped[i].startswith('Quiver arrow')];hits=BVHTree.FromPolygons(v,arrows,all_triangles=True).overlap(BVHTree.FromPolygons(v,wall,all_triangles=True,epsilon=fit['wall_margin_mesh_local']));assert not hits;assert sorted(original_wall)==sorted(key([v[k] for k in t]) for t in wall)
protected=[tuple(t.vertices) for i,t in enumerate(mesh.loop_triangles) if mapped[i] in {'Object_2.028','Object_2.029','Object_2.088','Object_2.089','Object_2.090'}];inside_tree=BVHTree.FromPolygons(v,protected,all_triangles=True);containment=[]
for number in range(1,7):
 for level in [fit['cut_z']+.005,fit['cut_z']+(.15-fit['cut_z'])/3,fit['cut_z']+2*(.15-fit['cut_z'])/3,.15]:
  pts={}
  for i,t in enumerate(mesh.loop_triangles):
   if mapped[i]!='Quiver arrow '+str(number):continue
   poly=[v[k] for k in t.vertices]
   for a,b in zip(poly,poly[1:]+poly[:1]):
    if (a.z>=level)!=(b.z>=level):c=a.lerp(b,(level-a.z)/(b.z-a.z));pts[tuple(round(x,6) for x in c)]=c
  assert pts;centre=sum(pts.values(),Vector())/len(pts);distances=[inside_tree.ray_cast(centre,Vector((0,sign,0)),.15)[3] for sign in [-1,1]];assert all(d is not None for d in distances);containment.append({'arrow':number,'level':level,'wall_distances':distances})
(w/'shaft-containment.json').write_text(json.dumps(containment,indent=2))
report=dict(fit,arrow_wall_intersections=len(hits),wall_geometry_preserved=True,source=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest().upper(),quiver_sha256=hashlib.sha256(dest.read_bytes()).hexdigest().upper(),arrows=6,exported_triangles=len(mapped),hidden_arrowheads_removed=True,shaft_containment_samples=len(containment),shafts_inside_pouch=True);(w/'quiver-wall-clearance.json').write_text(json.dumps(report,indent=2));(w/'triangle-parts.json').write_text(json.dumps(mapped))
p=copy.deepcopy(p);p.update(work=str(w),quiver_arrow_wall_revision=True,starting_custom_manifest=json.loads((Path(p['previous'])/'paladin-vanilla-dimensions/install-manifest.json').read_text()));p['quiver_fit']['arrow_wall_revision']=report
for j in p['jobs']:
 root=w/'jobs'/j['sheet'];root.mkdir(parents=True);ref=json.loads(Path(j['reference']).read_text());spec=next(e for e in ref['equipment'] if e.get('town_role')=='back_quiver');spec['previous_asset_path']=spec['path'];spec['path']=str(dest);rp=root/'reference.json';rp.write_text(json.dumps(ref,indent=2));j.update(root=str(root),reference=str(rp))
for name in ['quiver-fit-search.json','quiver-contour-search.json','translation-only-plan.json','endpoint-fit.json']:shutil.copy2(previous/name,w/name)
shutil.copytree(previous/'translation-only-references',w/'translation-only-references');(w/'plan.json').write_text(json.dumps(p,indent=2));print('VERIFIED',report,flush=True)
