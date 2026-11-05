"""Make sixteen attack poses, blending to the installed idle at both ends.

python sample_paladin_kick.py RETARGET.glb IDLE.glb OUTPUT.glb [MEASURE.json]
Optional evaluated measurements lock the supporting left foot and ground boots.
"""
import json,struct,sys
from pathlib import Path
import numpy as np
from merge_paladin_walk import read

kick,idle,dest=map(Path,sys.argv[1:4]);g,kb=read(kick);ig,ib=read(idle)
samples=[0,0,1,2,3,4,5,6,8,20,22,24,27,31,37,41]
weights=np.array([0,.3,.7,1,1,1,1,1,1,1,1,1,.85,.55,.25,0])[:,None]
weights*=.70  # Compact the Barbarian's high kick for the D1 attack cell.
def tracks(doc,blob):
 result={}
 for ch in doc['animations'][0]['channels']:
  path=ch['target']['path'];ac=doc['accessors'][doc['animations'][0]['samplers'][ch['sampler']]['output']];v=doc['bufferViews'][ac['bufferView']];width=4 if path=='rotation' else 3
  assert ac['componentType']==5126 and 'byteStride' not in v
  result[(doc['nodes'][ch['target']['node']]['name'],path)]=np.frombuffer(blob,dtype='<f4',count=ac['count']*width,offset=v.get('byteOffset',0)+ac.get('byteOffset',0)).reshape(-1,width).copy()
 return result
kt,it=tracks(g,kb),tracks(ig,ib);blob=bytearray(kb);names={n.get('name'):i for i,n in enumerate(g['nodes'])}
clip={'name':'Paladin-unarmed-kick-16','channels':[],'samplers':[]}
def add(data,kind):
 data=np.asarray(data,dtype='<f4');blob.extend(b'\0'*((-len(blob))%4));offset=len(blob);raw=data.tobytes();blob.extend(raw);vi=len(g['bufferViews']);g['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':len(raw)})
 ac={'bufferView':vi,'componentType':5126,'count':len(data),'type':kind}
 if kind=='SCALAR':ac.update(min=[float(data.min())],max=[float(data.max())])
 ai=len(g['accessors']);g['accessors'].append(ac);return ai
ti=add(np.arange(16,dtype=float)[:,None]/30,'SCALAR')
measure=json.loads(Path(sys.argv[4]).read_text()) if len(sys.argv)>4 else None
if measure:
 assert len(measure)==16 and all(abs(.003-m['boot_min_z'])<.2 for m in measure)
for key in sorted(kt.keys()|it.keys()):
 name,path=key;node=g['nodes'][names[name]];default={'rotation':[0,0,0,1],'translation':[0,0,0],'scale':[1,1,1]}[path]
 start=it[key][0] if key in it else np.array(node.get(path,default))
 posed=kt[key][samples] if key in kt else np.tile(start,(16,1))
 if path=='rotation':
  posed=posed.copy();posed[posed@start<0]*=-1
  dot=np.clip(posed@start,-1,1);angle=np.arccos(dot);den=np.sin(angle);result=np.tile(start,(16,1)).astype(float);ok=den>1e-6
  result[ok]=(np.sin((1-weights[ok])*angle[ok,None])*start+np.sin(weights[ok]*angle[ok,None])*posed[ok])/den[ok,None]
  result/=np.linalg.norm(result,axis=1,keepdims=True)
 else:result=start+(posed-start)*weights
 if measure and name=='root' and path=='translation':
  # Blender world (x,y,z) -> glTF (x,z,-y), with identity armature wrapper.
  anchor=np.array(measure[0]['bones']['foot.L'])
  for row,m in enumerate(measure):
   foot=np.array(m['bones']['foot.L']);result[row]+=np.array([anchor[0]-foot[0],.003-m['boot_min_z'],foot[1]-anchor[1]])
 clip['channels'].append({'sampler':len(clip['samplers']),'target':{'node':names[name],'path':path}});clip['samplers'].append({'input':ti,'output':add(result,'VEC4' if path=='rotation' else 'VEC3'),'interpolation':'LINEAR'})
g['animations']=[clip];g['buffers'][0]['byteLength']=len(blob);text=json.dumps(g,separators=(',',':')).encode();text+=b' '*((-len(text))%4);blob.extend(b'\0'*((-len(blob))%4))
dest.parent.mkdir(parents=True,exist_ok=True);assert dest.resolve() not in [kick.resolve(),idle.resolve()]
dest.write_bytes(struct.pack('<III',0x46546c67,2,28+len(text)+len(blob))+struct.pack('<II',len(text),0x4e4f534a)+text+struct.pack('<II',len(blob),0x004e4942)+blob)
dest.with_suffix('.sampling.json').write_text(json.dumps({'source_samples':samples,'kick_weights':weights[:,0].tolist(),'kick_motion_gain':.70,'contact_sheet_row_zero_based':8,'action_frame_one_based':9,'support_foot':'foot.L','grounded':bool(measure),'idle_first_pose_at_both_endpoints':True},indent=2))
