"""Blender --background --python SCRIPT -- A1_PLAN.json
Author native samples, fit transparent canvases, and audit two-hand contact/body.
Body scale and arm motion are never changed to fit the canvas.
"""
import bpy,json,sys,math,gc
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent));from author_equipped_motion import author;from preflight_equipped_sets import check,opaque
file=Path(sys.argv[sys.argv.index('--')+1]);plan=json.loads(file.read_text());assert plan['equipment_family']=='light-axe';work=Path(plan['work']);checks=[];audits=[];padding=[]
def geometry(obj):
 ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh();mesh.calc_loop_triangles();v=[ev.matrix_world@p.co for p in mesh.vertices];t=[tuple(p.vertices) for p in mesh.loop_triangles];ev.to_mesh_clear();return v,t
for job in plan['jobs']:
 motion=next(m for m in plan['motions'] if m['name']==job['motion']);author(motion['recipe'],job['model']) if not plan.get('reuse_body_animation') else None;reference=Path(job['reference']);ref=json.loads(reference.read_text());ref.update(canvas_logical=[256,192],canvas_anchor=[128,176],capture_bounds=True);reference.write_text(json.dumps(ref,indent=2));large=check(job['model'],reference);boxes=[b['bounds'] for b in large['cell_bounds']];inv=plan['inventory']['wla'][job['sheet']];logical=inv['cell']//8;ground=(logical*4,(logical-16)*8);offset=(ground[0]-1024,ground[1]-1280);xmin=min(b[0] for b in boxes)+offset[0];ymin=min(b[1] for b in boxes)+offset[1];xmax=max(b[2] for b in boxes)+offset[0];ymax=max(b[3] for b in boxes)+offset[1];guard=16;horizontal=max(0,math.ceil((guard-xmin)/8),math.ceil((xmax+guard-logical*8)/8));top=max(0,math.ceil((guard-ymin)/8));bottom=max(0,math.ceil((ymax+guard-logical*8)/8));canvas=[logical+2*horizontal,logical+top+bottom];anchor=[logical//2+horizontal,logical+top];ref.update(canvas_logical=canvas,canvas_anchor=anchor,pose_offsets=large['pose_offsets']);ref.pop('capture_bounds',None);reference.write_text(json.dumps(ref,indent=2));inv.update(size=[canvas[0]*64,canvas[1]*8*ref['rows']],canvas_logical=canvas,canvas_anchor=anchor);padding.append({'sheet':job['sheet'],'original_logical':[logical,logical],'canvas_logical':canvas,'anchor':anchor,'transparent_padding':[horizontal,top,horizontal,bottom]});file.write_text(json.dumps(plan,indent=2));result=check(job['model'],reference);result.update(sheet=job['sheet'],motion=job['motion']);(Path(job['root'])/'preflight.json').write_text(json.dumps(result,indent=2));checks.append(result);(work/'preflight-progress.json').write_text(json.dumps(checks,indent=2))
 rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');axe=next(o for o in bpy.data.objects if o.get('d1r_asset')=='twoHandAxe_base01.glb');item=ref['equipment'][0];parts=[o for o in bpy.data.objects if opaque(o) and not o.get('d1r_equipment') and not any('base01_GLV' in m.name for m in o.data.materials)];records=[]
 for sample in range((ref['rows']-1)*4+1 if job['action']=='at' else ref['rows']):
  row=sample/4 if job['action']=='at' else sample;bpy.context.scene.frame_set(int(row),subframe=row%1);bpy.context.view_layer.update();right=rig.matrix_world@rig.pose.bones['hand.R'].matrix@Vector((.0425,.0825,-.002));left=rig.matrix_world@rig.pose.bones['hand.L'].matrix@Vector((0,.05,0));local=axe.matrix_world.inverted()@left;right_local=axe.matrix_world.inverted()@right;v,t=geometry(axe);tree=BVHTree.FromPolygons(v,t,all_triangles=True);contacts=[]
  for part in parts:
   vertices,triangles=geometry(part)
   if any(max(p[k] for p in v)<min(p[k] for p in vertices) or min(p[k] for p in v)>max(p[k] for p in vertices) for k in range(3)):continue
   hits=tree.overlap(BVHTree.FromPolygons(vertices,triangles,all_triangles=True))
   if hits:contacts.append({'part':part.name,'triangles':len(hits)})
  records.append({'row':row,'right_grip_error':math.hypot(right_local.x,right_local.z),'left_shaft_error':math.hypot(local.x,local.z),'left_shaft_y':local.y,'contacts':contacts})
 audit={'native_support_hand_release_preserved':True,'sheet':job['sheet'],'samples':len(records),'max_right_grip_error':max(r['right_grip_error'] for r in records),'max_left_shaft_error':max(r['left_shaft_error'] for r in records),'left_grip_range':[min(r['left_shaft_y'] for r in records),max(r['left_shaft_y'] for r in records)],'contact_rows':[r for r in records if r['contacts']]};audits.append(audit);(work/'axe-audit.json').write_text(json.dumps(audits,indent=2));(work/'canvas-padding.json').write_text(json.dumps(padding,indent=2));print('AXE CHECK',job['sheet'],result['safe'],canvas,audit,flush=True);gc.collect()
assert len(checks)==4 and all(c['safe'] for c in checks),'Canvas fitting failed'
assert all(a['max_right_grip_error']<.04 and a['max_left_shaft_error']<.22 and a['left_grip_range'][0]>-1 and a['left_grip_range'][1]<.3653 and not a['contact_rows'] for a in audits),'Grip/body clearance requires review'
print('All A1 axe poses and minimum transparent canvases checked',flush=True)
