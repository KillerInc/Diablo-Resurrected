"""Extract exact skeletal animation data from a private donor, excluding artwork."""
import argparse,copy,json,struct,hashlib
from pathlib import Path
import numpy as np
from merge_paladin_walk import read

def extract(source,destination):
 source,destination=map(Path,(source,destination));doc,blob=read(source);assert doc.get('animations')
 used={s[k] for a in doc['animations'] for s in a['samplers'] for k in ('input','output')}
 result={k:copy.deepcopy(doc[k]) for k in ('asset','scene','scenes','nodes','animations') if k in doc}
 for n in result['nodes']:
  for key in ('mesh','skin','camera','extensions'):n.pop(key,None)
 result.update(bufferViews=[],accessors=[],buffers=[]);binary=bytearray();mapping={};widths={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}
 for old in sorted(used):
  ac=copy.deepcopy(doc['accessors'][old]);assert ac['componentType']==5126 and 'sparse' not in ac
  view=doc['bufferViews'][ac['bufferView']];width=widths[ac['type']];offset=view.get('byteOffset',0)+ac.get('byteOffset',0)
  values=np.ndarray((ac['count'],width),dtype='<f4',buffer=blob,offset=offset,strides=(view.get('byteStride',width*4),4)).copy().tobytes();binary.extend(b'\0'*((-len(binary))%4));start=len(binary);binary.extend(values)
  ac['bufferView']=len(result['bufferViews']);ac.pop('byteOffset',None);result['bufferViews'].append({'buffer':0,'byteOffset':start,'byteLength':len(values)});mapping[old]=len(result['accessors']);result['accessors'].append(ac)
 for clip in result['animations']:
  for sampler in clip['samplers']:
   for field in ('input','output'):sampler[field]=mapping[sampler[field]]
 result['buffers']=[{'byteLength':len(binary)}];text=json.dumps(result,separators=(',',':')).encode();text+=b' '*((-len(text))%4);binary.extend(b'\0'*((-len(binary))%4));destination.parent.mkdir(parents=True,exist_ok=True);assert destination.resolve()!=source.resolve()
 destination.write_bytes(struct.pack('<III',0x46546c67,2,28+len(text)+len(binary))+struct.pack('<II',len(text),0x4e4f534a)+text+struct.pack('<II',len(binary),0x004e4942)+binary)
 assert result['nodes']==[{k:v for k,v in n.items() if k not in ('mesh','skin','camera','extensions')} for n in doc['nodes']]
 check,check_blob=read(destination)
 for old in used:
  original=doc['accessors'][old];current=check['accessors'][mapping[old]];width=widths[original['type']];ov=doc['bufferViews'][original['bufferView']];nv=check['bufferViews'][current['bufferView']]
  a=np.ndarray((original['count'],width),dtype='<f4',buffer=blob,offset=ov.get('byteOffset',0)+original.get('byteOffset',0),strides=(ov.get('byteStride',width*4),4))
  b=np.ndarray((current['count'],width),dtype='<f4',buffer=check_blob,offset=nv.get('byteOffset',0),strides=(width*4,4))
  assert a.tobytes()==b.tobytes(),'Compacted sampler data changed'
 assert not check.get('meshes') and not check.get('images')

 return {'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'motion_sha256':hashlib.sha256(destination.read_bytes()).hexdigest(),'clips':[a.get('name') for a in doc['animations']],'exact_sampler_data':True,'artwork_included':False}

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('source');p.add_argument('destination');a=p.parse_args();print(json.dumps(extract(a.source,a.destination)))
