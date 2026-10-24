"""Extract one exact named clip from an animation-only GLB, compacting its data.

python SCRIPT ALL_ANIMATIONS.glb CLIP_NAME OUTPUT.glb
Node/skin hierarchy is preserved. Mesh-containing input is deliberately rejected.
"""
import copy,json,struct,sys
from pathlib import Path
import numpy as np
from merge_paladin_walk import read

source,name,destination=sys.argv[1:4];doc,binary=read(source)
assert not doc.get('meshes') and not doc.get('images'),'Animation-only input required'
matches=[a for a in doc['animations'] if a.get('name')==name];assert len(matches)==1,('exact clip not found',name)
clip=copy.deepcopy(matches[0]);used={s[k] for s in clip['samplers'] for k in ['input','output']}
used|={s['inverseBindMatrices'] for s in doc.get('skins',[]) if 'inverseBindMatrices' in s}
result={k:copy.deepcopy(v) for k,v in doc.items() if k not in ['buffers','bufferViews','accessors','animations']}
result.update(buffers=[],bufferViews=[],accessors=[],animations=[clip]);blob=bytearray();mapping={}
widths={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}
for old in sorted(used):
    ac=copy.deepcopy(doc['accessors'][old]);assert ac['componentType']==5126 and 'sparse' not in ac
    view=doc['bufferViews'][ac['bufferView']];assert view.get('buffer',0)==0
    width=widths[ac['type']];offset=view.get('byteOffset',0)+ac.get('byteOffset',0);stride=view.get('byteStride',width*4)
    data=np.ndarray((ac['count'],width),dtype='<f4',buffer=binary,offset=offset,strides=(stride,4)).copy().tobytes()
    blob.extend(b'\0'*((-len(blob))%4));start=len(blob);blob.extend(data)
    ac['bufferView']=len(result['bufferViews']);ac.pop('byteOffset',None)
    result['bufferViews'].append({'buffer':0,'byteOffset':start,'byteLength':len(data)})
    mapping[old]=len(result['accessors']);result['accessors'].append(ac)
for sampler in clip['samplers']:
    for key in ['input','output']:sampler[key]=mapping[sampler[key]]
for skin in result.get('skins',[]):
    if 'inverseBindMatrices' in skin:skin['inverseBindMatrices']=mapping[skin['inverseBindMatrices']]
result['buffers']=[{'byteLength':len(blob)}];text=json.dumps(result,separators=(',',':')).encode();text+=b' '*((-len(text))%4);blob.extend(b'\0'*((-len(blob))%4))
dest=Path(destination);dest.parent.mkdir(parents=True,exist_ok=True);assert dest.resolve()!=Path(source).resolve()
dest.write_bytes(struct.pack('<III',0x46546c67,2,28+len(text)+len(blob))+struct.pack('<II',len(text),0x4e4f534a)+text+struct.pack('<II',len(blob),0x004e4942)+blob)
print('Selected',name,'->',dest,';',len(blob),'binary bytes')
