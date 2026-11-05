"""Remove only the detached front tabard components of the audited heavy model."""
import bpy,bmesh,json,hashlib
from collections import Counter

def apply():
 obj=next(o for o in bpy.context.scene.objects if o.type=='MESH' and any(s.material and 'sets57_LEG_mat' in s.material.name for s in o.material_slots));mesh=obj.data;parent=list(range(len(mesh.vertices)))
 def find(i):
  while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
  return i
 for edge in mesh.edges:a,b=map(find,edge.vertices);parent[b]=a
 groups={}
 for vertex in mesh.vertices:groups.setdefault(find(vertex.index),[]).append(vertex.index)
 selected=set();counts=[]
 for ids in groups.values():
  points=[obj.matrix_world@mesh.vertices[i].co for i in ids];lo=[min(p[a] for p in points) for a in range(3)];hi=[max(p[a] for p in points) for a in range(3)]
  if hi[1]<-.02 and max(abs(lo[0]),abs(hi[0]))<.13 and .25<lo[2] and hi[2]<1.08:selected.update(ids);counts.append(len(ids))
 assert len(selected)==633,('Changed heavy cloth topology; inspect before removing',len(selected))
 def face_hash(poly):
  corners=[]
  for vi,li in zip(poly.vertices,poly.loop_indices):
   vertex=mesh.vertices[vi];corners.append((tuple(round(v,7) for v in vertex.co),tuple(sorted((g.group,round(g.weight,7)) for g in vertex.groups)),tuple(tuple(round(v,7) for v in layer.data[li].uv) for layer in mesh.uv_layers)))
  canonical=min(tuple(corners[i:]+corners[:i]) for i in range(len(corners)));return hashlib.sha256(repr((poly.material_index,canonical)).encode()).hexdigest()
 expected=Counter(face_hash(p) for p in mesh.polygons if not any(i in selected for i in p.vertices));before_faces=len(mesh.polygons)
 bm=bmesh.new();bm.from_mesh(mesh);bm.verts.ensure_lookup_table();bmesh.ops.delete(bm,geom=[bm.verts[i] for i in selected],context='VERTS');bm.to_mesh(mesh);bm.free();mesh.update();actual=Counter(face_hash(p) for p in mesh.polygons);assert actual==expected,'Noncloth geometry, UVs or weights changed'
 return {'mesh':obj.name,'removed_vertices':len(selected),'removed_components':len(counts),'component_sizes':sorted(counts,reverse=True),'removed_faces':before_faces-len(mesh.polygons),'waist_armor_and_leg_plates_preserved':True,'remaining_geometry_uv_weights_unchanged':True}
