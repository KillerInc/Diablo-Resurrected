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
 for item in spec.get('arms',[]):
  doc,binary=read(item['source']);assert doc['nodes']==g['nodes'] and doc['skins']==g['skins'];tr=tracks(doc,binary);root=names['m006.'+item['side']];indices=branch(root);overlays.append((item,tr,indices));keys|={k for k in tr if k[0] in indices}
 idle=None
 if spec.get('idle'):
  doc,binary=read(spec['idle']);assert doc['nodes']==g['nodes'];idle=tracks(doc,binary);keys|=set(idle)
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
 def tuck_arm(pose,side,amount):
  if amount<=0:return
  u,e,h=[names[n+'.'+side] for n in ['upperArm','forearm','hand']];get=world(pose);a=get(u).translation.copy();b=get(e).translation.copy();c=get(h).translation.copy();hand_rotation=get(h).to_quaternion();center=get(names['pelvis']).translation;radial=Vector((c.x-center.x,0,c.z-center.z));target=c.copy();target.y-=amount
  if radial.length>1e-5:target-=radial.normalized()*amount*.5
  upper=(b-a).length;lower=(c-b).length;direction=target-a;minimum=(upper*upper+lower*lower+2*upper*lower*math.cos(math.radians(130)))**.5;distance=max(minimum,min(direction.length,(upper+lower)*.99));direction.normalize();target=a+direction*distance;pole=b-a;pole-=direction*pole.dot(direction)
  if pole.length<1e-5:pole=Vector((1 if side=='L' else -1,0,0)).cross(direction)
  pole.normalize();along=(upper*upper-lower*lower+distance*distance)/(2*distance);elbow=a+direction*along+pole*max(0,upper*upper-along*along)**.5
  set_world_rotation(pose,u,(b-a).rotation_difference(elbow-a)@get(u).to_quaternion(),get);get=world(pose);b=get(e).translation;c=get(h).translation;set_world_rotation(pose,e,(c-b).rotation_difference(target-b)@get(e).to_quaternion(),get);get=world(pose);set_world_rotation(pose,h,hand_rotation,get)
 poses=[]
 for row,frame in enumerate(spec['frames']):
  pose={key:sample(data,*key,frame) for key in keys}
  for item,tr,indices in overlays:
   off_frame=item['frames'][row]
   for key in keys:
    if key[0] in indices:pose[key]=blend(pose[key],sample(tr,*key,off_frame),item.get('weight',1),key[1])
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
  for side,gain in spec.get('wrist_gain',{}).items():
   key=(names['hand.'+side],'rotation');pose[key]=blend(sample(idle,*key,0),pose[key],gain,'rotation')
  for side,amount in spec.get('arm_tuck',{}).items():tuck_arm(pose,side,float(amount)*(1-spec.get('idle_weights',[0]*rows)[row]))
  if spec.get('finger_grip'):
   assert idle is not None
   for side in spec['finger_grip']:
    finger_nodes=branch(names['hand.'+side])-{names['weapon.'+side]}
    if side=='R':finger_nodes.discard(names['hand.R'])
    for key in keys:
     if key[0] in finger_nodes:pose[key]=sample(idle,*key,0)
  poses.append(pose)
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
