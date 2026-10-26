"""Blender --background --python SCRIPT -- MACE_PLAN.json
Check existing poses and full shadows, rigid grips, and weapon/body intersections.
No animation edits or automatic arm attenuation are permitted.
"""
import bpy,json,sys,gc
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent));from preflight_equipped_sets import check,opaque
plan=json.loads(Path(sys.argv[sys.argv.index('--')+1]).read_text());assert plan['equipment_family']=='light-mace';work=Path(plan['work']);checks=[];audits=[]
def geometry(obj):
 ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh();mesh.calc_loop_triangles();v=[ev.matrix_world@p.co for p in mesh.vertices];t=[tuple(p.vertices) for p in mesh.loop_triangles];ev.to_mesh_clear();return v,t
for job in plan['jobs']:
 result=check(job['model'],job['reference']);result.update(sheet=job['sheet'],motion=job['motion']);root=Path(job['root']);(root/'preflight.json').write_text(json.dumps(result,indent=2));checks.append(result);(work/'preflight-progress.json').write_text(json.dumps(checks,indent=2));ref=json.loads(Path(job['reference']).read_text());rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');mace=next(o for o in bpy.data.objects if o.get('d1r_asset')=='mace_base03.glb');item=next(e for e in ref['equipment'] if Path(e['path']).name=='mace_base03.glb');parts=[o for o in bpy.data.objects if opaque(o) and not o.get('d1r_equipment') and not any('base01_GLV' in m.name for m in o.data.materials)];records=[]
 for sample in range((ref['rows']-1)*4+1 if job['action']=='at' else ref['rows']):
  row=sample/4 if job['action']=='at' else sample;bpy.context.scene.frame_set(int(row),subframe=row%1);bpy.context.view_layer.update();grip=mace.matrix_world@Vector(item['grip']);target=rig.matrix_world@rig.pose.bones['hand.R'].matrix@Vector(item['hand_point']);v,t=geometry(mace);tree=BVHTree.FromPolygons(v,t,all_triangles=True);contacts=[]
  for part in parts:
   vertices,triangles=geometry(part)
   if any(max(p[k] for p in v)<min(p[k] for p in vertices) or min(p[k] for p in v)>max(p[k] for p in vertices) for k in range(3)):continue
   hits=tree.overlap(BVHTree.FromPolygons(vertices,triangles,all_triangles=True))
   if hits:contacts.append({'part':part.name,'triangles':len(hits)})
  records.append({'row':row,'grip_error':(grip-target).length,'contacts':contacts})
 audit={'sheet':job['sheet'],'max_grip_error':max(r['grip_error'] for r in records),'contact_rows':[r for r in records if r['contacts']],'samples':len(records)};audits.append(audit);(work/'mace-audit.json').write_text(json.dumps(audits,indent=2));print('MACE CHECK',job['sheet'],result['safe'],audit,flush=True);gc.collect()
assert len(checks)==9 and all(r['safe'] for r in checks),'Capture bounds require attention; do not alter body animation'
assert all(a['max_grip_error']<.001 and not a['contact_rows'] for a in audits),'Rigid weapon/body audit requires attention'
print('All mace animations checked; body motion unchanged',flush=True)
