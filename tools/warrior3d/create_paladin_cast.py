"""Build a twenty-pose warrior cast from a native hand gesture and current idle.

Blender --python SCRIPT -- NATIVE.glb IDLE.glb OUTPUT.glb [GESTURE_STRENGTH]
Keeps geometry, bindings and nodes intact. The reviewed gesture profiles map their
release pose to gameplay frame 14; the existing engine controls spell timing. Idle endpoints are exact.
"""
import copy,json,struct,sys,math
from pathlib import Path
import numpy as np
from mathutils import Matrix,Quaternion,Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from merge_paladin_walk import read
arguments=sys.argv[sys.argv.index('--')+1:];source,idle,destination=map(Path,arguments[:3]);strength=float(arguments[3]) if len(arguments)>3 else 1.0;assert 0<strength<=1;g,original_blob=read(source);ig,ib=read(idle);original=copy.deepcopy(g);blob=bytearray(original_blob);ritual=g['animations'][0]['name']=='sorM_wndoh_attk_firewall-Paladin';assert ritual or g['animations'][0]['name']=='palM_HTH_event_use_resurrect','Expected reviewed native gesture'
assert g['nodes']==ig['nodes'] and g['skins']==ig['skins'],'Matching current rig required'
names={n.get('name'):i for i,n in enumerate(g['nodes'])};parents={c:i for i,n in enumerate(g['nodes']) for c in n.get('children',[])}
def array(doc,binary,index):
 a=doc['accessors'][index];v=doc['bufferViews'][a['bufferView']];assert a['componentType']==5126 and 'byteStride' not in v
 width={'SCALAR':1,'VEC3':3,'VEC4':4}[a['type']];return np.frombuffer(binary,dtype='<f4',count=a['count']*width,offset=v.get('byteOffset',0)+a.get('byteOffset',0)).reshape(-1,width).copy()
def tracks(doc,binary):
 result={}
 for ch in doc['animations'][0]['channels']:
  s=doc['animations'][0]['samplers'][ch['sampler']];assert s.get('interpolation','LINEAR') in ['LINEAR','STEP'];result[(ch['target']['node'],ch['target']['path'])]=(array(doc,binary,s['input'])[:,0],array(doc,binary,s['output']),s.get('interpolation','LINEAR'))
 return result
native=tracks(g,original_blob);rest=tracks(ig,ib);keys=set(native)|set(rest)|{(names['root'],'translation')}
def q(v):return Quaternion((v[3],v[0],v[1],v[2]))
def values(rotation):return np.array([rotation.x,rotation.y,rotation.z,rotation.w])
def blend(a,b,t,path):
 if t<=0:return np.array(a).copy()
 if t>=1:return np.array(b).copy()
 return values(q(a).slerp(q(b),t)) if path=='rotation' else np.asarray(a)*(1-t)+np.asarray(b)*t

def sample(data,i,path,time):
 if (i,path) not in data:return np.array(g['nodes'][i].get(path,{'translation':[0,0,0],'rotation':[0,0,0,1],'scale':[1,1,1]}[path]),dtype=float)
 times,vs,method=data[i,path];hi=int(np.searchsorted(times,time,side='right'))
 if hi==0:return vs[0].copy()
 if hi>=len(times):return vs[-1].copy()
 lo=hi-1;alpha=0 if method=='STEP' else float((time-times[lo])/(times[hi]-times[lo]));return blend(vs[lo],vs[hi],alpha,path)
base=[{path:sample(rest,i,path,0) for path in ['translation','rotation','scale']} for i in range(len(g['nodes']))]
def world(pose):
 cache={}
 def get(i):
  if i not in cache:
   n=g['nodes'][i];m=Matrix([n['matrix'][j:j+4] for j in range(0,16,4)]).transposed() if 'matrix' in n else Matrix.LocRotScale(Vector(pose[i]['translation']),q(pose[i]['rotation']),Vector(pose[i]['scale']))
   cache[i]=get(parents[i])@m if i in parents else m
  return cache[i]
 for i in range(len(pose)):get(i)
 return cache
def compact_arm(pose,side,amount):
 matrices=world(pose);u,e,h=[names[n+'.'+side] for n in ['upperArm','forearm','hand']];shoulder=matrices[u].translation.copy();elbow=matrices[e].translation.copy();wrist=matrices[h].translation.copy();hand_rotation=matrices[h].to_quaternion();target=wrist.copy();target.y=min(target.y,1.25)
 planar=Vector((target.x,0,target.z));radius=planar.length;limit=max(.22,.95-.5*target.y)
 if radius>limit:target.x*=limit/radius;target.z*=limit/radius
 a=(elbow-shoulder).length;b=(wrist-elbow).length;direction=target-shoulder;minimum=math.sqrt(max(0,a*a+b*b+2*a*b*math.cos(math.radians(130))));distance=max(minimum,min(direction.length,(a+b)*.99));direction.normalize();target=shoulder+direction*distance
 sign=1 if side=='L' else -1;hint=elbow.lerp(shoulder+Vector((sign*.18,-.32,.12)),.7*amount);pole=hint-shoulder;pole-=direction*pole.dot(direction)
 if pole.length<1e-6:pole=Vector((sign,0,0)).cross(direction)
 pole.normalize();along=(a*a-b*b+distance*distance)/(2*distance);desired=shoulder+direction*along+pole*math.sqrt(max(0,a*a-along*along))
 def set_rotation(i,rotation,matrices):pose[i]['rotation']=values((matrices[parents[i]].to_quaternion().inverted()@rotation).normalized())
 set_rotation(u,(elbow-shoulder).rotation_difference(desired-shoulder)@matrices[u].to_quaternion(),matrices);matrices=world(pose);elbow=matrices[e].translation;wrist=matrices[h].translation;set_rotation(e,(wrist-elbow).rotation_difference(target-elbow)@matrices[e].to_quaternion(),matrices);matrices=world(pose);set_rotation(h,hand_rotation,matrices)

first=world(base);stance=sum((first[names['ankle.'+s]].translation for s in ['L','R']),Vector())*.5
poses=[];report=[]
for row in range(20):
 if ritual:
  native_frame=[0,0,0,0,2,4,6,8,10,12,14,16,18,20,22,24,27,30,33,35][row]
  t=min(1,row/3) if row<=16 else (19-row)/3
 else:
  native_frame=26*row/13 if row<=13 else 26+(row-13)
  t=min(1,row/3) if row<=13 else 1-(row-13)/6
 t=t*t*(3-2*t)*strength
 pose=copy.deepcopy(base)
 for i,path in keys:pose[i][path]=blend(base[i][path],sample(native,i,path,native_frame/30) if not ritual or (i,path) in native else base[i][path],t,path)
 if t>0 and not ritual:
  # A compact shoulder gesture plus an anatomical elbow bend raises the palm
  # without reaching far enough forward to overflow the original shadow cell.
  envelope=t/strength
  for side in ['L','R']:
   arm_index=names['upperArm.'+side];pose[arm_index]['rotation']=blend(base[arm_index]['rotation'],sample(native,arm_index,'rotation',native_frame/30),t*.65,'rotation')
  for side,degrees in [('L',55),('R',20)]:
   matrices=world(pose);u,e,h=[names[n+'.'+side] for n in ['upperArm','forearm','hand']];upper=matrices[e].translation-matrices[u].translation;lower=matrices[h].translation-matrices[e].translation;axis=upper.cross(lower)
   if axis.length<1e-6:axis=upper.cross(Vector((0,0,1)))
   axis.normalize();angle=min(math.radians(degrees)*envelope,max(0,math.radians(125)-upper.angle(lower)));rotation=Quaternion(axis,angle)@matrices[e].to_quaternion();parent=matrices[parents[e]].to_quaternion();pose[e]['rotation']=values((parent.inverted()@rotation).normalized())
   if side=='L':
    matrices=world(pose);wrist=Quaternion(axis,math.radians(25)*envelope)@matrices[h].to_quaternion();pose[h]['rotation']=values((matrices[parents[h]].to_quaternion().inverted()@wrist).normalized())

 if t>0:
  matrices=world(pose);mid=sum((matrices[names['ankle.'+s]].translation for s in ['L','R']),Vector())*.5;delta=Vector((stance.x-mid.x,stance.y-mid.y if ritual else 0,stance.z-mid.z));root=names['root'];local=matrices[parents[root]].to_3x3().inverted()@delta if root in parents else delta;pose[root]['translation']=pose[root]['translation']+np.array(local)
 if ritual and t>0:
  for side in ['L','R']:
   for joint in ['ankle','foot']:
    i=names[joint+'.'+side];matrices=world(pose);rotation=matrices[i].to_quaternion().slerp(first[i].to_quaternion(),t/strength);pose[i]['rotation']=values((matrices[parents[i]].to_quaternion().inverted()@rotation).normalized())
   compact_arm(pose,side,t/strength)
 matrices=world(pose);mid=sum((matrices[names['ankle.'+s]].translation for s in ['L','R']),Vector())*.5;assert np.hypot(mid.x-stance.x,mid.z-stance.z)<1e-5
 poses.append(pose);report.append({'row':row,'native_frame':native_frame,'native_weight':t,'stance_midpoint':list(mid)})
for row in [0,19]:
 for i,path in keys:assert np.array_equal(poses[row][i][path],base[i][path]),('Idle endpoint changed',row,i,path)
def add(data,kind):
 data=np.asarray(data,dtype='<f4');blob.extend(b'\0'*((-len(blob))%4));offset=len(blob);raw=data.tobytes();blob.extend(raw);vi=len(g['bufferViews']);g['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':len(raw)});a={'bufferView':vi,'componentType':5126,'count':len(data),'type':kind}
 if kind=='SCALAR':a.update(min=[float(data.min())],max=[float(data.max())])
 index=len(g['accessors']);g['accessors'].append(a);return index
time=add(np.arange(20)[:,None]/30,'SCALAR');clip={'name':'Paladin-warrior-fire-ritual' if ritual else 'Paladin-warrior-fire-cast','channels':[],'samplers':[]}
for i,path in sorted(keys):
 clip['channels'].append({'sampler':len(clip['samplers']),'target':{'node':i,'path':path}});clip['samplers'].append({'input':time,'output':add([p[i][path] for p in poses],'VEC4' if path=='rotation' else 'VEC3'),'interpolation':'LINEAR'})
g['animations']=[clip];g['buffers'][0]['byteLength']=len(blob)
for key in ['meshes','skins','nodes','materials','images']:assert g[key]==original[key],key
assert blob[:len(original_blob)]==original_blob,'Original geometry/texture buffer changed'
text=json.dumps(g,separators=(',',':')).encode();text+=b' '*((-len(text))%4);blob.extend(b'\0'*((-len(blob))%4));destination.parent.mkdir(parents=True,exist_ok=True);assert destination.resolve() not in [source.resolve(),idle.resolve()];destination.write_bytes(struct.pack('<III',0x46546c67,2,28+len(text)+len(blob))+struct.pack('<II',len(text),0x4e4f534a)+text+struct.pack('<II',len(blob),0x004e4942)+blob)
destination.with_suffix('.casting.json').write_text(json.dumps({'native_clip':original['animations'][0]['name'],'frames':20,'gesture_strength':strength,'upper_arm_weight_multiplier':1 if ritual else .65,'casting_wrist_extension_degrees':0 if ritual else 25,'additional_elbow_flex_degrees':{} if ritual else {'L':55,'R':20},'release_frame_one_based':14,'native_release_frame':20 if ritual else 26,'exact_idle_endpoints':True,'geometry_bindings_nodes_preserved':True,'horizontal_stance_midpoint_fixed':True,'vertical_stance_midpoint_fixed':ritual,'compact_ritual_arms':ritual,'stable_casting_feet':ritual,'poses':report},indent=2));print('Created twenty cast poses; release 14; exact idle endpoints')
