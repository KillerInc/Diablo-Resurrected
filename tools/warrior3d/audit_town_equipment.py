"""Blender --background --python SCRIPT -- TOWN_PLAN.json
Fit transparent canvases and check stowed gear against the approved town poses.
"""
import bpy,json,sys,math,gc
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent));from preflight_equipped_sets import check,opaque
from back_shield_contact import shell_triangles
file=Path(sys.argv[sys.argv.index('--')+1]);plan=json.loads(file.read_text());work=Path(plan['work']);checks=[];audits=[];padding=[]
def geometry(o):
 ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();m.calc_loop_triangles();v=[ev.matrix_world@x.co for x in m.vertices];t=[tuple(x.vertices) for x in m.loop_triangles];ev.to_mesh_clear();return v,t
def bounds(v):return ([min(p[k] for p in v) for k in range(3)],[max(p[k] for p in v) for k in range(3)])
for j in plan['jobs']:
 rp=Path(j['reference']);ref=json.loads(rp.read_text());ref.update(canvas_logical=[256,192],canvas_anchor=[128,176],capture_bounds=True);rp.write_text(json.dumps(ref,indent=2));large=check(j['model'],rp);boxes=[b['bounds'] for b in large['cell_bounds']];inv=plan['inventory'][j['code']][j['sheet']];logical=inv['cell']//8;gx=logical*4;gy=(logical-16)*8;xmin=min(b[0] for b in boxes)+gx-1024;xmax=max(b[2] for b in boxes)+gx-1024;ymin=min(b[1] for b in boxes)+gy-1280;ymax=max(b[3] for b in boxes)+gy-1280;pad=max(0,math.ceil((16-xmin)/8),math.ceil((xmax+16-logical*8)/8));top=max(0,math.ceil((16-ymin)/8));bottom=max(0,math.ceil((ymax+16-logical*8)/8));canvas=[logical+2*pad,logical+top+bottom];anchor=[logical//2+pad,logical+top];ref.update(canvas_logical=canvas,canvas_anchor=anchor,pose_offsets=large['pose_offsets']);ref.pop('capture_bounds',None);rp.write_text(json.dumps(ref,indent=2));inv.update(size=[canvas[0]*64,canvas[1]*8*ref['rows']],canvas_logical=canvas,canvas_anchor=anchor);file.write_text(json.dumps(plan,indent=2));result=check(j['model'],rp);result.update(sheet=j['sheet'],motion=j['motion']);checks.append(result);(Path(j['root'])/'preflight.json').write_text(json.dumps(result,indent=2));(work/'preflight-progress.json').write_text(json.dumps(checks,indent=2));padding.append({'sheet':j['sheet'],'canvas':canvas,'anchor':anchor});(work/'canvas-padding.json').write_text(json.dumps(padding,indent=2));rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');gear=[o for o in bpy.data.objects if o.type=='MESH' and o.get('d1r_equipment')];parts=[o for o in bpy.data.objects if opaque(o) and not o.get('d1r_equipment')];contacts=[]
 for row in range(ref['rows']):
  bpy.context.scene.frame_set(row);bpy.context.view_layer.update();body=[]
  for o in parts:
   v,t=geometry(o);body.append((o,v,t,bounds(v),None))
  for o in gear:
   if o.get('town_contact_ok'):continue
   v,t=geometry(o);box=bounds(v);tree=None;asset=o.get('d1r_asset','');rear=[]
   if any(Path(e['path']).name==asset and e.get('town_role')=='back_shield' and e.get('allow_rear_band_body_overlap') for e in ref['equipment']):t,rear=shell_triangles(o.data)
   for k,(part,bv,bt,bb,cached) in enumerate(body):
    material=part.data.materials[0].name
    if 'Shield_' in asset and not plan.get('town_back_stow_revision') and 'P00_HED' not in material:continue
    if 'twoHandAxe' in asset and 'base01_GLV' in material:continue
    if any(box[1][a]<bb[0][a] or box[0][a]>bb[1][a] for a in range(3)):continue
    if tree is None:tree=BVHTree.FromPolygons(v,t,all_triangles=True)
    if cached is None:cached=BVHTree.FromPolygons(bv,bt,all_triangles=True);body[k]=(part,bv,bt,bb,cached)
    hits=tree.overlap(cached)
    if hits:contacts.append({'row':row,'equipment':o.name,'asset':asset,'part':part.name,'triangles':len(hits)})
 audit={'sheet':j['sheet'],'samples':ref['rows'],'contact_rows':contacts,'roles':[e['town_role'] for e in ref['equipment']]};audits.append(audit);(work/'town-audit.json').write_text(json.dumps(audits,indent=2));print('TOWN CHECK',j['sheet'],result['safe'],'contacts',len(contacts),flush=True);gc.collect()
assert len(checks)==len(plan['jobs']) and all(r['safe'] for r in checks),'Town capture bounds need review'
assert all(not r['contact_rows'] for r in audits),'Town gear/body placement needs review'
print('All town gear placements and full shadows checked')
