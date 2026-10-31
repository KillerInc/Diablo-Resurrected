"""Blender --python SCRIPT -- QUIVER_FIT_PLAN.json
Measure the closest inward chest mount that clears every approved bow pose.
Straps may touch the torso; pouch, rim, lining and arrows are protected.
"""
import bpy,sys,json,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from paladin_equipment import attach_equipment
from preflight_equipped_sets import opaque
file=Path(sys.argv[sys.argv.index('--')+1]);p=json.loads(file.read_text());w=file.resolve().parent;names=json.loads((w/'triangle-parts.json').read_text());shell={'Object_2.028','Object_2.029','Object_2.088','Object_2.089','Object_2.090'};distances=[i*.0025 for i in range(21)];hits={str(d):[] for d in distances};body_hashes={}
def geo(o):
 e=o.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();m.calc_loop_triangles();vs=[e.matrix_world@v.co for v in m.vertices];ts=[tuple(t.vertices) for t in m.loop_triangles];e.to_mesh_clear();return vs,ts
for j in p['jobs']:
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=j['model']);rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');r=json.loads(Path(j['reference']).read_text());qspec=next(e for e in r['equipment'] if e.get('town_role')=='back_quiver');gear=attach_equipment(rig,[qspec])[0];body=[o for o in bpy.data.objects if opaque(o) and o!=gear];body_hashes[j['sheet']]=hashlib.sha256(Path(j['model']).read_bytes()).hexdigest().upper()
 for row,t in enumerate(r['source_frames']):
  bpy.context.scene.frame_set(t);bpy.context.view_layer.update();v,ts=geo(gear);protected=[a for i,a in enumerate(ts) if names[i] in shell or names[i].startswith('Quiver arrow')];body_trees=[]
  for o in body:
   bv,bt=geo(o);body_trees.append((o.name,BVHTree.FromPolygons(bv,bt,all_triangles=True)))
  for d in distances:
   if hits[str(d)]:continue
   delta=gear.matrix_world.to_3x3()@Vector((0,-d/.8,0));tree=BVHTree.FromPolygons([a+delta for a in v],protected,all_triangles=True)
   for name,bvh in body_trees:
    if tree.overlap(bvh):hits[str(d)].append({'sheet':j['sheet'],'row':row,'body':name});break
 print('CHECKED',j['sheet'],flush=True)
safe=[d for d in distances if not hits[str(d)]];assert 0 in safe;maximum=max(safe);selected=max(0,maximum-.0025) if maximum else 0;assert selected>0,'Existing mount is already at the no-contact limit';report={'maximum_collision_free_inward_metres':maximum,'selected_inward_metres':selected,'extra_clearance_margin_metres':maximum-selected,'body_sha256':body_hashes,'tests':hits};(w/'quiver-fit-search.json').write_text(json.dumps(report,indent=2))
for j in p['jobs']:
 rp=Path(j['reference']);r=json.loads(rp.read_text());q=next(e for e in r['equipment'] if e.get('town_role')=='back_quiver');m=q['local_transform']
 for k in range(3):m[k][3]-=m[k][1]*selected/.8
 q['pouch_clearance_outward_metres']=q.get('pouch_clearance_outward_metres',.03)-selected;q['quiver_inward_revision_metres']=selected;rp.write_text(json.dumps(r,indent=2))
p['quiver_fit']=report;file.write_text(json.dumps(p,indent=2));print('QUIVER INWARD',selected,'metres',flush=True)
