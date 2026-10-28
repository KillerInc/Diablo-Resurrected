"""Blender --python SCRIPT -- CLOSED_GRIP_PLAN.json
Check the actual wooden cross-section against the closed-palm opening.
String clearance includes gloves and gauntlets; wood/glove grip contact is allowed.
"""
import bpy,sys,json,math,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent));from paladin_equipment import attach_equipment
from preflight_equipped_sets import opaque
from merge_paladin_walk import read
from author_equipped_motion import tracks
import numpy as np
file=Path(sys.argv[sys.argv.index('--')+1]);w=file.resolve().parent;p=json.loads(file.read_text());reports=[]
def geom(o):
 e=o.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();m.calc_loop_triangles();v=[e.matrix_world@a.co for a in m.vertices];t=[tuple(a.vertices) for a in m.loop_triangles];e.to_mesh_clear();return v,t
for j in p['jobs']:
 fit=json.loads((w/(j['sheet']+'-fit.json')).read_text());original=fit.get('original_idle_model',fit.get('original_town_model'));og,ob=read(original);ng,nb=read(j['model']);ot=tracks(og,ob);nt=tracks(ng,nb);names={n.get('name'):i for i,n in enumerate(og['nodes'])}
 def branch(i):return {i}|set().union(*(branch(c) for c in og['nodes'][i].get('children',[])))
 allowed=branch(names['upperArm.L']);channel_error=0
 for key,(times,values,method) in nt.items():
  if key[0] in allowed:continue
  old=np.column_stack([np.interp(times,ot[key][0],ot[key][1][:,k]) for k in range(values.shape[1])]) if key in ot else np.broadcast_to(np.asarray(og['nodes'][key[0]].get(key[1],{'translation':[0,0,0],'rotation':[0,0,0,1],'scale':[1,1,1]}[key[1]])),values.shape);channel_error=max(channel_error,float(np.max(np.abs(old-values))))
 assert channel_error<1e-5 and nb[:len(ob)]==ob
 for field in ['meshes','materials','images','skins']:assert ng[field]==og[field]
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=j['model']);rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');r=json.loads(Path(j['reference']).read_text());gear=attach_equipment(rig,[r['equipment'][0]]);wood=next(o for o in gear if 'string' not in o.name.lower());cord=next(o for o in gear if 'string' in o.name.lower());body=[o for o in bpy.data.objects if opaque(o) and o not in gear];contacts=[];centres=[];inside=[];arm_gaps=[]
 for row,time in enumerate(r['source_frames']):
  bpy.context.scene.frame_set(time);bpy.context.view_layer.update();hand=rig.matrix_world@rig.pose.bones['hand.L'].matrix;P=hand@Vector((-.04,.065,0));axis=(hand.to_3x3()@Vector((0,0,1))).normalized();v,_=geom(wood);near=[a-P for a in v if abs((a-P).dot(axis))<.03 and ((a-P)-axis*(a-P).dot(axis)).length<.06];x=Vector((-1,0,0));x=(x-axis*x.dot(axis)).normalized();z=x.cross(axis).normalized();error=math.hypot((min(a.dot(x) for a in near)+max(a.dot(x) for a in near))/2,(min(a.dot(z) for a in near)+max(a.dot(z) for a in near))/2);centres.append(error);cv,_=geom(cord);inside.append(min((a-P).dot(x) for a in cv))
  if p.get('bow_string_clearance_revision'):
   glove=next(o for o in body if 'base01_GLV' in o.data.materials[0].name);gv,gt=geom(glove);gtree=BVHTree.FromPolygons(gv,gt,all_triangles=True);C=sum(cv,Vector())/len(cv);lo=min((a-C).dot(axis) for a in cv);hi=max((a-C).dot(axis) for a in cv);probe=[(gtree.find_nearest(C+axis*(lo+(hi-lo)*k/180))[3],lo+(hi-lo)*k/180) for k in range(181)];best,u=min(probe);span=(hi-lo)/180
   for k in range(81):best=min(best,gtree.find_nearest(C+axis*(u-span+2*span*k/80))[3])
   arm_gaps.append(best-.002)
  for o in gear:
   v,t=geom(o);tree=BVHTree.FromPolygons(v,t,all_triangles=True)
   for part in body:
    if o==wood and 'base01_GLV' in part.data.materials[0].name:continue
    bv,bt=geom(part);hits=tree.overlap(BVHTree.FromPolygons(bv,bt,all_triangles=True))
    if hits:contacts.append({'row':row,'equipment':o.name,'part':part.name,'hits':len(hits)})
 reports.append({'sheet':j['sheet'],'rows':r['rows'],'non_left_arm_channel_error':channel_error,'original_art_buffers_preserved':True,'bow_sha256':hashlib.sha256(Path(r['equipment'][0]['path']).read_bytes()).hexdigest().upper(),'body_sha256':hashlib.sha256(Path(j['model']).read_bytes()).hexdigest().upper(),'max_geometric_grip_centre_error':max(centres),'minimum_string_inward_metres':min(inside),'body_contacts':contacts});
 if arm_gaps:reports[-1].update(string_arm_gap_metres=arm_gaps,minimum_string_arm_gap_metres=min(arm_gaps),maximum_string_arm_gap_metres=max(arm_gaps))
 (w/'idle-hold-audit.json').write_text(json.dumps(reports,indent=2));print(j['sheet'],max(centres),min(inside),contacts,flush=True)


assert len(reports)==2 and all(not r["body_contacts"] and r["max_geometric_grip_centre_error"]<.005 and r["minimum_string_inward_metres"]>.04 for r in reports)

if p.get("bow_string_clearance_revision"):assert all(r["minimum_string_arm_gap_metres"]>=.0015 and r["maximum_string_arm_gap_metres"]<=.012 for r in reports)
