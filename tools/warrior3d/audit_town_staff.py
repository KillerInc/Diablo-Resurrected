"""Blender --python SCRIPT -- TOWN_STAFF_PLAN
Verify held-staff grips, wrist, floor clearance and original gait channels.
"""
import bpy,json,sys,math,numpy as np
from pathlib import Path
from mathutils import Vector
tools=Path(__file__).resolve().parent;sys.path.insert(0,str(tools));from paladin_equipment import attach_equipment;from merge_paladin_walk import read;from author_equipped_motion import tracks
file=Path(sys.argv[sys.argv.index('--')+1]);work=file.resolve().parent;plan=json.loads(file.read_text());reports=[]
for j in plan['jobs']:
 ref=json.loads(Path(j['reference']).read_text());fit=json.loads((work/(j['sheet']+'-fit.json')).read_text());old,ob=read(fit['original_town_model']);new,nb=read(j['model']);before=tracks(old,ob);after=tracks(new,nb);names={n.get('name'):i for i,n in enumerate(new['nodes'])}
 def branch(i):return {i}|set().union(*(branch(c) for c in new['nodes'][i].get('children',[])))
 allowed=branch(names['hand.L'])-{names['weapon.L']}|{names['forearm.L'],names['upperArm.L']};other=0
 for key,(_,v,_) in after.items():
  i,path=key
  if i in allowed:continue
  base=before[key][1] if key in before else np.tile(np.array(old['nodes'][i].get(path,{'translation':[0,0,0],'rotation':[0,0,0,1],'scale':[1,1,1]}[path])),(ref['rows'],1));e=np.max(np.abs(v-base),axis=1)
  if path=='rotation':e=np.minimum(e,np.max(np.abs(v+base),axis=1))
  other=max(other,float(e.max()))
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=j['model']);rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');staff=attach_equipment(rig,ref['equipment'])[0];rest=(rig.data.bones['forearm.L'].matrix_local.inverted()@rig.data.bones['hand.L'].matrix_local).to_quaternion();poses=[]
 for row in range(ref['rows']):
  bpy.context.scene.frame_set(row);bpy.context.view_layer.update();h=rig.matrix_world@rig.pose.bones['hand.L'].matrix;p=h@Vector((-.04,.065,0));axis=(h.to_3x3()@Vector((0,0,1))).normalized();expected=Vector(fit['mounts'][row]['shaft_axis']);relative=(rig.pose.bones['forearm.L'].matrix.inverted()@rig.pose.bones['hand.L'].matrix).to_quaternion();angle=math.degrees((relative@rest.inverted()).angle);angle=min(angle,360-angle);ev=staff.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();points=[ev.matrix_world@v.co for v in m.vertices];ev.to_mesh_clear();poses.append({'row':row,'nearest_staff_vertex_metres':min((v-p).length for v in points),'axis_error_degrees':math.degrees(math.acos(min(1,abs(axis.dot(expected))))),'wrist_relative_bind_degrees':angle,'staff_minimum_height':min(v.z for v in points)})
 r={'sheet':j['sheet'],'maximum_other_channel_error':other,'short_stride_and_all_non_left_arm_channels_preserved':other<1e-5,'maximum_grip_vertex_distance':max(p['nearest_staff_vertex_metres'] for p in poses),'maximum_axis_error_degrees':max(p['axis_error_degrees'] for p in poses),'maximum_wrist_relative_bind_degrees':max(p['wrist_relative_bind_degrees'] for p in poses),'minimum_staff_ground_height':min(p['staff_minimum_height'] for p in poses),'poses':poses};reports.append(r);print(json.dumps({k:v for k,v in r.items() if k!='poses'}),flush=True);assert other<1e-5 and r['maximum_grip_vertex_distance']<.06 and r['maximum_axis_error_degrees']<.1 and r['maximum_wrist_relative_bind_degrees']<26 and r['minimum_staff_ground_height']>.02
(work/'town-grip-audit.json').write_text(json.dumps(reports,indent=2))
