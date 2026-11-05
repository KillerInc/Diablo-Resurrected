"""Blender --python SCRIPT -- APPROVED_PREVIEW_PLAN ALIGNED_PLAN
Check frame-11 impact identity, rigid exact-key staff geometry, grips and wrist.
Bind the report to final derived inputs for guarded installation.
"""
import bpy,json,math,sys,hashlib,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.kdtree import KDTree
tools=Path(__file__).resolve().parent;sys.path.insert(0,str(tools));from paladin_equipment import attach_equipment;from merge_paladin_walk import read;from author_equipped_motion import tracks
args=sys.argv[sys.argv.index('--')+1:];original=json.loads(Path(args[0]).read_text());plan_file=Path(args[1]);work=plan_file.resolve().parent;plan=json.loads(plan_file.read_text());timing=json.loads((work/'timing-fit.json').read_text());mapping=timing['frame_map'];sets=[]
for p in [original,plan]:
 j=p['jobs'][0];ref=json.loads(Path(j['reference']).read_text());bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=j['model']);rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');staff=attach_equipment(rig,ref['equipment'])[0];rest=(rig.data.bones['forearm.R'].matrix_local.inverted()@rig.data.bones['hand.R'].matrix_local).to_quaternion();poses=[]
 for row in range(16):
  bpy.context.scene.frame_set(row);bpy.context.view_layer.update();ev=staff.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();v=[ev.matrix_world@x.co for x in m.vertices];ev.to_mesh_clear();R=rig.matrix_world@rig.pose.bones['hand.R'].matrix;L=rig.matrix_world@rig.pose.bones['hand.L'].matrix;r=R@Vector((.04,.065,0));l=L@Vector((-.04,.065,0));axis=(l-r).normalized();rel=(rig.pose.bones['forearm.R'].matrix.inverted()@rig.pose.bones['hand.R'].matrix).to_quaternion();angle=math.degrees((rel@rest.inverted()).angle);axes={s:math.degrees(math.acos(min(1,abs((H.to_3x3()@Vector((0,0,1))).normalized().dot(axis))))) for s,H in [('R',R),('L',L)]};poses.append({'vertices':v,'right_wrist':min(angle,360-angle),'axes':axes,'grip_distances':{'R':min((p-r).length for p in v),'L':min((p-l).length for p in v)}})
 sets.append(poses)
maximum=0;checks=[]
for row,t in enumerate(mapping):
 if t!=int(t):continue
 reference=sets[0][int(t)]['vertices'];tree=KDTree(len(reference))
 for i,p in enumerate(reference):tree.insert(p,i)
 tree.balance();error=max(tree.find(p)[2] for p in sets[1][row]['vertices']);maximum=max(maximum,error);checks.append({'game_frame':row+1,'approved_frame':int(t)+1,'maximum_staff_world_vertex_error':error})
a,ab=read(original['jobs'][0]['model']);b,bb=read(plan['jobs'][0]['model']);ta=tracks(a,ab);tb=tracks(b,bb);pose_error=max(float(np.max(np.abs(tb[key][1][10]-v[1][3]))) for key,v in ta.items());fields=['meshes','nodes','skins','images','materials'];assert all(a.get(k)==b.get(k) for k in fields)
report={'visual_hit_frame':11,'approved_impact_frame':4,'engine_impact_frame':11,'frame_map':mapping,'maximum_exact_pose_error':pose_error,'maximum_exact_staff_vertex_error':maximum,'maximum_right_wrist_degrees':max(r['right_wrist'] for r in sets[1]),'maximum_grip_axis_error_degrees':max(r['axes'][s] for r in sets[1] for s in ['R','L']),'maximum_grip_vertex_distance':max(r['grip_distances'][s] for r in sets[1] for s in ['R','L']),'geometry_materials_nodes_bindings_unchanged':True,'derived_body_sha256':hashlib.sha256(Path(plan['jobs'][0]['model']).read_bytes()).hexdigest().upper(),'derived_staff_sha256':hashlib.sha256(Path(json.loads(Path(plan['jobs'][0]['reference']).read_text())['equipment'][0]['path']).read_bytes()).hexdigest().upper(),'exact_keys':checks};(work/'aligned-verification.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='exact_keys'}));assert pose_error<1e-5 and maximum<1e-5 and report['maximum_right_wrist_degrees']<26 and report['maximum_grip_axis_error_degrees']<6 and report['maximum_grip_vertex_distance']<.06
