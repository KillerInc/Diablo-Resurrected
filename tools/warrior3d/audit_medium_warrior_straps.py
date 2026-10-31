import bpy,json
from pathlib import Path
from mathutils import Vector
import argparse
p=argparse.ArgumentParser(description="Audit connected upper armor components without changing the model.")
p.add_argument('scene',type=Path);p.add_argument('output',type=Path)
a=p.parse_args(__import__('sys').argv[__import__('sys').argv.index('--')+1:]);source=a.scene.resolve();output=a.output.resolve()
bpy.ops.wm.open_mainfile(filepath=str(source))
report=[]
for o in bpy.context.scene.objects:
 if o.type!='MESH':continue
 verts=o.data.vertices
 p=[o.matrix_world@v.co for v in verts]
 item={'name':o.name,'hidden_render':o.hide_render,'hidden_view':o.hide_get(),'bounds':[[min(v[i] for v in p) for i in range(3)],[max(v[i] for v in p) for i in range(3)]],'materials':[m.name for m in o.data.materials if m]}
 if o.name in ('Mesh_9','Mesh_10'):
  parents=list(range(len(verts)))
  def root(i):
   while parents[i]!=i:parents[i]=parents[parents[i]];i=parents[i]
   return i
  def join(a,b):parents[root(a)]=root(b)
  for e in o.data.edges:join(*e.vertices)
  dup={}
  for v in verts:
   key=tuple(round(float(x),5) for x in v.co)
   if key in dup:join(v.index,dup[key])
   else:dup[key]=v.index
  comps={}
  for v in verts:comps.setdefault(root(v.index),[]).append(v.index)
  result=[]
  for ids in comps.values():
   points=[p[i] for i in ids]
   if max(v.z for v in points)<1.35:continue
   weights={}
   for i in ids:
    for g in verts[i].groups:weights[o.vertex_groups[g.group].name]=weights.get(o.vertex_groups[g.group].name,0)+g.weight
   result.append({'ids':ids,'count':len(ids),'bounds':[[min(v[d] for v in points) for d in range(3)],[max(v[d] for v in points) for d in range(3)]],'bones':sorted(weights.items(),key=lambda x:-x[1])[:5]})
  item['components']=result
 report.append(item)
output.write_text(json.dumps(report,indent=2))
print(json.dumps([{**x,'components':[{k:v for k,v in c.items() if k!='ids'} for c in x.get('components',[])]} for x in report],indent=2))
