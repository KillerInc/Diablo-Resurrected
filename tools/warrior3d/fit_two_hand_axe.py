"""Shorten only A1's unused lower haft in a private copy; preserve source art.

python SCRIPT ORIGINAL_A1.glb FITTED_A1.glb
Blender mesh +Y corresponds to glTF -Z for this identity-node local asset.
"""
import copy,hashlib,json,struct,sys
from pathlib import Path
import numpy as np
from merge_paladin_walk import read
source,dest=map(Path,sys.argv[1:]);assert source.resolve()!=dest.resolve();g,original=read(source);old=copy.deepcopy(g);blob=bytearray(original);assert g['nodes']==[{'mesh':0}] and len(g['meshes'])==1;changed=0
for primitive in g['meshes'][0]['primitives']:
 a=g['accessors'][primitive['attributes']['POSITION']];v=g['bufferViews'][a['bufferView']];assert a['componentType']==5126 and a['type']=='VEC3' and not v.get('byteStride');positions=np.frombuffer(blob,dtype='<f4',count=a['count']*3,offset=v.get('byteOffset',0)+a.get('byteOffset',0)).reshape(-1,3);before=positions.copy();tail=-positions[:,2];mask=tail>.24;old_end=float(tail.max());assert .36<old_end<.37;positions[mask,2]=-(.24+(tail[mask]-.24)*(.29-.24)/(old_end-.24));changed+=int(mask.sum());assert np.array_equal(positions[:,:2],before[:,:2]) and np.array_equal(positions[~mask],before[~mask]);a.update(min=positions.min(0).tolist(),max=positions.max(0).tolist())
for field in ['nodes','meshes','materials','images','textures','skins']:assert g.get(field)==old.get(field),field
text=json.dumps(g,separators=(',',':')).encode();text+=b' '*((-len(text))%4);blob.extend(b'\0'*((-len(blob))%4));dest.parent.mkdir(exist_ok=True,parents=True);dest.write_bytes(struct.pack('<III',0x46546c67,2,28+len(text)+len(blob))+struct.pack('<II',len(text),0x4e4f534a)+text+struct.pack('<II',len(blob),0x004e4942)+blob);report={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'changed_tail_vertices':changed,'old_positive_y_end':old_end,'new_positive_y_end':.29,'shortened_meters':old_end-.29,'head_textures_materials_and_other_geometry_preserved':True};dest.with_suffix('.fit.json').write_text(json.dumps(report,indent=2));print(report)
