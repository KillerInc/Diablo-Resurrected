"""Blender --python SCRIPT -- FULL_MOTION_PLAN.json
Report equipment contact without modifying a pose to hide it.
"""
import bpy,json,sys,gc
from pathlib import Path
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
from preflight_equipped_sets import check,opaque
file=Path(sys.argv[sys.argv.index('--')+1]);plan=json.loads(file.read_text());audits=[]
def geometry(o):
 ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();m.calc_loop_triangles();v=[ev.matrix_world@x.co for x in m.vertices];t=[tuple(x.vertices) for x in m.loop_triangles];ev.to_mesh_clear();return v,t
def bounds(v):return ([min(p[k] for p in v) for k in range(3)],[max(p[k] for p in v) for k in range(3)])
for j in plan['jobs']:
 ref=json.loads(Path(j['reference']).read_text());check(j['model'],j['reference']);parts=[o for o in bpy.data.objects if opaque(o) and not o.get('d1r_equipment') and 'base01_GLV' not in o.data.materials[0].name];gear=[o for o in bpy.data.objects if o.type=='MESH' and o.get('d1r_equipment')];contacts=[]
 for row in range(ref['rows']):
  bpy.context.scene.frame_set(row);bpy.context.view_layer.update();body=[]
  for part in parts:
   v,t=geometry(part);body.append((part,v,t,bounds(v),None))
  for o in gear:
   v,t=geometry(o);box=bounds(v);tree=None;asset=o.get('d1r_asset','')
   for k,(part,bv,bt,bb,cached) in enumerate(body):
    # Combat shield straps brace against the forearm; preserve the existing
    # audit convention while checking the critical head clearance.
    if 'Shield_' in asset and 'P00_HED' not in part.data.materials[0].name:continue
    if any(box[1][a]<bb[0][a] or box[0][a]>bb[1][a] for a in range(3)):continue
    if tree is None:tree=BVHTree.FromPolygons(v,t,all_triangles=True)
    if cached is None:cached=BVHTree.FromPolygons(bv,bt,all_triangles=True);body[k]=(part,bv,bt,bb,cached)
    hits=tree.overlap(cached)
    if hits:contacts.append({'row':row,'asset':asset,'part':part.name,'triangles':len(hits)})
 audits.append({'sheet':j['sheet'],'contact_rows':contacts,'pose_modified_for_contact':False});(Path(plan['work'])/'native-contact-audit.json').write_text(json.dumps(audits,indent=2));print('NATIVE CONTACT AUDIT',j['sheet'],len(contacts),flush=True);gc.collect()
