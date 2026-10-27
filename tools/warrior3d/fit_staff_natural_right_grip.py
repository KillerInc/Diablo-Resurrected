"""Blender --python SCRIPT -- RIGHT_FINGERS_CLOSED_PLAN NEW_PRIVATE_WORK
Fit a consistent grip with elbow bend and forearm turn. A constant grip-axis
sign avoids wrist flips; elbow/shaft candidates keep wrist rotation small.
Run rebase_staff_attachment.py against the previous plan before rendering.
"""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
tools=Path(__file__).resolve().parent;sys.path.insert(0,str(tools));from merge_paladin_walk import read;from author_equipped_motion import tracks,author
args=sys.argv[sys.argv.index('--')+1:];plan_file=Path(args[0]);work=Path(args[1]).resolve();assert not work.exists();work.mkdir(parents=True);plan=json.loads(plan_file.read_text());source=Path(plan['jobs'][0]['model']);g,b=read(source);tr=tracks(g,b);names={n.get('name'):i for i,n in enumerate(g['nodes'])};parents={c:i for i,n in enumerate(g['nodes']) for c in n.get('children',[])};B=Matrix(((1,0,0,0),(0,0,-1,0),(0,1,0,0),(0,0,0,1)));bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=str(source));rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');targets=[];corrections=[]
def worlds(row):
 cache={}
 def get(i):
  if i not in cache:
   node=g['nodes'][i]
   def value(path,default):return tr[i,path][1][row] if (i,path) in tr else node.get(path,default)
   if 'matrix' in node:m=Matrix([node['matrix'][j:j+4] for j in range(0,16,4)]).transposed()
   else:
    q=value('rotation',[0,0,0,1]);m=Matrix.LocRotScale(Vector(value('translation',[0,0,0])),Quaternion((float(q[3]),*map(float,q[:3]))),Vector(value('scale',[1,1,1])))
   cache[i]=(get(parents[i]) if i in parents else Matrix.Identity(4))@m
  return cache[i]
 return get
rest=(rig.data.bones['forearm.R'].matrix_local.inverted()@rig.data.bones['hand.R'].matrix_local).to_quaternion();grip=Vector((.04,.065,0));targets=[];reviews=[];previous=None;axis_sign=None
for row in range(16):
 bpy.context.scene.frame_set(row);bpy.context.view_layer.update();h=rig.matrix_world@rig.pose.bones['hand.R'].matrix;fq=(rig.matrix_world@rig.pose.bones['forearm.R'].matrix).to_quaternion();A=rig.matrix_world@rig.pose.bones['upperArm.R'].head;E0=rig.matrix_world@rig.pose.bones['forearm.R'].head;H0=h.translation;P=h@Vector((.0425,.0825,-.002));L=rig.matrix_world@rig.pose.bones['hand.L'].matrix@Vector((-.04,.065,0));axis=(P-L).normalized()
 if axis_sign is None:axis_sign=1 if (h.to_3x3()@Vector((0,0,1))).dot(axis)>=0 else -1
 z=axis*axis_sign;upper=(E0-A).length;lower=(H0-E0).length;best=None
 for step in range(-10,11):
  slide=step*.025;centre=P+axis*slide
  for pole_degrees in range(-100,101,20):
   q=h.to_quaternion();valid=True
   for iteration in range(16):
    H=centre-q@grip;D=H-A;distance=D.length
    if distance>upper+lower-.003 or distance<abs(upper-lower)+.003:valid=False;break
    D.normalize();pole=E0-A;pole-=D*pole.dot(D)
    if pole.length<1e-5:valid=False;break
    pole=Quaternion(D,math.radians(pole_degrees))@pole.normalized();along=(upper*upper-lower*lower+distance*distance)/(2*distance);E=A+D*along+pole*max(0,upper*upper-along*along)**.5;F=(H-E).normalized();uq=(E0-A).rotation_difference(E-A);eq=(uq@(H0-E0)).rotation_difference(H-E);baseq=eq@uq@fq;neutral=baseq@rest;v=neutral@Vector((0,0,1));a=v-F*v.dot(F);b=z-F*z.dot(F)
    if min(a.length,b.length)<1e-5:valid=False;break
    a.normalize();b.normalize();twist=math.atan2(F.dot(a.cross(b)),a.dot(b));twist=max(-math.radians(80),min(math.radians(80),twist));forearm=Quaternion(F,twist)@baseq;neutral=forearm@rest;delta=(neutral@Vector((0,0,1))).rotation_difference(z);nextq=delta@neutral
    if nextq.rotation_difference(q).angle<1e-5:q=nextq;break
    q=q.slerp(nextq,.7)
   if not valid:continue
   desired_H=centre-q@grip;error=(desired_H-H).length;bend=math.degrees(delta.angle)
   if error>.001 or bend>25:continue
   jump=math.degrees(q.rotation_difference(previous).angle) if previous is not None else 0
   cost=.2*bend*bend+.025*math.degrees(twist)**2+slide*slide*2500+(E-E0).length_squared*1200+.008*jump*jump
   if best is None or cost<best[0]:best=(cost,desired_H.copy(),q.copy(),E.copy(),math.degrees(twist),slide,bend,(E-E0).length)
 assert best is not None,('No natural grip candidate',row)
 _,H,q,E,twist,slide,bend,elbow_move=best;previous=q.copy();desired=Matrix.LocRotScale(H,q,h.to_scale());gw=worlds(row)(names['hand.R']);C=(B@gw).inverted()@h;target=B.inverted()@desired@C.inverted();qt=target.to_quaternion();targets.append({'position':list(target.translation),'rotation_wxyz':[qt.w,qt.x,qt.y,qt.z],'elbow':list(B.inverted()@E),'forearm_twist_degrees':twist});reviews.append({'row':row,'wrist_delta_from_bind_degrees':bend,'forearm_twist_degrees':twist,'grip_slide_metres':slide,'elbow_move_metres':elbow_move});print('NATURAL GRIP',reviews[-1],flush=True)
recipe={'name':'Selected Sorcerer, natural right elbow and forearm grip','source':str(source),'frames':list(range(16)),'arms':[],'preserve_attack_motion':True,'hand_grip_poses':{'R':targets}};rp=work/'recipe.json';rp.write_text(json.dumps(recipe,indent=2));model=work/'sorcerer.glb';author(rp,model);plan['work']=str(work);j=plan['jobs'][0];out=work/'preview';out.mkdir(exist_ok=True);ref=json.loads(Path(j['reference']).read_text());reference=out/'reference.json';reference.write_text(json.dumps(ref,indent=2));j.update(model=str(model),root=str(out),reference=str(reference));(work/'plan.json').write_text(json.dumps(plan,indent=2));(work/'natural-arm-fit.json').write_text(json.dumps(reviews,indent=2))
