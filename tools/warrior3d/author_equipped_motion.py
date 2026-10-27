"""Author sampled equipment actions from existing matching-rig local clips.

Blender --python SCRIPT -- RECIPE.json OUTPUT.glb
Only animation data is appended. Meshes, images, nodes and bind data are kept.
Recipes may substitute an unused arm from another existing animation or retain
a shield guard during casting. No artwork or extracted tracks live in source.
"""
import copy,json,struct,sys,math
from pathlib import Path
import numpy as np
from mathutils import Quaternion,Matrix,Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from merge_paladin_walk import read


def tracks(g,b):
 def array(i):
  a=g['accessors'][i];v=g['bufferViews'][a['bufferView']];assert a['componentType']==5126 and 'byteStride' not in v
  width={'SCALAR':1,'VEC3':3,'VEC4':4}[a['type']]
  return np.frombuffer(b,dtype='<f4',count=a['count']*width,offset=v.get('byteOffset',0)+a.get('byteOffset',0)).reshape(-1,width).copy()
 result={}
 for c in g['animations'][0]['channels']:
  s=g['animations'][0]['samplers'][c['sampler']];method=s.get('interpolation','LINEAR');assert method in ('LINEAR','STEP');result[c['target']['node'],c['target']['path']]=(array(s['input'])[:,0],array(s['output']),method)
 return result


def blend(a,b,t,path):
 if t<=0:return np.asarray(a).copy()
 if t>=1:return np.asarray(b).copy()
 if path!='rotation':return np.asarray(a)*(1-t)+np.asarray(b)*t
 qa=Quaternion((a[3],*a[:3]));qb=Quaternion((b[3],*b[:3]));q=qa.slerp(qb,t).normalized();return np.array([q.x,q.y,q.z,q.w])


def author(recipe,destination):
 spec=json.loads(Path(recipe).read_text());source=Path(spec['source']);g,original_blob=read(source);original=copy.deepcopy(g);data=tracks(g,original_blob);blob=bytearray(original_blob);names={n.get('name'):i for i,n in enumerate(g['nodes'])};rows=len(spec['frames']);assert rows>=2
 def sample(tr,i,path,frame):
  if (i,path) not in tr:return np.array(g['nodes'][i].get(path,{'translation':[0,0,0],'rotation':[0,0,0,1],'scale':[1,1,1]}[path]),dtype=float)
  times,values,method=tr[i,path];time=frame/30;hi=int(np.searchsorted(times,time,side='right'))
  if hi==0:return values[0].copy()
  if hi>=len(times):return values[-1].copy()
  lo=hi-1;t=0 if method=='STEP' else float((time-times[lo])/(times[hi]-times[lo]));return blend(values[lo],values[hi],t,path)
 def branch(i):
  result={i}
  for c in g['nodes'][i].get('children',[]):result|=branch(c)
  return result
 overlays=[];keys=set(data)
 for item in spec.get('arms',[])+spec.get('node_overlays',[]):
  doc,binary=read(item['source']);assert doc['nodes']==g['nodes'] and doc['skins']==g['skins'];tr=tracks(doc,binary);indices={names[n] for n in item['nodes']} if 'nodes' in item else branch(names['m006.'+item['side']]);overlays.append((item,tr,indices));keys|={k for k in tr if k[0] in indices}
 idle=None
 if spec.get('idle'):
  doc,binary=read(spec['idle']);assert doc['nodes']==g['nodes'];idle=tracks(doc,binary);keys|=set(idle)
 world_arms=[]
 for item in spec.get('world_arm_sources',[]):
  doc,binary=read(item['source']);assert doc['nodes']==g['nodes'];world_arms.append((item,tracks(doc,binary)))
 parents={c:i for i,n in enumerate(g['nodes']) for c in n.get('children',[])}
 def world(pose):
  cache={}
  def get(i):
   if i not in cache:
    node=g['nodes'][i]
    if 'matrix' in node:m=Matrix([node['matrix'][j:j+4] for j in range(0,16,4)]).transposed()
    else:
     t=pose.get((i,'translation'),node.get('translation',[0,0,0]));r=pose.get((i,'rotation'),node.get('rotation',[0,0,0,1]));s=pose.get((i,'scale'),node.get('scale',[1,1,1]));m=Matrix.LocRotScale(Vector(t),Quaternion((r[3],*r[:3])),Vector(s))
    cache[i]=get(parents[i])@m if i in parents else m
   return cache[i]
  return get
 def set_world_rotation(pose,index,rotation,get):
  q=(get(parents[index]).to_quaternion().inverted()@rotation).normalized();pose[index,'rotation']=np.array([q.x,q.y,q.z,q.w])
 def tuck_arm(pose,side,amount,target_override=None):
  if amount<=0 and target_override is None:return
  u,e,h=[names[n+'.'+side] for n in ['upperArm','forearm','hand']];get=world(pose);a=get(u).translation.copy();b=get(e).translation.copy();c=get(h).translation.copy();hand_rotation=get(h).to_quaternion();center=get(names['pelvis']).translation;radial=Vector((c.x-center.x,0,c.z-center.z));target=c.copy();target.y-=amount
  if radial.length>1e-5:target-=radial.normalized()*amount*.5
  if target_override is not None:target=Vector(target_override)
  upper=(b-a).length;lower=(c-b).length;direction=target-a;minimum=(upper*upper+lower*lower+2*upper*lower*math.cos(math.radians(130)))**.5;distance=max(minimum,min(direction.length,(upper+lower)*.99));direction.normalize();target=a+direction*distance;pole=b-a;pole-=direction*pole.dot(direction)
  if pole.length<1e-5:pole=Vector((1 if side=='L' else -1,0,0)).cross(direction)
  pole.normalize();along=(upper*upper-lower*lower+distance*distance)/(2*distance);elbow=a+direction*along+pole*max(0,upper*upper-along*along)**.5
  set_world_rotation(pose,u,(b-a).rotation_difference(elbow-a)@get(u).to_quaternion(),get);get=world(pose);b=get(e).translation;c=get(h).translation;set_world_rotation(pose,e,(c-b).rotation_difference(target-b)@get(e).to_quaternion(),get);get=world(pose);set_world_rotation(pose,h,hand_rotation,get)
 if spec.get('align_horizontal_root'):keys.add((names['root'],'translation'))
 for item in spec.get('attachment_constraints',[]):
  for path in ['translation','rotation','scale']:keys.add((names[item['bone']],path))
 poses=[];root_alignment=None
 for row,frame in enumerate(spec['frames']):
  pose={key:sample(data,*key,frame) for key in keys}
  for item,tr,indices in overlays:
   off_frame=item['frames'][row]
   for key in keys:
    if key[0] in indices:pose[key]=blend(pose[key],sample(tr,*key,off_frame),item.get('weights',[item.get('weight',1)]*rows)[row],key[1])
  if idle is not None:
   weight=spec.get('idle_weights',[0]*rows)[row]
   for key in keys:pose[key]=blend(pose[key],sample(idle,*key,0),weight,key[1])
   gain=spec.get('arm_gain',1)
   if gain<1:
    arm_nodes=branch(names['m006.L'])|branch(names['m006.R'])
    for key in keys:
     if key[0] in arm_nodes:pose[key]=blend(sample(idle,*key,0),pose[key],gain,key[1])
   motion_gain=spec.get('motion_gain',1)
   if motion_gain<1:
    for key in keys:pose[key]=blend(sample(idle,*key,0),pose[key],motion_gain,key[1])
  if spec.get('align_horizontal_root'):
   get=world(pose)
   if root_alignment is None:
    pelvis=get(names['pelvis']).translation;root_alignment=Vector((-pelvis.x,0,-pelvis.z))
   i=names['root'];pose[i,'translation']+=np.array(get(parents[i]).to_3x3().inverted()@root_alignment)
  for side,gain in spec.get('wrist_gain',{}).items():
   key=(names['hand.'+side],'rotation');pose[key]=blend(sample(idle,*key,0),pose[key],gain,'rotation')
  for root_name,gain in spec.get('branch_gains',{}).items():
   indices=branch(names[root_name]);assert idle is not None
   for key in keys:
    if key[0] in indices:pose[key]=blend(sample(idle,*key,0),pose[key],gain,key[1])
  for item,tr in world_arms:
   native=world({key:sample(tr,*key,item['frames'][row]) for key in tr});rest=world({key:sample(idle,*key,0) for key in idle});amount=1-spec.get('idle_weights',[0]*rows)[row]
   for joint in ['upperArm','forearm','hand']:
    i=names[joint+'.'+item['side']];rotation=rest(i).to_quaternion().slerp(native(i).to_quaternion(),amount);set_world_rotation(pose,i,rotation,world(pose))
  for side,amount in spec.get('arm_tuck',{}).items():tuck_arm(pose,side,float(amount)*(1-spec.get('idle_weights',[0]*rows)[row]))
  for side,offsets in spec.get('hand_offsets',{}).items():
   target=world(pose)(names['hand.'+side]).translation+Vector(offsets[row]);tuck_arm(pose,side,0,target)
  # Keep a complete weapon arc; adjust the wrist's reach with two-bone IK,
  # rather than blending away the attack rotations. The rigid grip is unchanged.
  if spec.get('weapon_envelope'):
   env=spec['weapon_envelope'];side=env.get('side','R')
   direction=env.get('directions',[None]*rows)[row]
   if direction is not None:
    get=world(pose);i=names['hand.'+side];hand=get(i);current=hand.to_3x3()@Vector(env['tip_local']);rotation=current.rotation_difference(Vector(direction))@hand.to_quaternion();set_world_rotation(pose,i,rotation,get)
   for iteration in range(3):
    get=world(pose);hand=get(names['hand.'+side]);tip=hand@Vector(env['tip_local']);pelvis=get(names['pelvis']).translation;radial=Vector((tip.x-pelvis.x,0,tip.z-pelvis.z));height=max(0,tip.y-pelvis.y+env.get('hip_height',.95));limit=min(env.get('horizontal_budget',1.50)-.5*height,env.get('bottom_budget',.72)+2/3*height);excess=radial.length-max(.15,limit)
    excess_height=max(0,height-env.get('height_limit',100))
    if excess<=0 and excess_height<=0:break
    target=hand.translation.copy()
    if excess>0:target-=radial.normalized()*excess
    target.y-=excess_height;tuck_arm(pose,side,0,target)
  if spec.get('finger_grip'):
   assert idle is not None
   for side in spec['finger_grip']:
    finger_nodes=branch(names['hand.'+side])-{names['weapon.'+side]}
    if side=='R' or spec.get('preserve_grip_wrist_motion'):finger_nodes.discard(names['hand.'+side])
    for key in keys:
     if key[0] in finger_nodes:pose[key]=sample(idle,*key,0)
  poses.append(pose)
 # Optional attack-only temporal smoothing. Locked rows retain the start,
 # gameplay impact and end poses; bone lengths and bind data stay untouched.
 for smoothing_pass in range(spec.get('temporal_smoothing_passes',0)):
  previous=poses;poses=[];locked=set(spec.get('locked_rows',[0,rows-1]))
  for row,pose in enumerate(previous):
   if row in locked or row==0 or row==rows-1:poses.append(pose);continue
   poses.append({key:blend(blend(previous[row-1][key],pose[key],2/3,key[1]),previous[row+1][key],.25,key[1]) for key in keys})
 # Wrist-only shield tilt: preserve shoulder, elbow and hand position.
 for item in spec.get('wrist_shield_vertical',[]):
  hand_index=names[item['hand']];weapon_index=names[item['bone']];reference=world(poses[0]);relative=reference(hand_index).inverted()@reference(weapon_index)
  for row,pose in enumerate(poses):
   get=world(pose);hand=get(hand_index);shield=hand@relative;normal=(shield.to_3x3().inverted().transposed()@Vector(item['normal_local'])).normalized();target=Vector((normal.x,0,normal.z))
   if target.length<1e-5:continue
   target.normalize();correction=normal.rotation_difference(target);rotation=hand.to_quaternion().slerp(correction@hand.to_quaternion(),item['weights'][row]);set_world_rotation(pose,hand_index,rotation,get)
 # Equipment-only attachment bones can keep a rigid item's face upright while
 # its grip follows the native hand. They must have no weighted body vertices.
 for row,pose in enumerate(poses):
  for item in spec.get('attachment_constraints',[]):
   assert item.get('weighted_body_vertices')==0
   get=world(pose);i=names[item['bone']];hand=get(names[item['hand']]);current=get(i);normal=(current.to_3x3().inverted().transposed()@Vector(item['normal_local'])).normalized();rotation=current.to_quaternion();desired=normal.rotation_difference(Vector(item.get('forward',[0,0,1])))@rotation
   if item.get('up_local'):
    source_normal=Vector(item['normal_local']).normalized();source_up=Vector(item['up_local']);source_up=(source_up-source_normal*source_up.dot(source_normal)).normalized();target_normal=Vector(item.get('forward',[0,0,1])).normalized();target_up=Vector((0,1,0));target_up=(target_up-target_normal*target_up.dot(target_normal)).normalized();source_basis=Matrix((source_up,source_normal,source_up.cross(source_normal))).transposed();target_basis=Matrix((target_up,target_normal,target_up.cross(target_normal))).transposed();desired=(target_basis@source_basis.transposed()).to_quaternion()
   if item.get('follow_hand'):
    # Carry the approved mount with the hand, or fit a hand-relative
    # contact orientation. Never change any body bone to compensate.
    reference_get=world(poses[item.get('reference_row',8)]);reference_hand=reference_get(names[item['hand']]).to_quaternion()
    desired=hand.to_quaternion()@(reference_hand.inverted()@reference_get(i).to_quaternion()) if item.get('preserve_mount_rotation') else hand.to_quaternion()@(reference_hand.inverted()@desired)
   rotation=rotation.slerp(desired,item.get('weights',[1]*rows)[row]);matrix=Matrix.LocRotScale(Vector((0,0,0)),rotation,Vector(item['scale']));matrix.translation=hand@Vector(item['hand_grip_local'])-matrix.to_3x3()@Vector(item['grip_local']);local=get(parents[i]).inverted()@matrix;position,q,scale=local.decompose();pose[i,'translation']=np.array(position);pose[i,'rotation']=np.array([q.x,q.y,q.z,q.w]);pose[i,'scale']=np.array(scale)
 def add(values,kind):
  a=np.asarray(values,dtype='<f4');blob.extend(b'\0'*((-len(blob))%4));offset=len(blob);raw=a.tobytes();blob.extend(raw);view=len(g['bufferViews']);g['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':len(raw)});acc={'bufferView':view,'componentType':5126,'count':len(a),'type':kind}
  if kind=='SCALAR':acc.update(min=[float(a.min())],max=[float(a.max())])
  index=len(g['accessors']);g['accessors'].append(acc);return index
 time=add(np.arange(rows)[:,None]/30,'SCALAR');clip={'name':spec.get('name','Equipped action'),'channels':[],'samplers':[]}
 for key in sorted(keys):
  i,path=key;clip['channels'].append({'sampler':len(clip['samplers']),'target':{'node':i,'path':path}});clip['samplers'].append({'input':time,'output':add([p[key] for p in poses],'VEC4' if path=='rotation' else 'VEC3'),'interpolation':'LINEAR'})
 g['animations']=[clip];g['buffers'][0]['byteLength']=len(blob)
 for field in ['meshes','nodes','skins','images','materials']:assert g.get(field)==original.get(field),field
 assert blob[:len(original_blob)]==original_blob
 text=json.dumps(g,separators=(',',':')).encode();text+=b' '*((-len(text))%4);blob.extend(b'\0'*((-len(blob))%4));destination=Path(destination);assert destination.resolve()!=source.resolve();destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(struct.pack('<III',0x46546c67,2,28+len(text)+len(blob))+struct.pack('<II',len(text),0x4e4f534a)+text+struct.pack('<II',len(blob),0x004e4942)+blob)
 destination.with_suffix('.motion.json').write_text(json.dumps({'recipe':spec,'frames':rows,'original_geometry_images_nodes_and_bindings_preserved':True},indent=2));print('Authored',clip['name'],rows,'frames')


if __name__=='__main__':author(*sys.argv[sys.argv.index('--')+1:])
