"""Find a minimal rigid grip-pivot rotation, without changing arms or animation."""
import bpy,json,sys,math,copy,gc
from pathlib import Path
import numpy as np
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from paladin_equipment import attach_equipment
file=Path(sys.argv[sys.argv.index('--')+1]).resolve();plan=json.loads(file.read_text());jobs={j['sheet']:j for j in plan['jobs']};proof_path=Path(plan['work'])/'grip-clearance-fit.json';proof=json.loads(proof_path.read_text()) if proof_path.exists() else []
for armor in 'lm':
 for weapon in 'bdhu':
  name='w'+armor+weapon+'fm';job=jobs[name];ref=json.loads(Path(job['reference']).read_text())
  bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=job['model']);rig=next(o for o in scene.objects if o.type=='ARMATURE');gear=attach_equipment(rig,ref['equipment'])
  asset='wlbas-bow.glb' if weapon=='b' else 'Shield_S15_Warrior_Red.glb'
  target=next(o for o in gear if o.get('d1r_asset')==asset);setting=next(s for s in ref['equipment'] if Path(s['path']).name==asset)
  if setting.get('cast_head_clearance'):continue
  bone=target.parent_bone;local=Matrix.Translation((0,rig.data.bones[bone].length,0))@target.matrix_basis
  pivot=Vector(setting['closed_palm_grip']) if weapon=='b' else local@Vector(setting['grip'])
  points=[];faces=[]
  for obj in gear:
   if obj.get('d1r_asset')!=asset:continue
   other=Matrix.Translation((0,rig.data.bones[obj.parent_bone].length,0))@obj.matrix_basis
   assert max(abs(other[i][j]-local[i][j]) for i in range(4) for j in range(4))<1e-5,'Equipment pieces must share a grip transform'
   ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh()
   start=len(points);points.extend(tuple(v.co) for v in mesh.vertices);faces.extend(tuple(start+i for i in p.vertices) for p in mesh.polygons);ev.to_mesh_clear()
  verts=np.asarray(points)
  heads=[o for o in scene.objects if o.type=='MESH' and o.data.materials and any(t in o.data.materials[0].name for t in ('P00_HED','Helmet dark gray metal'))]
  snapshots=[]
  # Include every integer source frame, not just the eventual native sheet samples.
  for frame in range(math.floor(rig.animation_data.action.frame_range[0]),math.ceil(rig.animation_data.action.frame_range[1])+1):
   scene.frame_set(frame);bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get();headparts=[]
   for o in heads:
    ev=o.evaluated_get(deps);me=ev.to_mesh();v=[ev.matrix_world@p.co for p in me.vertices];f=[tuple(p.vertices) for p in me.polygons];a=np.asarray(v);headparts.append((BVHTree.FromPolygons(v,f),a.min(0),a.max(0)));ev.to_mesh_clear()
   snapshots.append((frame,np.asarray(rig.matrix_world@rig.pose.bones[bone].matrix),headparts))
  def clear(candidate):
   c=np.asarray(candidate)
   for frame,bm,hs in snapshots:
    matrix=bm@c;v=verts@matrix[:3,:3].T+matrix[:3,3];lo=v.min(0);hi=v.max(0);tree=None
    for head,hl,hh in hs:
     if np.any(hi<hl) or np.any(lo>hh):continue
     if tree is None:tree=BVHTree.FromPolygons([Vector(p) for p in v],faces)
     if tree.overlap(head):return False
   return True
  chosen=None
  if clear(local):chosen=(0,'X',local)
  else:
   for degrees in range(2,62,2):
    for axis in ('X','Y','Z'):
     for sign in (-1,1):
      rotation=Matrix.Rotation(math.radians(degrees*sign),4,axis);candidate=Matrix.Translation(pivot)@rotation@Matrix.Translation(-pivot)@local
      if clear(candidate):chosen=(degrees*sign,axis,candidate);break
     if chosen:break
    if chosen:break
  assert chosen,('No rigid grip-preserving head clearance found',name)
  angle,axis,candidate=chosen
  if angle:
   grip=Vector(setting.get('grip',setting.get('closed_palm_grip',[0,0,0])))
   assert ((candidate@grip)-(local@grip)).length<1e-5
   setting['local_transform']=[list(r) for r in candidate];setting['cast_head_clearance']={'axis':axis,'degrees':angle,'pivot':list(pivot),'arm_motion_unchanged':True,'all_source_frames_checked':len(snapshots)}
   for spell in ('fm','lm','qm'):
    rpath=Path(jobs['w'+armor+weapon+spell]['reference']);r=json.loads(rpath.read_text())
    r['equipment']=[copy.deepcopy(setting) if Path(s['path']).name==asset else s for s in r['equipment']];rpath.write_text(json.dumps(r,indent=2))
  proof=[r for r in proof if r['sheet_family']!='w'+armor+weapon]
  proof.append({'sheet_family':'w'+armor+weapon,'asset':asset,'angle':angle,'axis':axis,'pivot':list(pivot),'source_frames_checked':len(snapshots),'head_contacts':0})
  (Path(plan['work'])/'grip-clearance-fit.json').write_text(json.dumps(proof,indent=2));print('CAST_GRIP_FIT',name,angle,axis,flush=True);gc.collect()
