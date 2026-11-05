import bpy,json,math
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
import argparse,sys
parser=argparse.ArgumentParser(description="Fit detached medium Warrior cords to armor in a private prepared Blender scene.")
parser.add_argument('scene',type=Path);parser.add_argument('components',type=Path);parser.add_argument('output',type=Path)
a=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
source=a.scene.resolve();components=a.components.resolve();out=a.output.resolve()
assert not out.exists(), 'Use a new output directory; preserve the source'
out.mkdir(parents=True)
report=json.loads(components.read_text());comps=next(x['components'] for x in report if x['name']=='Mesh_9')
bpy.ops.wm.open_mainfile(filepath=str(source));o=bpy.data.objects['Mesh_9']
assert len(o.data.vertices)==7443 and len(o.vertex_groups)==633, 'Re-audit changed topology before fitting'
for obj in bpy.context.scene.objects:
 if obj.type=='MESH' and any(m and ('cape_sim' in m.name.lower() or 'skirt_sim' in m.name.lower()) for m in obj.data.materials):
  obj.hide_render=True;obj.hide_set(True)
# Detached upper-back rope, fasteners, and small shoulder attachment trims.
selected=[1,3,6,22,23]
ids={v for c in selected for v in comps[c]['ids']};original={v.index:v.co.copy() for v in o.data.vertices}
world=[o.matrix_world@v.co for v in o.data.vertices]
faces=[tuple(p.vertices) for p in o.data.polygons if not any(v in ids for v in p.vertices)]
target=BVHTree.FromPolygons(world,faces,all_triangles=False)
torso_ids=set(comps[0]['ids'])
torso_faces=[tuple(p.vertices) for p in o.data.polygons if all(v in torso_ids for v in p.vertices) and abs(sum(world[v].x for v in p.vertices)/len(p.vertices))<.2 and sum(world[v].y for v in p.vertices)/len(p.vertices)>.12 and sum(world[v].z for v in p.vertices)/len(p.vertices)>1.3]
torso=BVHTree.FromPolygons(world,torso_faces,all_triangles=False)
all_target=target
metrics=[]
for c in selected:
 target=torso if c in (6,22,23) else all_target
 indices=comps[c]['ids'];points=[world[i] for i in indices];before=[target.find_nearest(p)[3] for p in points]
 if c in (22,23):
  # Keep each round clasp rigid; align its disk plane with the mail beneath it.
  center=sum(points,Vector())/len(points);near,normal,_,distance=target.find_nearest(center)
  a=np.array([list(p-center) for p in points]);vals,axes=np.linalg.eigh(a.T@a)
  axis=Vector(axes[:,0]);axis=axis if axis.dot(normal)>0 else -axis
  rotation=axis.rotation_difference(normal);half=max(abs((p-center).dot(axis)) for p in points)
  for i,p in zip(indices,points):world[i]=near+normal*(half+.0025)+rotation@(p-center)
 else:
  # Smooth the surface displacement over each cord rather than flattening its
  # individual vertices. This preserves tube thickness and braided detail.
  for iteration in range(4):
   points=[world[i] for i in indices]
   tree=KDTree(len(points));deltas=[]
   for k,p in enumerate(points):
    tree.insert(p,k);near,normal,_,_=target.find_nearest(p);deltas.append(near+normal*.004-p)
   tree.balance()
   for i,p in zip(indices,points):
    neighbours=tree.find_range(p,.018);weights=[max(.05,1-distance/.018) for _,_,distance in neighbours]
    delta=sum((deltas[k]*w for (_,k,_),w in zip(neighbours,weights)),Vector())/sum(weights)
    world[i]=p+delta
 # Preserve the engraved disks as rigid pieces; only their cords bend.
 if c in (1,3):
  pool=set(indices);adj={i:[] for i in indices}
  for edge in o.data.edges:
   a,b=edge.vertices
   if a in pool and b in pool:adj[a].append(b);adj[b].append(a)
  seen=set();clasp=[]
  for start in indices:
   if start in seen:continue
   todo=[start];seen.add(start);group=[]
   while todo:
    v=todo.pop();group.append(v)
    for n in adj[v]:
     if n not in seen:seen.add(n);todo.append(n)
   points0=[o.matrix_world@original[i] for i in group]
   if max(p.y for p in points0)-min(p.y for p in points0)<.08:clasp.extend(group)
  points0=[o.matrix_world@original[i] for i in clasp]
  center=sum(points0,Vector())/len(points0);near,normal,_,_=target.find_nearest(center)
  direction=Vector((0,1 if c==3 else -1,0));hit=target.ray_cast(center-direction*.3,direction,.8)
  if hit[0] is not None:near,normal=hit[0],hit[1]
  a=np.array([list(p-center) for p in points0]);vals,axes=np.linalg.eigh(a.T@a);axis=Vector(axes[:,0]);axis=axis if axis.dot(normal)>0 else -axis
  rotation=axis.rotation_difference(normal);half=max(abs((p-center).dot(axis)) for p in points0)
  for i,p in zip(clasp,points0):world[i]=near+normal*(half+.0025)+rotation@(p-center)
 for i in indices:o.data.vertices[i].co=o.matrix_world.inverted()@world[i]
 after=[target.find_nearest(world[i])[3] for i in indices]
 metrics.append({'component':c,'vertices':len(indices),'before_mean_mm':float(np.mean(before)*1000),'after_mean_mm':float(np.mean(after)*1000),'after_max_mm':max(after)*1000})
o.data.update();bpy.context.view_layer.update()
# UVs, groups, weights, topology and all non-trim positions remain unchanged.
assert all(v.co==original[v.index] for v in o.data.vertices if v.index not in ids)
(out/'strap-fit.json').write_text(json.dumps({'components':selected,'changed_vertices':len(ids),'metrics':metrics,'original_glb_untouched':True,'cape_and_skirt_disabled':True,'animation_validation':'pending'},indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(out/'D1 Warrior Medium - fitted straps.blend'))
bpy.ops.object.select_all(action='DESELECT')
for obj in bpy.context.scene.objects:
 if obj.type in ('MESH','ARMATURE') and not obj.hide_render and not obj.hide_get():obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(out/'D1 Warrior Medium - fitted straps.glb'),export_format='GLB',use_selection=True,export_animations=False)
print('STRAP_FIT',json.dumps(metrics))
