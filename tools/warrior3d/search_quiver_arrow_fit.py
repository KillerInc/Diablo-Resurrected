"""Blender --python SCRIPT -- PREVIOUS_PLAN NEW_WORK
Search short hidden shafts and small rigid translations with wall clearance and
four inside-pouch cross-section checks per arrow. Source art stays unchanged.
"""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
old,w=map(Path,sys.argv[sys.argv.index('--')+1:]);w=w.resolve();p=json.loads(old.read_text());previous=Path(p['work']);r=json.loads(Path(p['jobs'][0]['reference']).read_text());q=next(e for e in r['equipment'] if e.get('town_role')=='back_quiver');bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=q['path']);m=next(o.data for o in bpy.data.objects if o.type=='MESH');m.calc_loop_triangles();names=json.loads((previous/'triangle-parts.json').read_text());v=[a.co.copy() for a in m.vertices];wall=[tuple(t.vertices) for i,t in enumerate(m.loop_triangles) if not names[i].startswith('Quiver arrow')];tree=BVHTree.FromPolygons(v,wall,all_triangles=True,epsilon=.0005);shifts=sorted([(a*.0025,b*.0025) for a in range(-16,17) for b in range(-16,17)],key=lambda a:a[0]**2+a[1]**2)
protected=[tuple(t.vertices) for i,t in enumerate(m.loop_triangles) if names[i] in {'Object_2.028','Object_2.029','Object_2.088','Object_2.089','Object_2.090'}];inside_tree=BVHTree.FromPolygons(v,protected,all_triangles=True)
for z in [-.15,-.05,.05,.15]:
 chosen={}
 for number in range(1,7):
  av=[];at=[]
  for i,t in enumerate(m.loop_triangles):
   if not names[i].startswith('Quiver arrow '+str(number)+' '):continue
   poly=[v[k] for k in t.vertices];out=[]
   for a,b in zip(poly,poly[1:]+poly[:1]):
    if a.z>=z:out.append(a)
    if (a.z>=z)!=(b.z>=z):out.append(a+(b-a)*((z-a.z)/(b.z-a.z)))
   for k in range(1,len(out)-1):base=len(av);av.extend([out[0],out[k],out[k+1]]);at.append((base,base+1,base+2))
  centres=[]
  for level in [z+.005,z+(.15-z)/3,z+2*(.15-z)/3,.15]:
   pts={}
   for tri in at:
    poly=[av[k] for k in tri]
    for a,b in zip(poly,poly[1:]+poly[:1]):
     if (a.z>=level)!=(b.z>=level):c=a.lerp(b,(level-a.z)/(b.z-a.z));pts[tuple(round(x,6) for x in c)]=c
   assert pts;centres.append(sum(pts.values(),Vector())/len(pts))
  for dx,dy in shifts:
   shift=Vector((dx,dy,0))
   if not all(inside_tree.ray_cast(c+shift,Vector((0,sign,0)),.15)[0] is not None for c in centres for sign in [-1,1]):continue
   a=[x+shift for x in av]
   if not BVHTree.FromPolygons(a,at,all_triangles=True).overlap(tree):chosen[str(number)]=[dx,dy];break
  if str(number) not in chosen:break
 print('CANDIDATE',z,chosen,flush=True)
 if len(chosen)==6:(w/'arrow-fit.json').write_text(json.dumps({'cut_z':z,'translations_mesh_local':chosen,'wall_margin_mesh_local':.0005,'shaft_containment_required':True},indent=2));break
assert len(chosen)==6
