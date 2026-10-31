"""Blender --background --python SCRIPT -- CORRECTED_PLAN.json
Check every shield pose, both strap locations, head intersections and bounds.
"""
import bpy,json,sys,gc
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
plan_file=Path(sys.argv[sys.argv.index('--')+1]);plan=json.loads(plan_file.read_text());work=Path(plan['work']);sys.path.insert(0,str(Path(__file__).parent));from author_equipped_motion import author;from preflight_equipped_sets import check
if not Path(plan['author_once']['model']).exists():author(plan['author_once']['recipe'],plan['author_once']['model'])
records=[];audits=[]
def tree(o):
 ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();m.calc_loop_triangles();v=[ev.matrix_world@x.co for x in m.vertices];t=[tuple(x.vertices) for x in m.loop_triangles];r=BVHTree.FromPolygons(v,t,all_triangles=True);ev.to_mesh_clear();return r
for j in plan['jobs']:
 result=check(j['model'],j['reference']);result.update(sheet=j['sheet'],motion=j['motion']);root=Path(j['root']);(root/'preflight.json').write_text(json.dumps(result,indent=2));records.append(result);(work/'preflight-progress.json').write_text(json.dumps(records,indent=2));rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');shield=next(o for o in bpy.data.objects if o.get('d1r_asset')=='Shield_S15_Warrior_Red.glb');heads=[o for o in bpy.data.objects if o.type=='MESH' and any('P00_HED' in m.name for m in o.data.materials)];ref=json.loads(Path(j['reference']).read_text());item=next(e for e in ref['equipment'] if 'Shield_' in e['path']);frames=[]
 for sample in range((ref['rows']-1)*4+1 if j['sheet'].endswith('at') else ref['rows']):
  row=sample/4 if j['sheet'].endswith('at') else sample
  bpy.context.scene.frame_set(int(row),subframe=row%1);bpy.context.view_layer.update();small=shield.matrix_world@Vector(item['grip']);large=shield.matrix_world@Vector((-.10,0,-.12));hand=rig.matrix_world@rig.pose.bones['hand.L'].matrix@Vector(item['hand_point']);elbow=rig.matrix_world@rig.pose.bones['forearm.L'].head;s=tree(shield);frames.append({'row':row,'hand_grip_error':(small-hand).length,'large_strap_nearer_elbow':(large-elbow).length<(small-elbow).length,'head_contacts':sum(len(s.overlap(tree(h))) for h in heads)})
 audit={'sheet':j['sheet'],'maximum_grip_error':max(r['hand_grip_error'] for r in frames),'head_contact_rows':[r['row'] for r in frames if r['head_contacts']],'elbow_strap_wrong_rows':[r['row'] for r in frames if not r['large_strap_nearer_elbow']],'frames':frames};audits.append(audit);(work/'strap-audit.json').write_text(json.dumps(audits,indent=2));print('CHECK',j['sheet'],result['safe'],result['minimum_body_margin'],result['minimum_shadow_margin_before_blur'],{k:v for k,v in audit.items() if k!='frames'},flush=True);gc.collect()
assert all(r['safe'] for r in records),'Bounds preflight failed; do not change body motion to compensate'
assert all(not a['head_contact_rows'] and not a['elbow_strap_wrong_rows'] and a['maximum_grip_error']<.012 for a in audits),'Shield mounting audit failed'
print('All shield placements checked without altering body animation',flush=True)
