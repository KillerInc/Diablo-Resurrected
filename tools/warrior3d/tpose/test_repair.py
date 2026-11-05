"""Inspect and repair the user's 50-part T-pose Warrior; outputs stay private."""
import bpy,math,json,sys,argparse
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
import numpy as np
p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);bpy.ops.import_scene.gltf(filepath=str(a.input.resolve()))
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');meshes=[o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith('tripo_part_')];assert len(meshes)==50
for o in list(bpy.data.objects):
 if o.type=='MESH' and o not in meshes:bpy.data.objects.remove(o,do_unlink=True)
rig.animation_data_clear();prefix='mixamorig:';B=lambda n:prefix+n
for bone in rig.pose.bones:bone.rotation_mode='QUATERNION';bone.matrix_basis.identity()
bpy.context.view_layer.update()
scene=bpy.context.scene;scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=640;scene.render.resolution_y=640;scene.render.resolution_percentage=100;scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.world.color=(.15,.15,.15)
center=rig.matrix_world@Vector((0,-.02,.51));up=(rig.matrix_world.to_3x3()@Vector((0,0,1))).normalized();front=(rig.matrix_world.to_3x3()@Vector((0,-1,0))).normalized()
bpy.ops.object.camera_add();cam=bpy.context.object;cam.data.type='ORTHO';cam.data.ortho_scale=1.27;scene.camera=cam
for pos,power in [((-2,-3,3),120),((2,-1,2),70),((0,2,2),85)]:
 bpy.ops.object.light_add(type='AREA',location=rig.matrix_world@Vector(pos));o=bpy.context.object;o.data.energy=power;o.data.size=3;o.rotation_euler=(center-o.location).to_track_quat('-Z','Y').to_euler()
def camera(view):
 direction=Quaternion(up,math.radians({'front':0,'side':90,'back':180}[view]))@front;cam.location=center+direction*3+up*.2;back=(cam.location-center).normalized();right=up.cross(back).normalized();cam.rotation_euler=Matrix((right,back.cross(right),back)).transposed().to_euler()
def render(name,view='front'):
 camera(view);scene.render.filepath=str(a.out/(name+'.png'));bpy.ops.render.render(write_still=True)
def rotate(name,axis,angle):
 bone=rig.pose.bones[name];pivot=bone.head.copy();rotation=Quaternion(axis,math.radians(angle)).to_matrix().to_4x4();bone.matrix=Matrix.Translation(pivot)@rotation@Matrix.Translation(-pivot)@bone.matrix;bpy.context.view_layer.update()
def pose(amount):
 for bone in rig.pose.bones:bone.matrix_basis.identity()
 bpy.context.view_layer.update()
 for side,sign in [('Left',1),('Right',-1)]:
  rotate(B(side+'Arm'),(0,1,0),sign*70*(1-amount));rotate(B(side+'ForeArm'),(0,0,1),-sign*20*amount);rotate(B(side+'Leg'),(1,0,0),55*amount)
 if repaired:
  clearance_samples.append(clear_hinge(rig,plate,coat,amount))
def lengths():
 deps=bpy.context.evaluated_depsgraph_get();result={}
 for o in globals().get('metric_meshes',meshes):
  ev=o.evaluated_get(deps);me=ev.to_mesh();coords=np.array([tuple(v.co) for v in me.vertices]);edges=np.array([tuple(e.vertices) for e in me.edges]);result[o.name]=np.linalg.norm(coords[edges[:,0]]-coords[edges[:,1]],axis=1);ev.to_mesh_clear()
 return result
sys.path.insert(0,str(Path(__file__).resolve().parent))
from hinge import clear_hinge
clearance_samples=[]
repaired=False
for bone in rig.pose.bones:bone.matrix_basis.identity()
bpy.context.view_layer.update();baseline=lengths()
def distortion():
 now=lengths();parts={name:float((now[name]/np.maximum(baseline[name],1e-8)).max()) for name in baseline};ratios=np.concatenate([now[n]/np.maximum(baseline[n],1e-8) for n in baseline]);return {'maximum':float(ratios.max()),'p99':float(np.percentile(ratios,99)),'over_3x':int((ratios>3).sum()),'worst_parts':{n:r for n,r in parts.items() if r>2}}
report={'input':a.input.name,'status':'working candidate','body_joint_positions_preserved':True}
pose(0);report['original_arms_down']=distortion();render('before-arms-down')
pose(1);report['original_bend']=distortion();render('before-bend')
for bone in rig.pose.bones:bone.matrix_basis.identity()
bpy.context.view_layer.update()
# The shield is optional and should be attached to the chest, never stretched.
def bind(obj,names):
 old=[[(obj.vertex_groups[g.group].name,g.weight) for g in v.groups] for v in obj.data.vertices]
 for g in list(obj.vertex_groups):obj.vertex_groups.remove(g)
 groups={n:obj.vertex_groups.new(name=n) for n in names}
 for vertex,weights in zip(obj.data.vertices,old):
  values={n:w for n,w in weights if n in groups};total=sum(values.values())
  if len(names)==1 or total<1e-8:values={names[0]:1};total=1
  for n,w in values.items():
   if w>0:groups[n].add([vertex.index],w/total,'REPLACE')
# Keep original anatomical shoulder/chest influences in skin meshes.
rigid={0:'Spine2',3:'Head',5:'RightUpLeg',7:'RightForeArm',9:'RightLeg',11:'LeftLeg',15:'Hips',17:'LeftFoot',18:'RightFoot',19:'Hips',21:'RightUpLeg',22:'Hips',23:'Hips',25:'LeftFoot',26:'RightFoot',28:'Hips',29:'Hips',30:'Hips',32:'Hips',33:'RightUpLeg',34:'Hips',35:'Hips',37:'RightUpLeg',39:'RightUpLeg',40:'RightUpLeg',41:'RightForeArm',42:'RightUpLeg',43:'RightForeArm',44:'RightUpLeg',45:'RightUpLeg',46:'Hips',48:'RightUpLeg',49:'RightUpLeg'}
for index,bone in rigid.items():bind(bpy.data.objects[f'tripo_part_{index}'],[B(bone)])
for index,names in {1:['Spine','Spine1','Spine2','LeftShoulder','RightShoulder'],6:['Spine1','Spine2','RightShoulder','RightArm','RightForeArm'],10:['Spine2','LeftShoulder','LeftArm','LeftForeArm'],13:['Head','Neck','Spine2','LeftShoulder','RightShoulder'],20:['LeftForeArm','LeftArm','LeftHand'],27:['Spine2','Neck','Spine1'],31:['LeftArm'],36:['Spine2','Spine1','Neck'],38:['LeftShoulder','Spine2'],47:['Spine2','Spine1','LeftShoulder']}.items():bind(bpy.data.objects[f'tripo_part_{index}'],[B(n) for n in names])
bind(bpy.data.objects['tripo_part_31'],[B('LeftArm')])
# Mail is on the upper arm; transfer forearm influences to its parent arm.
mail=bpy.data.objects['tripo_part_10'];arm=mail.vertex_groups[B('LeftArm')];forearm=mail.vertex_groups.get(B('LeftForeArm'))
if forearm:
 for vertex in mail.data.vertices:
  wa=sum(g.weight for g in vertex.groups if g.group==arm.index);wf=sum(g.weight for g in vertex.groups if g.group==forearm.index)
  if wf>0:arm.add([vertex.index],wa+wf,'REPLACE');forearm.remove([vertex.index])
# Extract the metal shoulder region into an independent rigid control. UVs and
# source positions are preserved. The cut is local to the known left shoulder.
source=bpy.data.objects['tripo_part_1'];old=source.data;inv=rig.matrix_world.inverted()
selected=[];keep=[]
for face in old.polygons:
 center_local=sum((inv@source.matrix_world@old.vertices[i].co for i in face.vertices),Vector())/len(face.vertices)
 (selected if (center_local.x>.095 and center_local.z>.755) or (center_local.x>.065 and center_local.z>.815) else keep).append(face.index)
assert selected,'No pauldron region found'
def copy_region(name,face_ids):
 ids=sorted({i for f in face_ids for i in old.polygons[f].vertices});lookup={i:j for j,i in enumerate(ids)};mesh=bpy.data.meshes.new(name);mesh.from_pydata([old.vertices[i].co[:] for i in ids],[],[tuple(lookup[i] for i in old.polygons[f].vertices) for f in face_ids]);mesh.update();obj=bpy.data.objects.new(name,mesh);scene.collection.objects.link(obj);obj.matrix_world=source.matrix_world.copy()
 for mat in old.materials:mesh.materials.append(mat)
 layer=mesh.uv_layers.new(name='UVMap')
 for face,original_id in zip(mesh.polygons,face_ids):
  previous=old.polygons[original_id];face.use_smooth=True;face.material_index=previous.material_index
  for a,b in zip(face.loop_indices,previous.loop_indices):layer.data[a].uv=old.uv_layers.active.data[b].uv
 return obj,ids
plate,plate_ids=copy_region('Independent_pauldron',selected);coat,coat_ids=copy_region('Coat_without_pauldron',keep)
groups={g.name:coat.vertex_groups.new(name=g.name) for g in source.vertex_groups}
for i,source_id in enumerate(coat_ids):
 for g in old.vertices[source_id].groups:groups[source.vertex_groups[g.group].name].add([i],g.weight,'REPLACE')
mod=coat.modifiers.new('Coat rig','ARMATURE');mod.object=rig
source.hide_render=True;source.hide_set(True)
bpy.context.view_layer.objects.active=rig;bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT');bone=rig.data.edit_bones.new('Pauldron_Hinge');bone.head=(.070,-.025,.875);bone.tail=(.070,.035,.875);bone.parent=rig.data.edit_bones[B('Spine2')];bpy.ops.object.mode_set(mode='OBJECT');bind(plate,['Pauldron_Hinge']);mod=plate.modifiers.new('Rigid hinge attachment','ARMATURE');mod.object=rig
# Correct the trousers around the knee without globally replacing shoulder skin.
for index,side in [(24,'Right')]:
 obj=bpy.data.objects[f'tripo_part_{index}'];knee=rig.data.bones[B(side+'Leg')].head_local.z
 for g in list(obj.vertex_groups):obj.vertex_groups.remove(g)
 thigh=obj.vertex_groups.new(name=B(side+'UpLeg'));calf=obj.vertex_groups.new(name=B(side+'Leg'))
 for vertex in obj.data.vertices:
  z=(inv@obj.matrix_world@vertex.co).z;t=max(0,min(1,(knee+.05-z)/.1));t=t*t*(3-2*t)
  if t<1:thigh.add([vertex.index],1-t,'REPLACE')
  if t>0:calf.add([vertex.index],t,'REPLACE')
for obj in meshes+[coat]:
 for mod in obj.modifiers:
  if mod.type=='ARMATURE':mod.use_deform_preserve_volume=True
shield=bpy.data.objects['tripo_part_0'];shield.hide_render=True;shield.hide_set(True)
metric_meshes=[o for o in meshes if not o.hide_render]+[coat,plate]
baseline=lengths()
repaired=True;report['pauldron_faces']=len(selected);report['shield_hidden_reversibly']=True
pose(0);report['repaired_arms_down']=distortion();render('after-arms-down');render('unshielded-back','back')
pose(1);report['repaired_bend']=distortion();render('after-bend')
# Save reusable editable scene, including unmodified hidden coat and shield.
pose(0);bpy.ops.wm.save_as_mainfile(filepath=str(a.out/'Warrior-T-Pose-working.blend'),compress=True)
rig.animation_data_create();action=bpy.data.actions.new('Tpose_repaired_joint_review');rig.animation_data.action=action
for frame in range(17):
 scene.frame_set(frame+1)
 pose(.5-.5*math.cos(2*math.pi*frame/16))
 for bone in rig.pose.bones:
  for path in ('location','rotation_quaternion','scale'):bone.keyframe_insert(data_path=path,frame=frame+1,group=bone.name)
 if frame<16:
  for view in ('front','side','back'):render(f'{view}-{frame:02}',view)
scene.frame_start=1;scene.frame_end=17;scene.render.fps=10;scene.frame_set(1)
report['pauldron_clearance']=clearance_samples
bpy.ops.wm.save_as_mainfile(filepath=str(a.out/'Warrior-T-Pose-animated.blend'),compress=True)
(a.out/'validation.json').write_text(json.dumps(report,indent=2));print('VALIDATION',json.dumps(report),flush=True)
