"""Blender --python SCRIPT -- APPROVED_PREVIEW_PLAN STAFF_PLAN NEW_WORK
Retime the approved Sorcerer attack so approved pose 4 lands at game frame 11.
Preserve body artwork and rigid staff scale; fit the shaft between both grips.
Private input models and animation data are never included in source control.
"""
import bpy,json,sys,math,copy,shutil,hashlib,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
tools=Path(__file__).resolve().parent;sys.path.insert(0,str(tools));from author_equipped_motion import author;from paladin_equipment import attach_equipment;from bake_bow_equipment import keys
args=sys.argv[sys.argv.index('--')+1:];approved_file=Path(args[0]);approved=approved_file.resolve().parent;template=json.loads(Path(args[1]).read_text());previous=Path(template['previous']);oldplan=json.loads(approved_file.read_text());oldjob=oldplan['jobs'][0];oldref=json.loads(Path(oldjob['reference']).read_text());work=Path(args[2]).resolve();assert not work.exists();work.mkdir(parents=True);times=[0,.3,.6,.9,1.2,1.5,1.8,2.1,2.4,2.7,3,4,6,9,12,15];recipe={'name':'Approved Sorcerer staff, hit aligned to frame 11','source':oldjob['model'],'frames':times,'arms':[]};rp=work/'aligned-recipe.json';rp.write_text(json.dumps(recipe,indent=2));model=work/'approved-body.glb';author(rp,model)
bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=oldjob['model']);rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');staff=attach_equipment(rig,oldref['equipment'])[0];worlds=[];right=[];left=[]
for row in range(16):
 scene.frame_set(row);bpy.context.view_layer.update();ev=staff.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();worlds.append(np.array([list(ev.matrix_world@v.co) for v in m.vertices]));ev.to_mesh_clear();right.append(rig.matrix_world@rig.pose.bones['hand.R'].matrix@Vector((.04,.065,0)));left.append(rig.matrix_world@rig.pose.bones['hand.L'].matrix@Vector((-.04,.065,0)))
reference=worlds[0];origin=reference.mean(0);centered=reference-origin;transforms=[];max_error=0
for points in worlds:
 c=points.mean(0);u,s,v=np.linalg.svd(centered.T@(points-c));rotation=v.T@u.T
 if np.linalg.det(rotation)<0:v[-1]*=-1;rotation=v.T@u.T
 translation=c-rotation@origin;M=Matrix(rotation).to_4x4();M.translation=Vector(translation);transforms.append(M);max_error=max(max_error,float(np.max(np.abs(reference@rotation.T+translation-points))))
assert max_error<1e-5,max_error
canon_right=[M.inverted()@p for M,p in zip(transforms,right)];canon_axis=(left[0]-right[0]).normalized();bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=str(model));rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');positions=[];rows=[]
for row,time in enumerate(times):
 scene.frame_set(row);bpy.context.view_layer.update();R=rig.matrix_world@rig.pose.bones['hand.R'].matrix;L=rig.matrix_world@rig.pose.bones['hand.L'].matrix;r=R@Vector((.04,.065,0));l=L@Vector((-.04,.065,0));lo=int(time);hi=min(lo+1,15);t=time-lo;q=transforms[lo].to_quaternion().slerp(transforms[hi].to_quaternion(),t);axis=(l-r).normalized();q=(q@canon_axis).rotation_difference(axis)@q;grip=canon_right[lo].lerp(canon_right[hi],t);pose=q.to_matrix().to_4x4();pose.translation=r-q@grip;inverse=R.inverted();world=[pose@Vector(p) for p in reference];positions.append([inverse@p for p in world]);errors={}
 for side,H in [('R',R),('L',L)]:
  normal=(H.to_3x3()@Vector((0,0,1))).normalized();errors[side]=math.degrees(math.acos(min(1,abs(normal.dot(axis)))))
 rows.append({'row':row,'approved_frame':time,'grip_axis_errors_degrees':errors})
before=set(bpy.data.objects);bpy.ops.import_scene.gltf(filepath=oldref['equipment'][0]['path']);o=next(o for o in set(bpy.data.objects)-before if o.type=='MESH');assert len(o.data.vertices)==len(reference);o.shape_key_clear();o.animation_data_clear();keys(o,positions);o.parent=None;o.matrix_world=Matrix.Identity(4);bpy.ops.object.select_all(action='DESELECT');o.select_set(True);scene.frame_start=0;scene.frame_end=15;scene.frame_set(0);dest=work/'approved-staff.glb';bpy.ops.export_scene.gltf(filepath=str(dest),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='SCENE',export_anim_scene_split_object=False,export_frame_range=True,export_force_sampling=True)
plan=copy.deepcopy(template);donor=copy.deepcopy(next(j for j in template['jobs'] if j['sheet']=='wltat'));plan.update(attack_only=True,approved_profile='sorcerer-natural-right-30cm',selected_native_clip='sorM_STF_attk_weaponAttack',engine_impact_frame=11,starting_custom_manifest=json.loads((previous/'paladin-vanilla-dimensions/install-manifest.json').read_text()),jobs=[donor],motions=[{'name':donor['motion']}],copies=[],inventory={'wlt':{'wltat':copy.deepcopy(template['inventory']['wlt']['wltat'])}});plan.update(work=str(work),timing_choice='aligned_hit',approved_timing_preserved=False,approved_frame_map=times,visual_thrust_frame=11);job=plan['jobs'][0];out=work/'jobs/wltat';out.mkdir(parents=True);ref=json.loads(Path(job['reference']).read_text());ref.update(source_frames=list(range(16)),render_directions=list(range(8)),preview_contact_row=10,preview_caption='Approved Sorcerer staff | hit frame 11 / natural wrist');ref['equipment'][0]['path']=str(dest)
for key in ['pose_offsets','direction_pose_offsets']:ref.pop(key,None)
reference_file=out/'reference.json';reference_file.write_text(json.dumps(ref,indent=2));job.update(model=str(model),root=str(out),reference=str(reference_file));(work/'plan.json').write_text(json.dumps(plan,indent=2))
inputs={}
for role,path in [('body',Path(oldjob['model'])),('staff',Path(oldref['equipment'][0]['path']))]:
 dest=work/('source-approved-'+role+'.glb');shutil.copy2(path,dest);inputs[role]={'approved_path':str(path),'path':str(dest),'sha256':hashlib.sha256(path.read_bytes()).hexdigest().upper()}
(work/'approved-inputs.json').write_text(json.dumps(inputs,indent=2))
for name in ['both-grip-path-audit.json','wrist-comparison-audit.json','natural-arm-fit.json']:shutil.copy2(approved/name,work/name)
report={'frame_map':times,'source_rigidity_error':max_error,'maximum_grip_axis_error_degrees':max(r['grip_axis_errors_degrees'][s] for r in rows for s in ['R','L']),'rows':rows,'whole_staff_scale_preserved':True};(work/'timing-fit.json').write_text(json.dumps(report,indent=2));print('ALIGNMENT',json.dumps({k:v for k,v in report.items() if k!='rows'}),flush=True)
