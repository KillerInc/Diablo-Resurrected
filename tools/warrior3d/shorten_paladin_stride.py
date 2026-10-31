"""Shorten gait animation buffers while preserving the source GLB mesh binding.

python SCRIPT INPUT.glb OUTPUT.glb [GROUND_CORRECTION.json]
Leg rotation excursion is 60%; pelvis motion is 50%. Sample times are untouched.
Optional boot-ground corrections are added to the root Y translation.
"""
import json,struct,sys
from pathlib import Path
import numpy as np
src,dest=map(Path,sys.argv[1:3]);data=src.read_bytes();n=struct.unpack_from('<I',data,12)[0];g=json.loads(data[20:20+n]);blob=bytearray(data[28+n:]);changed=[]
ground=json.loads(Path(sys.argv[3]).read_text()) if len(sys.argv)>3 else None
for clip in g['animations']:
 for channel in clip['channels']:
  name=g['nodes'][channel['target']['node']]['name'];path=channel['target']['path'];sampler=clip['samplers'][channel['sampler']];a=g['accessors'][sampler['output']];view=g['bufferViews'][a['bufferView']]
  assert a['componentType']==5126 and 'byteStride' not in view and 'sparse' not in a
  offset=view.get('byteOffset',0)+a.get('byteOffset',0)
  if name in ['thigh.L','thigh.R','shin.L','shin.R','foot.L','foot.R'] and path=='rotation':
   values=np.frombuffer(blob,dtype='<f4',count=a['count']*4,offset=offset).reshape(-1,4).copy();values[values@values[0]<0]*=-1
   mean=values.mean(0);mean/=np.linalg.norm(mean);angle=np.arccos(np.clip(values@mean,-1,1));den=np.sin(angle);safe=den>1e-6
   result=values.copy();result[safe]=(np.sin(angle[safe]*.4)[:,None]*mean+np.sin(angle[safe]*.6)[:,None]*values[safe])/den[safe,None]
   result/=np.linalg.norm(result,axis=1)[:,None];blob[offset:offset+result.nbytes]=result.astype('<f4').tobytes();changed.append(name)
  if name=='pelvis' and path=='translation':
   values=np.frombuffer(blob,dtype='<f4',count=a['count']*3,offset=offset).reshape(-1,3).copy();mean=values.mean(0);result=mean+(values-mean)*.5;blob[offset:offset+result.nbytes]=result.astype('<f4').tobytes()
  if ground and name=='root' and path=='translation':
   values=np.frombuffer(blob,dtype='<f4',count=a['count']*3,offset=offset).reshape(-1,3).copy();correction=np.array(ground['root_vertical_correction']);assert len(correction)==len(values) and abs(correction).max()<.2
   values[:,1]+=correction;blob[offset:offset+values.nbytes]=values.astype('<f4').tobytes()
dest.parent.mkdir(parents=True,exist_ok=True);assert src.resolve()!=dest.resolve();dest.write_bytes(data[:28+n]+blob)
dest.with_suffix('.stride.json').write_text(json.dumps({'leg_rotation_gain':.6,'pelvis_motion_gain':.5,'changed_leg_bones':changed,'ground_correction':ground,'mesh_skin_nodes_and_material_records_unchanged':True,'original_sample_times_preserved':True},indent=2))

