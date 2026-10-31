"""Attach a matching animation-only GLB without rewriting character meshes.

python merge_paladin_walk.py CHARACTER.glb ANIMATION.glb OUTPUT.glb
Checks local rest transforms and parent names for every animated node.
"""
import copy,json,struct,sys,math
from pathlib import Path

def read(path):
 data=Path(path).read_bytes();magic,version,total=struct.unpack_from('<III',data)
 assert magic==0x46546c67 and version==2 and total==len(data)
 offset=12;doc=None;blob=b''
 while offset<len(data):
  size,kind=struct.unpack_from('<II',data,offset);chunk=data[offset+8:offset+8+size];offset+=8+size
  if kind==0x4e4f534a:doc=json.loads(chunk)
  elif kind==0x004e4942:blob=chunk
 assert doc is not None
 return doc,blob

def matrix(node):
 if 'matrix' in node:return node['matrix']
 x,y,z,w=node.get('rotation',[0,0,0,1]);s=node.get('scale',[1,1,1]);t=node.get('translation',[0,0,0])
 return [(1-2*(y*y+z*z))*s[0],2*(x*y+z*w)*s[0],2*(x*z-y*w)*s[0],0,
         2*(x*y-z*w)*s[1],(1-2*(x*x+z*z))*s[1],2*(y*z+x*w)*s[1],0,
         2*(x*z+y*w)*s[2],2*(y*z-x*w)*s[2],(1-2*(x*x+y*y))*s[2],0,*t,1]

def logical_parent(doc,parents,index,animated_names):
 parent=parents.get(index);joints={joint for skin in doc.get('skins',[]) for joint in skin.get('joints',[])}
 while parent is not None:
  node=doc['nodes'][parent];identity=max(abs(x-y) for x,y in zip(matrix(node),matrix({})))<1e-6
  wrapper=node.get('name','').lower().startswith('armature') and parent not in joints and node.get('name') not in animated_names and identity
  if not wrapper:return node.get('name')
  parent=parents.get(parent)
 return None

def merge(character,animation,destination):
 c,cb=read(character);a,ab=read(animation);original=copy.deepcopy(c)
 assert not c.get('animations'),'Do not silently replace existing character animations'
 cn={n['name']:i for i,n in enumerate(c['nodes']) if 'name' in n}
 ap={ch:i for i,n in enumerate(a['nodes']) for ch in n.get('children',[])}
 cp={ch:i for i,n in enumerate(c['nodes']) for ch in n.get('children',[])}
 targets={ch['target']['node'] for clip in a['animations'] for ch in clip['channels']}
 animated_names={a['nodes'][i]['name'] for i in targets}
 max_delta=0
 for i in targets:
  name=a['nodes'][i]['name'];assert name in cn,('missing bone',name)
  j=cn[name];delta=max(abs(x-y) for x,y in zip(matrix(a['nodes'][i]),matrix(c['nodes'][j])))
  max_delta=max(max_delta,delta);assert delta<1e-4,('incompatible rest transform',name,delta)
  # Exporters may add an unanimated identity Armature wrapper on either side.
  # Compare logical parents without modifying either hierarchy or bind matrix.
  assert logical_parent(a,ap,i,animated_names)==logical_parent(c,cp,j,animated_names),('different parent',name)
 viewbase=len(c.get('bufferViews',[]));accbase=len(c.get('accessors',[]));offset=len(cb)
 for v in a.get('bufferViews',[]):
  v=copy.deepcopy(v);assert v.get('buffer',0)==0;v['byteOffset']=v.get('byteOffset',0)+offset;c['bufferViews'].append(v)
 for ac in a.get('accessors',[]):
  ac=copy.deepcopy(ac);assert 'sparse' not in ac;ac['bufferView']+=viewbase;c['accessors'].append(ac)
 c['animations']=copy.deepcopy(a['animations'])
 for clip in c['animations']:
  for sampler in clip['samplers']:sampler['input']+=accbase;sampler['output']+=accbase
  for channel in clip['channels']:channel['target']['node']=cn[a['nodes'][channel['target']['node']]['name']]
 blob=cb+ab;c['buffers'][0]['byteLength']=len(blob)
 assert c['meshes']==original['meshes'] and c['skins']==original['skins'] and c['nodes']==original['nodes']
 text=json.dumps(c,separators=(',',':')).encode();text+=b' '*((-len(text))%4);blob+=b'\0'*((-len(blob))%4)
 packed=struct.pack('<III',0x46546c67,2,28+len(text)+len(blob))+struct.pack('<II',len(text),0x4e4f534a)+text+struct.pack('<II',len(blob),0x004e4942)+blob
 destination=Path(destination);destination.parent.mkdir(parents=True,exist_ok=True);assert destination.resolve()!=Path(character).resolve()
 destination.write_bytes(packed)
 result={'animated_bones_matched':len(targets),'max_rest_matrix_difference':max_delta,'mesh_skin_and_nodes_unchanged':True,'clips':[x.get('name') for x in c['animations']]}
 destination.with_suffix('.validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))

if __name__=='__main__':merge(*sys.argv[1:4])
