"""Blender --python SCRIPT -- INSTALLED_CLOSED_GRIP_PLAN NEW_WORK
Roll rigid bow/string around the unchanged closed-palm shaft axis to fit
near the inside of the gauntlet, preserving body animation and bow shape.
"""
import bpy,json,sys,math,copy,hashlib,shutil
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from paladin_equipment import attach_equipment
from preflight_equipped_sets import opaque
from bake_bow_equipment import keys
source,work=map(Path,sys.argv[sys.argv.index('--')+1:]);old=json.loads(source.read_text());work=work.resolve();work.mkdir(exist_ok=False);p=copy.deepcopy(old);p.update(work=str(work),starting_custom_manifest=json.loads((Path(old['previous'])/'paladin-vanilla-dimensions/install-manifest.json').read_text()),jobs=[],motions=[],inventory={'wlb':{}},copies=[],bow_string_clearance_revision=True);reports=[]
def geo(o):
 e=o.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();m.calc_loop_triangles();v=[e.matrix_world@a.co for a in m.vertices];t=[tuple(a.vertices) for a in m.loop_triangles];e.to_mesh_clear();return v,t
for donor in old['jobs']:
 j=copy.deepcopy(donor);name=j['sheet'];r=json.loads(Path(j['reference']).read_text());rows=r['rows'];bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=j['model']);rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');gear=attach_equipment(rig,[r['equipment'][0]]);cord=next(o for o in gear if 'string' in o.name.lower());wood=next(o for o in gear if o!=cord);body=[o for o in bpy.data.objects if opaque(o) and o not in gear];samples=[]
 for row,time in enumerate(r['source_frames']):
  scene.frame_set(time);bpy.context.view_layer.update();h=rig.matrix_world@rig.pose.bones['hand.L'].matrix;P=h@Vector((-.04,.065,0));axis=(h.to_3x3()@Vector((0,0,1))).normalized();cv,ct=geo(cord);wv,wt=geo(wood);C=sum(cv,Vector())/len(cv);ts=[(v-C).dot(axis) for v in cv];trees=[]
  for o in body:
   v,t=geo(o);trees.append((o,BVHTree.FromPolygons(v,t,all_triangles=True)))
  samples.append({'row':row,'hand':h,'P':P,'axis':axis,'C':C,'lo':min(ts),'hi':max(ts),'trees':trees,'wood':wv,'cord':cv,'wt':wt,'ct':ct})
 def gap(sample,angle):
  P=sample['P'];axis=sample['axis'];q=Quaternion(axis,math.radians(angle));C=P+q@(sample['C']-P);tree=next(t for o,t in sample['trees'] if 'base01_GLV' in o.data.materials[0].name);lo,hi=sample['lo'],sample['hi'];best=(1e9,0)
  for k in range(121):
   u=lo+(hi-lo)*k/120;d=tree.find_nearest(C+axis*u)[3]
   if d<best[0]:best=(d,u)
  for k in range(41):
   u=best[1]-(hi-lo)/120+(hi-lo)/60*k/40;d=tree.find_nearest(C+axis*u)[3]
   if d<best[0]:best=(d,u)
  return best[0]-.002
 # Use a constant roll normally; the reference pose optionally fits a smooth cyclic roll.
 candidates=[]
 for angle in range(-60,61,2):
  values=[gap(s,angle) for s in samples]
  if min(values)>=.002:candidates.append((abs(min(values)-.003)+abs(angle)*.000001,angle,values))
 assert candidates,(name,'no clear near-arm candidate')
 chosen=None
 for score,angle,values in sorted(candidates):
  contacts=[]
  for s in samples:
   P=s['P'];q=Quaternion(s['axis'],math.radians(angle));v=[P+q@(a-P) for a in s['cord']];tree=BVHTree.FromPolygons(v,s['ct'],all_triangles=True)
   for o,bvh in s['trees']:
    if tree.overlap(bvh):contacts.append((s['row'],o.name))
   v=[P+q@(a-P) for a in s['wood']];tree=BVHTree.FromPolygons(v,s['wt'],all_triangles=True)
   for o,bvh in s['trees']:
    if 'base01_GLV' not in o.data.materials[0].name and tree.overlap(bvh):contacts.append((s['row'],o.name))
  if not contacts:chosen=(angle,values);break
 assert chosen,(name,'near-arm rolls intersect body');angle,values=chosen;pose_angles=[angle]*rows
 if old.get('bow_reference_pose_revision'):
  states=[]
  for sample in samples:
   available=[]
   for a in range(-60,61,2):
    distance=gap(sample,a)
    if not .002<=distance<=.012:continue
    P=sample['P'];q=Quaternion(sample['axis'],math.radians(a));bad=False
    for field,triangles in [('cord','ct'),('wood','wt')]:
     tree=BVHTree.FromPolygons([P+q@(v-P) for v in sample[field]],sample[triangles],all_triangles=True)
     for o,bvh in sample['trees']:
      if field=='wood' and 'base01_GLV' in o.data.materials[0].name:continue
      if tree.overlap(bvh):bad=True;break
     if bad:break
    if not bad:available.append((a,distance))
   assert available,(name,sample['row'],'no near-arm roll');states.append(available)
  best_cycle=None
  for first,first_gap in states[0]:
   dp={first:((1000*(first_gap-.003))**2,[first],[first_gap])}
   for options in states[1:]:
    next_dp={}
    for a,distance in options:
     paths=[(cost+.04*(a-prev)**2+(1000*(distance-.003))**2,path+[a],gaps+[distance]) for prev,(cost,path,gaps) in dp.items() if abs(a-prev)<=12]
     if paths:next_dp[a]=min(paths,key=lambda x:x[0])
    dp=next_dp
   for last,(cost,path,gaps) in dp.items():
    if abs(last-first)>12:continue
    item=(cost+.04*(last-first)**2,path,gaps)
    if best_cycle is None or item[0]<best_cycle[0]:best_cycle=item
  assert best_cycle,(name,'no continuous cyclic clearance path');_,pose_angles,values=best_cycle
 positions={wood:[],cord:[]}
 for s in samples:
  inv=s['hand'].inverted();P=s['P'];q=Quaternion(s['axis'],math.radians(pose_angles[s['row']]))
  for o,field in [(wood,'wood'),(cord,'cord')]:positions[o].append([inv@(P+q@(v-P)) for v in s[field]])
 # Reuse original mesh/UV/materials and replace only morph keys.
 for o in gear:
  if o.data.shape_keys:o.shape_key_clear()
  o.animation_data_clear();o.parent=None;o.matrix_world=Matrix.Identity(4);keys(o,positions[o])
 scene.frame_start=0;scene.frame_end=rows-1;scene.frame_set(0);bpy.ops.object.select_all(action='DESELECT')
 for o in gear:o.select_set(True)
 bow=work/(name+'-bow.glb');bpy.ops.export_scene.gltf(filepath=str(bow),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='SCENE',export_anim_scene_split_object=False,export_frame_range=True,export_force_sampling=True)
 refpath=work/'jobs'/name/'reference.json';refpath.parent.mkdir(parents=True);r['equipment'][0]['path']=str(bow);r['preview_caption']=name.upper()+' | string close inside arm';refpath.write_text(json.dumps(r,indent=2));j.update(reference=str(refpath),root=str(refpath.parent));p['jobs'].append(j);p['motions'].append({'name':j['motion']});p['inventory']['wlb'][name]=copy.deepcopy(old['inventory']['wlb'][name]);shutil.copy2(Path(old['work'])/(name+'-fit.json'),work/(name+'-fit.json'));report={'sheet':name,'additional_shaft_roll_degrees':pose_angles[0] if len(set(pose_angles))==1 else None,'per_pose_shaft_roll_degrees':pose_angles,'string_surface_arm_gap_metres':values,'minimum_gap_metres':min(values),'maximum_gap_metres':max(values),'body_contacts':[],'body_sha256':hashlib.sha256(Path(j['model']).read_bytes()).hexdigest().upper()};reports.append(report);bow.with_suffix('.fit.json').write_text(json.dumps(report,indent=2));print('NEAR ARM',report,flush=True)
p['bow_hold_angles']['string_arm_clearance_target_metres']=.003;p['bow_hold_angles']['string_clearance_rolls']={r['sheet']:r.get('per_pose_shaft_roll_degrees',r['additional_shaft_roll_degrees']) for r in reports};(work/'string-clearance.json').write_text(json.dumps(reports,indent=2));(work/'plan.json').write_text(json.dumps(p,indent=2))
