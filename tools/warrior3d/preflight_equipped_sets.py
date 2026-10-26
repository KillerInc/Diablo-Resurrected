"""Prepare authored equipment motions and check all poses before raster rendering.

Blender --python SCRIPT -- PLAN.json
Only pose excursions may be blended toward the corresponding existing idle.
Body/equipment geometry, canvas, anchor and southeast shadow length stay fixed.
"""
import bpy,json,sys,math,gc
from pathlib import Path
import numpy as np
from mathutils import Matrix,Quaternion,Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from author_equipped_motion import author,tracks,blend
from merge_paladin_walk import read
from paladin_equipment import attach_equipment

def opaque(o):
 return o.type=='MESH' and o.data.materials and any(t in o.data.materials[0].name for t in ['base16_TRS','armor_skin','P00_HED','base01_GLV','base01_LEG','base05_BTS'])

def native_root_drive(model,ref):
 """Use travel relative to the native clip's start, not a blended idle pose."""
 spec=json.loads(Path(model).with_suffix('.motion.json').read_text())['recipe'];g,b=read(spec['source']);tr=tracks(g,b);names={n.get('name'):i for i,n in enumerate(g['nodes'])};parents={c:i for i,n in enumerate(g['nodes']) for c in n.get('children',[])}
 def position(frame):
  cache={}
  def value(i,path,default):
   if (i,path) not in tr:return g['nodes'][i].get(path,default)
   times,values,method=tr[i,path];t=frame/30;hi=int(np.searchsorted(times,t,side='right'))
   if hi==0:return values[0]
   if hi>=len(times):return values[-1]
   lo=hi-1;weight=0 if method=='STEP' else float((t-times[lo])/(times[hi]-times[lo]));return blend(values[lo],values[hi],weight,path)
  def world(i):
   if i not in cache:
    n=g['nodes'][i]
    if 'matrix' in n:m=Matrix([n['matrix'][j:j+4] for j in range(0,16,4)]).transposed()
    else:
     q=value(i,'rotation',[0,0,0,1]);m=Matrix.LocRotScale(Vector(value(i,'translation',[0,0,0])),Quaternion((q[3],*q[:3])),Vector(value(i,'scale',[1,1,1])))
    cache[i]=world(parents[i])@m if i in parents else m
   return cache[i]
  p=world(names[ref['motion_root_bone']]).translation;return np.array([p.x,-p.z])
 origin=position(0);count=len(spec['frames']);returns=ref.get('root_motion_return',[1]*count);idle=spec.get('idle_weights',[0]*count);result=[(position(frame)-origin)*ref.get('root_motion_scale',0)*returns[row]*(1-idle[row]) for row,frame in enumerate(spec['frames'])]
 for _ in range(spec.get('temporal_smoothing_passes',0)):
  old=result;locked=set(spec.get('locked_rows',[0,count-1]));result=[p if row in locked or row==0 or row==count-1 else old[row-1]*.25+p*.5+old[row+1]*.25 for row,p in enumerate(old)]
 return [p.tolist() for p in result]

def check(model,reference):
 ref=json.loads(Path(reference).read_text());drive=native_root_drive(model,ref) if ref.get('native_root_drive') else None;bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=str(model));rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');rig.rotation_mode='XYZ';rig.rotation_euler=(0,0,0);rig.location=(0,0,0);scene.frame_set(0);bpy.context.view_layer.update();equipment=attach_equipment(rig,ref.get('equipment',[]));body=[o for o in bpy.data.objects if o.type=='MESH' and o not in equipment];parts=[o for o in body if opaque(o)];assert len(parts)==6
 logical=ref.get('canvas_logical',ref['cell']//8);width,height=(logical,logical) if isinstance(logical,int) else logical;width*=8;height*=8
 initial=(rig.matrix_world@rig.pose.bones['pelvis'].head).copy();actor_name=ref.get('motion_root_bone');actor_initial=(rig.matrix_world@rig.pose.bones[actor_name].head).copy() if actor_name else None;root_positions=[];cell=ref['cell'];anchor=ref['canvas_anchor'];ground=np.array([anchor[0]*8,(anchor[1]-16)*8]);density=1.1334110707181562*768/2.75;floors=[];bounds=[];collisions=[];target_floor=-.0026297522708773613
 def vertices(o,deps,need_faces=False):
  ev=o.evaluated_get(deps);mesh=ev.to_mesh();a=np.empty(len(mesh.vertices)*3,dtype=np.float32);mesh.vertices.foreach_get('co',a);m=np.asarray(ev.matrix_world,dtype=float);world=a.reshape(-1,3)@m[:3,:3].T+m[:3,3];faces=[tuple(p.vertices) for p in mesh.polygons] if need_faces else [];ev.to_mesh_clear();return world,faces
 for row in range(ref['rows']):
  rig.location=(0,0,0);scene.frame_set(row);bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get();floor=min(vertices(o,deps)[0][:,2].min() for o in parts);offset=target_floor-float(floor);sway=ref.get('pose_xy_offsets',[[0,0]]*ref['rows'])[row]
  if actor_name:
   actor=rig.matrix_world@rig.pose.bones[actor_name].head;center=rig.matrix_world@rig.pose.bones['pelvis'].head;gain=ref.get('root_motion_scale',0)*ref.get('root_motion_return',[1]*ref['rows'])[row];sway=[center.x-actor.x+actor_initial.x-initial.x+(actor.x-actor_initial.x)*gain,center.y-actor.y+actor_initial.y-initial.y+(actor.y-actor_initial.y)*gain]
   if drive is not None:sway=[center.x-actor.x+actor_initial.x-initial.x+drive[row][0],center.y-actor.y+actor_initial.y-initial.y+drive[row][1]]
  floors.append([sway[0],sway[1],offset]);pelvis=rig.matrix_world@rig.pose.bones['pelvis'].head;rig.location=(initial.x-pelvis.x+sway[0],initial.y-pelvis.y+sway[1],offset);bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get()
  if actor_name:root_positions.append(list(rig.matrix_world@rig.pose.bones[actor_name].head))
  objects=parts+equipment;chunks=[vertices(o,deps)[0] for o in objects];starts=np.cumsum([0]+[len(p) for p in chunks]);world_body=np.concatenate(chunks);world_shadow=world_body.copy()
  for d in range(8):
   a=-d*math.pi/4;c,s=math.cos(a),math.sin(a);rotation=np.array([[c,-s,0],[s,c,0],[0,0,1]])
   for kind,xyz in [('body',world_body),('shadow',world_shadow)]:
    p=xyz@rotation.T
    if kind=='shadow':h=np.maximum(p[:,2],0);p[:,0]-=.5*h;p[:,1]+=2/3*h;p[:,2]=.002
    xy=np.column_stack((ground[0]+density*p[:,0],ground[1]-density*(.5*p[:,1]+math.sqrt(.75)*p[:,2])));lo=xy.min(0);hi=xy.max(0);margin=float(min(*lo,width-hi[0],height-hi[1]));owner=objects[int(np.searchsorted(starts,int(np.argmin(xy[:,0])),side='right')-1)];bounds.append({'row':row,'direction':d,'kind':kind,'margin':margin,'leftmost_object':owner.get('d1r_asset',owner.name),'bounds':[*lo.tolist(),*hi.tolist()]})
  swords=[o for o in equipment if o.get('d1r_asset')=='sword_base00.glb']
  if swords and min(b['margin'] for b in bounds)>3:
   points=[];polygons=[]
   for o in parts:
    p,f=vertices(o,deps,True);base=len(points);points.extend(Vector(v) for v in p);polygons.extend(tuple(base+i for i in face) for face in f)
   tree=BVHTree.FromPolygons(points,polygons);sword=swords[0];start=sword.matrix_world@Vector((0,-.04,0));end=sword.matrix_world@Vector((0,-1.03,0));ray=end-start;hit=tree.ray_cast(start,ray.normalized(),ray.length)
   if hit[0] is not None:collisions.append({'row':row,'point':list(hit[0])})
 minimum_body=min(b['margin'] for b in bounds if b['kind']=='body');minimum_shadow=min(b['margin'] for b in bounds if b['kind']=='shadow');safe=minimum_body>3 and minimum_shadow>3 and not collisions
 weights=json.loads(Path(model).with_suffix('.motion.json').read_text())['recipe'].get('idle_weights',[0]*ref['rows']);moving_shadow=min((b['margin'] for b in bounds if b['kind']=='shadow' and weights[b['row']]<1),default=minimum_shadow);safe=safe and moving_shadow>7
 result={'motion_root_bone':actor_name,'native_root_drive_offsets':drive,'root_world_positions':root_positions,'safe':safe,'minimum_body_margin':minimum_body,'minimum_shadow_margin_before_blur':minimum_shadow,'body_intersections':collisions,'worst_cells':sorted(bounds,key=lambda b:b['margin'])[:8],'pose_offsets':floors}
 if ref.get('capture_bounds'):result['cell_bounds']=bounds
 return result

def run(plan_file):
 plan=json.loads(Path(plan_file).read_text());progress=Path(plan['work'])/'preflight-progress.json';results=json.loads(progress.read_text()) if progress.exists() else [];results=[r for r in results if r['safe']]
 for motion in plan['motions']:
  if any(r['motion']==motion['name'] for r in results):continue
  jobs=[j for j in plan['jobs'] if j['motion']==motion['name']];assert jobs;recipe=Path(motion['recipe']);spec=json.loads(recipe.read_text());attempts=[];result=None
  # Prefer the complete source gesture. Smaller excursions stay joint-based;
  # they never shrink the model, equipment or ground shadow.
  candidates=[(1,1,0),(1,1,.025),(1,1,.05),(1,1,.075),(.9,1,.05),(.8,1,.05),(.7,1,.05),(.6,1,.05),(.5,1,.05),(.4,1,.05),(.35,.9,.05),(.35,.8,.05),(.25,.7,.05)]
  equipped=json.loads(Path(jobs[0]['reference']).read_text()).get('equipment',[]);sides=['R' if Path(e['path']).name.startswith('sword') else 'L' for e in equipped]
  if 'L' in sides:candidates=candidates[:4]+[(1,1,{'L':.10,'R':0}),(1,1,{'L':.15,'R':0}),(1,1,{'L':.20,'R':0})]+candidates[4:]
  if motion['name'].endswith('-attack') and 'R' in sides:candidates=candidates[:4]+[(1,1,{'R':.15,'L':.10}),(1,1,{'R':.25,'L':.15}),(1,1,{'R':.35,'L':.15}),(.8,1,{'R':.25,'L':.15}),(.6,1,{'R':.25,'L':.15})]+candidates[4:]
  if motion['name'].endswith('-attack') and 'R' in sides:candidates += [(.2,1,.05),(.15,1,.05),(.1,1,.05)]
  if motion['name'].endswith('-hit'):candidates=[(1,.5,.1),(1,.4,.1)]+candidates
  if motion['name'].endswith('-block'):candidates=[(.25,1,.15),(.25,1,.2),(.2,1,.15),(.15,1,.1)]+candidates+[(.2,1,.05),(.15,1,.05),(.1,1,.05),(.05,1,.05)]
  candidates=[(a,m,t,1) for a,m,t in candidates]
  if motion['name'].endswith('-attack') and 'R' in sides:candidates=[(.2,1,.05,1),(.15,1,.05,1),(.1,1,.05,1)]+[(1,1,{'R':t,'L':.1},w) for w in [0,.35,.65] for t in [.05,.15,.25]]+candidates
  if spec.get('preserve_attack_motion'):candidates=[(spec.get('arm_gain',1),spec.get('motion_gain',1),spec.get('arm_tuck',{}),spec.get('wrist_gain',{}).get('R',1))]
  for arm_gain,motion_gain,tuck,wrist in candidates:
   if not spec.get('preserve_attack_motion'):
    spec['wrist_gain']={'R':wrist} if 'R' in sides else {}
    spec.update(arm_gain=arm_gain,motion_gain=motion_gain,arm_tuck={side:(tuck.get(side,0) if isinstance(tuck,dict) else tuck) for side in sides})
   recipe.write_text(json.dumps(spec,indent=2));author(recipe,motion['model']);result=check(motion['model'],jobs[0]['reference']);attempts.append({'arm_gain':arm_gain,'motion_gain':motion_gain,'wrist_gain':spec.get('wrist_gain',{}),'arm_tuck':spec.get('arm_tuck',{}),**{k:v for k,v in result.items() if k!='pose_offsets'}})
   if result['safe']:break
  record={'motion':motion['name'],'safe':result['safe'],'arm_gain':spec['arm_gain'],'motion_gain':spec['motion_gain'],'arm_tuck':spec.get('arm_tuck',{}),'attempts':attempts};results.append(record)
  (Path(plan['work'])/'preflight-progress.json').write_text(json.dumps(results,indent=2))
  if not result['safe']:
   print('PREFLIGHT NEEDS REFINEMENT',motion['name'],flush=True);continue
  for job in jobs:
   path=Path(job['reference']);ref=json.loads(path.read_text());ref['pose_offsets']=result['pose_offsets'];path.write_text(json.dumps(ref,indent=2));(Path(job['root'])/'preflight.json').write_text(json.dumps(record,indent=2))
  print('PREFLIGHT OK',motion['name'],spec['arm_gain'],spec['motion_gain'],flush=True);gc.collect()
 (Path(plan['work'])/'preflight.json').write_text(json.dumps(results,indent=2))
 failed=[r['motion'] for r in results if not r['safe']]
 if failed:raise RuntimeError('Motions still requiring refinement: '+', '.join(failed))
 print('All equipped motions prepared and checked',flush=True)

if __name__=='__main__':run(sys.argv[sys.argv.index('--')+1])
