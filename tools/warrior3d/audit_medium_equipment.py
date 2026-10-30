"""Audit actual head/helmet contact across all equipped medium poses."""
import bpy,json,sys,gc
from pathlib import Path
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from paladin_equipment import attach_equipment
file=Path(sys.argv[sys.argv.index('--')+1]).resolve();plan=json.loads(file.read_text());results=[]
for job in plan['jobs']:
 ref=json.loads(Path(job['reference']).read_text())
 if not ref.get('equipment'):continue
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=job['model']);rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');gear=attach_equipment(rig,ref['equipment']);head=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.data.materials and any(t in o.data.materials[0].name for t in ('P00_HED','Helmet dark gray metal'))];assert len(head)==2
 contacts=[]
 for row,frame in enumerate(ref['source_frames']):
  bpy.context.scene.frame_set(int(frame));bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get();trees=[]
  for o in head+gear:
   ev=o.evaluated_get(deps);mesh=ev.to_mesh();vertices=[ev.matrix_world@v.co for v in mesh.vertices];faces=[tuple(p.vertices) for p in mesh.polygons];tree=BVHTree.FromPolygons(vertices,faces);lo=[min(v[a] for v in vertices) for a in range(3)];hi=[max(v[a] for v in vertices) for a in range(3)];trees.append((o,tree,lo,hi));ev.to_mesh_clear()
  for h,tree,lo,hi in trees[:2]:
   for o,other,ol,oh in trees[2:]:
    if any(hi[a]<ol[a] or lo[a]>oh[a] for a in range(3)):continue
    hits=tree.overlap(other)
    if hits:contacts.append({'row':row,'part':h.name,'equipment':o.get('d1r_asset',o.name),'intersections':len(hits)})
 results.append({'sheet':job['sheet'],'frames':ref['rows'],'head_contacts':contacts});(Path(plan['work'])/'all-equipment-head-audit.json').write_text(json.dumps(results,indent=2));print('HEAD_AUDIT',job['sheet'],len(contacts),flush=True);gc.collect()
print('MEDIUM_HEAD_AUDIT_DONE',len(results),flush=True)
