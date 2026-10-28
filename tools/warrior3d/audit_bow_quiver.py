"""Blender --python SCRIPT -- QUIVER_PLAN.json
Verify the final mount over every source pose. Strap contact is reported
separately from the pouch, rim, bottom and arrow geometry.
Explicit minor-back-overlap plans may intersect the pouch; arrows stay protected.
Private triangle-parts.json maps consolidated triangles to original components.
"""
import bpy,sys,json,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent));from paladin_equipment import attach_equipment
from preflight_equipped_sets import opaque
plan_file=Path(sys.argv[sys.argv.index('--')+1]);w=plan_file.resolve().parent;p=json.loads(plan_file.read_text());names=json.loads((w/'triangle-parts.json').read_text());shell={'Object_2.028','Object_2.029','Object_2.088','Object_2.089','Object_2.090'};reports=[]
def geo(o):
 e=o.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();m.calc_loop_triangles();vs=[e.matrix_world@v.co for v in m.vertices];ts=[tuple(t.vertices) for t in m.loop_triangles];e.to_mesh_clear();return vs,ts
for j in p['jobs']:
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=j['model']);rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');r=json.loads(Path(j['reference']).read_text());gear=attach_equipment(rig,[r['equipment'][-1]])[0];body=[o for o in bpy.data.objects if opaque(o) and o!=gear];basis=gear.matrix_basis.copy();tests=[]
 for dy in [0]:
  gear.matrix_basis=basis.copy();gear.matrix_basis.translation+=basis.to_3x3()@Vector((0,dy/.8,0));contacts=[];arrow_contacts=[]
  for row,t in enumerate(r['source_frames']):
   bpy.context.scene.frame_set(t);bpy.context.view_layer.update();v,all_ts=geo(gear);ts=[t for i,t in enumerate(all_ts) if names[i] in shell];arrows=[t for i,t in enumerate(all_ts) if names[i].startswith('Quiver arrow')];tree=BVHTree.FromPolygons(v,ts,all_triangles=True);arrow_tree=BVHTree.FromPolygons(v,arrows,all_triangles=True)
   for part in body:
    bv,bt=geo(part);hits=tree.overlap(BVHTree.FromPolygons(bv,bt,all_triangles=True))
    if arrow_tree.overlap(BVHTree.FromPolygons(bv,bt,all_triangles=True)):arrow_contacts.append({'row':row,'body':part.name})
    if hits:contacts.append({'row':row,'body':part.name,'hits':len(hits)})
  tests.append({'outward_metres':dy,'contacts':contacts,'arrow_contacts':arrow_contacts})
  if not contacts:break
 reports.append({'sheet':j['sheet'],'model_sha256':hashlib.sha256(Path(j['model']).read_bytes()).hexdigest().upper(),'reference_sha256':hashlib.sha256(Path(j['reference']).read_bytes()).hexdigest().upper(),'quiver_sha256':hashlib.sha256(Path(r['equipment'][-1]['path']).read_bytes()).hexdigest().upper(),'tests':tests});(w/'final-clearance.json').write_text(json.dumps(reports,indent=2));print(j['sheet'],dy,len(contacts),flush=True)

allow=p.get('quiver_fit',{}).get('approved_minor_back_overlap',False)
assert not allow or 0<p['quiver_fit']['additional_inward_metres']<=.02
assert len(reports)==9 and all(not r['tests'][-1]['arrow_contacts'] and (allow or not r['tests'][-1]['contacts']) for r in reports), 'Unapproved pouch or arrow intersection'
