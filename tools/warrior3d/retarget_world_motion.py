"""Blender --python SCRIPT -- LOCAL_RETARGET.glb SOURCE_CLIP.glb OUTPUT.glb
Retarget mapped joints by global rest-pose rotation deltas; preserve target skin.
Uses the semantic/ancestor mapping report from retarget_paladin_kick.py.
"""
import sys,json,copy,struct,math
from pathlib import Path
import numpy as np
from mathutils import Matrix,Vector,Quaternion
sys.path.insert(0,str(Path(__file__).parent));from merge_paladin_walk import read
from author_equipped_motion import tracks,blend
target,source,dest=map(Path,sys.argv[sys.argv.index('--')+1:]);g,blob0=read(target);s,sb=read(source);original=copy.deepcopy(g);report=json.loads(target.with_suffix('.retarget.json').read_text());sn={n.get('name'):i for i,n in enumerate(s['nodes'])};tn={n.get('name'):i for i,n in enumerate(g['nodes'])};mapping={sn[n]:tn[report['ancestor_bridges'].get(n,n)] for n in report['matched_named_bones']};reverse={j:i for i,j in mapping.items()};sp={c:i for i,n in enumerate(s['nodes']) for c in n.get('children',[])};tp={c:i for i,n in enumerate(g['nodes']) for c in n.get('children',[])};tr=tracks(s,sb)
def rest(n):
 if 'matrix' in n:return Matrix([n['matrix'][k:k+4] for k in range(0,16,4)]).transposed()
 q=n.get('rotation',[0,0,0,1]);return Matrix.LocRotScale(Vector(n.get('translation',[0,0,0])),Quaternion((q[3],*q[:3])),Vector(n.get('scale',[1,1,1])))
def worlds(nodes,parents,locals):
 result={}
 def get(i):
  if i not in result:result[i]=(get(parents[i]) if i in parents else Matrix.Identity(4))@locals[i]
  return result[i]
 for i in range(len(nodes)):get(i)
 return result
sr=[rest(n) for n in s['nodes']];tt=[rest(n) for n in g['nodes']];sw0=worlds(s['nodes'],sp,sr);tw0=worlds(g['nodes'],tp,tt)
correction={j:sw0[i].to_quaternion().inverted()@tw0[j].to_quaternion() for i,j in mapping.items()}
for socket in ['weapon.L','weapon.R']:
 if socket in sn and sn[socket] in mapping:correction[mapping[sn[socket]]]=Quaternion((1,0,0,0))
# Match anatomical link directions, rather than retaining a different class's
# A/T-pose arm spread as an offset throughout the animation.
links={'upperArm':'forearm','forearm':'hand','hand':'handEnd','thigh':'shin','shin':'ankle'}
for side in ['.L','.R']:
 for a,b in links.items():
  ai,bi=sn[a+side],sn[b+side];aj,bj=tn[a+side],tn[b+side];sv=sw0[bi].translation-sw0[ai].translation;tv=tw0[bj].translation-tw0[aj].translation
  correction[aj]=sw0[ai].to_quaternion().inverted()@tv.rotation_difference(sv)@tw0[aj].to_quaternion()
 for a,b in report['ancestor_bridges'].items():
  if not a.endswith(side):continue
  ai,aj=sn[a],tn[b];bi,bj=sn['upperArm'+side],tn['upperArm'+side];sv=sw0[bi].translation-sw0[ai].translation;tv=tw0[bj].translation-tw0[aj].translation
  if min(sv.length,tv.length)>.0001:correction[aj]=sw0[ai].to_quaternion().inverted()@tv.rotation_difference(sv)@tw0[aj].to_quaternion()
def value(i,path,time):
 if (i,path) not in tr:return np.array(s['nodes'][i].get(path,{'translation':[0,0,0],'rotation':[0,0,0,1],'scale':[1,1,1]}[path]))
 times,values,method=tr[i,path];hi=int(np.searchsorted(times,time,side='right'))
 if hi==0:return values[0]
 if hi>=len(times):return values[-1]
 lo=hi-1;return blend(values[lo],values[hi],0 if method=='STEP' else (time-times[lo])/(times[hi]-times[lo]),path)
end=max(float(v[0][-1]) for v in tr.values());count=round(end*30)+1;out={(j,p):[] for j in reverse for p in ['translation','rotation','scale']}
for frame in range(count):
 time=frame/30;sl=[]
 for i,n in enumerate(s['nodes']):
  q=value(i,'rotation',time);sl.append(Matrix.LocRotScale(Vector(value(i,'translation',time)),Quaternion((float(q[3]),*map(float,q[:3]))),Vector(value(i,'scale',time))))
 sw=worlds(s['nodes'],sp,sl);cache={}
 def target_world(j):
  if j in cache:return cache[j]
  parent=target_world(tp[j]) if j in tp else Matrix.Identity(4);local=tt[j].copy()
  if j in reverse:
   i=reverse[j];desired=sw[i].to_quaternion()@correction[j];q=parent.to_quaternion().inverted()@desired
   st=Vector(s['nodes'][i].get('translation',[0,0,0]));position=tt[j].translation+(Vector(value(i,'translation',time))-st)*(tt[j].translation.length/st.length if st.length>.05 else 1);scale=tt[j].to_scale();local=Matrix.LocRotScale(position,q,scale)
   out[j,'translation'].append(list(position));out[j,'rotation'].append([q.x,q.y,q.z,q.w]);out[j,'scale'].append(list(scale))
  cache[j]=parent@local;return cache[j]
 for j in range(len(g['nodes'])):target_world(j)
blob=bytearray(blob0)
def add(data,kind):
 data=np.asarray(data,dtype='<f4');blob.extend(b'\0'*((-len(blob))%4));offset=len(blob);raw=data.tobytes();blob.extend(raw);vi=len(g['bufferViews']);g['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':len(raw)});ac={'bufferView':vi,'componentType':5126,'count':len(data),'type':kind}
 if kind=='SCALAR':ac.update(min=[float(data.min())],max=[float(data.max())])
 ai=len(g['accessors']);g['accessors'].append(ac);return ai
times=add(np.arange(count)/30,'SCALAR');clip={'name':s['animations'][0]['name']+'-world-Paladin','channels':[],'samplers':[]}
for (j,p),data in out.items():
 ai=add(data,'VEC4' if p=='rotation' else 'VEC3');clip['channels'].append({'sampler':len(clip['samplers']),'target':{'node':j,'path':p}});clip['samplers'].append({'input':times,'output':ai,'interpolation':'LINEAR'})
g['animations']=[clip];g['buffers'][0]['byteLength']=len(blob)
for k in ['nodes','meshes','skins','materials','images']:assert g.get(k)==original.get(k)
text=json.dumps(g,separators=(',',':')).encode();text+=b' '*((-len(text))%4);blob.extend(b'\0'*((-len(blob))%4));dest.parent.mkdir(parents=True,exist_ok=True);assert dest.resolve()!=target.resolve();dest.write_bytes(struct.pack('<III',0x46546c67,2,28+len(text)+len(blob))+struct.pack('<II',len(text),0x4e4f534a)+text+struct.pack('<II',len(blob),0x004e4942)+blob);dest.with_suffix('.retarget.json').write_text(json.dumps({'method':'source animated global * inverse source rest global * target rest global','mapped_joints':len(mapping),'frames':count,'geometry_bind_materials_unchanged':True},indent=2));print('World-retargeted',count,'frames and',len(mapping),'joints')
