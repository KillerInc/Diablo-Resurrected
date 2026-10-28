"""Blender --python SCRIPT -- TRANSLATED_QUIVER_PLAN.json
Fit a small back-following pitch while retaining collision clearance in all poses.
"""
import bpy,sys,json,math
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from paladin_equipment import attach_equipment
from preflight_equipped_sets import opaque
file=Path(sys.argv[sys.argv.index('--')+1]);p=json.loads(file.read_text());w=file.resolve().parent;names=json.loads((w/'triangle-parts.json').read_text());shell={'Object_2.028','Object_2.029','Object_2.088','Object_2.089','Object_2.090'};pivot=Vector((-.129,0,.28));states=[(a,k) for a in range(0,-7,-1) for k in range(-4,9)];hits={str(t):[] for t in states};shell_points=None
(file.with_name('translation-only-plan.json')).write_text(json.dumps(p,indent=2));backup=w/'translation-only-references';backup.mkdir(exist_ok=True)
def transform(a,k):return Matrix.Translation((0,-k*.0025/.8,0))@Matrix.Translation(pivot)@Matrix.Rotation(math.radians(a),4,'X')@Matrix.Translation(-pivot)
def geo(o):
 e=o.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();m.calc_loop_triangles();v=[e.matrix_world@a.co for a in m.vertices];t=[tuple(a.vertices) for a in m.loop_triangles];e.to_mesh_clear();return v,t
for j in p['jobs']:
 rp=Path(j['reference']);r=json.loads(rp.read_text());(backup/(j['sheet']+'.json')).write_bytes(rp.read_bytes());bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=j['model']);rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');spec=next(e for e in r['equipment'] if e.get('town_role')=='back_quiver');assert not spec.get('back_contour_pitch_degrees'),'Start from a translated, unpitched mount';gear=attach_equipment(rig,[spec])[0];body=[o for o in bpy.data.objects if opaque(o) and o!=gear]
 for row,time in enumerate(r['source_frames']):
  bpy.context.scene.frame_set(time);bpy.context.view_layer.update();v,t=geo(gear);G=gear.matrix_world.copy();local=[G.inverted()@a for a in v];protected=[tri for i,tri in enumerate(t) if names[i] in shell or names[i].startswith('Quiver arrow')]
  if shell_points is None:
   ids=set(i for k,tri in enumerate(t) if names[k] in shell for i in tri);shell_points=[local[i] for i in ids]
  trees=[]
  for o in body:
   bv,bt=geo(o);trees.append((o.name,BVHTree.FromPolygons(bv,bt,all_triangles=True)))
  for state in states:
   if hits[str(state)]:continue
   M=G@transform(*state);tree=BVHTree.FromPolygons([M@a for a in local],protected,all_triangles=True)
   for name,bvh in trees:
    if tree.overlap(bvh):hits[str(state)].append({'sheet':j['sheet'],'row':row,'body':name});break
 print('CONTOUR CHECK',j['sheet'],flush=True)
choices=[]
for a,k in states:
 if (a,k-1) not in states or hits[str((a,k))] or hits[str((a,k-1))]:continue
 F=transform(a,k-1);score=.8*sum((v-F@v).y for v in shell_points)/len(shell_points);choices.append((score,a,k-1))
score,angle,step=max(choices);assert score>0,'Contour fit did not improve closeness';F=transform(angle,step);extra=step*.0025;initial=p['quiver_fit']['selected_inward_metres'];report={'pitch_degrees':angle,'additional_inward_metres':extra,'total_translation_inward_metres':initial+extra,'average_pouch_inward_metres':initial+score,'pivot_mesh_local':list(pivot),'margin_tested_inward_metres':.0025,'tests':hits};(w/'quiver-contour-search.json').write_text(json.dumps(report,indent=2))
for j in p['jobs']:
 rp=Path(j['reference']);r=json.loads(rp.read_text());q=next(e for e in r['equipment'] if e.get('town_role')=='back_quiver');M=Matrix(q['local_transform'])@F;q['local_transform']=[list(row) for row in M];q['quiver_inward_revision_metres']=initial+extra;q['pouch_clearance_outward_metres']-=extra;q['back_contour_pitch_degrees']=angle;rp.write_text(json.dumps(r,indent=2))
p['quiver_fit'].update(selected_inward_metres=initial+extra,contour=report);file.write_text(json.dumps(p,indent=2));print('SELECTED CONTOUR',angle,extra,'average inward',initial+score,flush=True)
