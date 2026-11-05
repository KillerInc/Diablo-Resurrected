"""Create a red-wood H3 variant by splitting its wood/metal material assignment.

python SCRIPT ORIGINAL.glb OUTPUT.glb
Uses the existing metallic texture to classify triangle interiors. Embedded
images and position/normal/UV buffers are retained byte-for-byte, as are all
triangles; the original source is never overwritten. No artwork is embedded.
"""
import copy,io,json,struct,sys,hashlib
from pathlib import Path
import numpy as np
from PIL import Image
from merge_paladin_walk import read

source,destination=map(Path,sys.argv[1:3]);assert source.resolve()!=destination.resolve()
g,raw=read(source);original=copy.deepcopy(g);blob=bytearray(raw)
assert len(g['meshes'])==1 and len(g['meshes'][0]['primitives'])==1 and len(g['materials'])==1
primitive=g['meshes'][0]['primitives'][0];material=g['materials'][primitive.get('material',0)]
assert material['name']=='1HShield_S15_Warrior'
def array(index):
 a=g['accessors'][index];v=g['bufferViews'][a['bufferView']];dtype={5126:'<f4',5125:'<u4',5123:'<u2'}[a['componentType']];width={'VEC2':2,'VEC3':3,'SCALAR':1}[a['type']];assert 'byteStride' not in v
 return np.frombuffer(raw,dtype=dtype,count=a['count']*width,offset=v.get('byteOffset',0)+a.get('byteOffset',0)).reshape(-1,width).copy()
uv=array(primitive['attributes']['TEXCOORD_0']);triangles=array(primitive['indices']).reshape(-1,3)
texture=g['textures'][material['pbrMetallicRoughness']['metallicRoughnessTexture']['index']];v=g['bufferViews'][g['images'][texture['source']]['bufferView']];image=Image.open(io.BytesIO(raw[v.get('byteOffset',0):v.get('byteOffset',0)+v['byteLength']])).convert('RGB');metal=np.asarray(image)[:,:,2]/255
# Interior samples avoid UV seams. Face categories remain rigid geometry.
weights=np.array([[1/3]*3,[.6,.2,.2],[.2,.6,.2],[.2,.2,.6]])
samples=np.einsum('sk,tkc->tsc',weights,uv[triangles])%1
x=np.minimum((samples[:,:,0]*image.width).astype(int),image.width-1);y=np.minimum((samples[:,:,1]*image.height).astype(int),image.height-1)
scores=metal[y,x].mean(axis=1);wood=scores<.45;assert wood.any() and (~wood).any()
red=copy.deepcopy(material);red['name']='H3 worn red wood';red['pbrMetallicRoughness']['baseColorFactor']=[1,.075,.05,1];g['materials'].append(red)
parts=[]
for mask,mat in [(~wood,0),(wood,1)]:
 data=np.asarray(triangles[mask],dtype='<u4').ravel();blob.extend(b'\0'*((-len(blob))%4));offset=len(blob);blob.extend(data.tobytes());view=len(g['bufferViews']);g['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':data.nbytes,'target':34963});accessor=len(g['accessors']);g['accessors'].append({'bufferView':view,'componentType':5125,'count':len(data),'type':'SCALAR'});p=copy.deepcopy(primitive);p.update(indices=accessor,material=mat);parts.append(p)
g['meshes'][0]['primitives']=parts;g['buffers'][0]['byteLength']=len(blob)
assert g['nodes']==original['nodes'] and g['images']==original['images'] and g['textures']==original['textures']
assert len(triangles[wood])+len(triangles[~wood])==len(triangles)
assert blob[:len(raw)]==raw
text=json.dumps(g,separators=(',',':')).encode();text+=b' '*((-len(text))%4);blob.extend(b'\0'*((-len(blob))%4));destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(struct.pack('<III',0x46546c67,2,28+len(text)+len(blob))+struct.pack('<II',len(text),0x4e4f534a)+text+struct.pack('<II',len(blob),0x004e4942)+blob)
report={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'output_sha256':hashlib.sha256(destination.read_bytes()).hexdigest(),'wood_triangles':int(wood.sum()),'metal_triangles':int((~wood).sum()),'all_triangles_preserved':True,'original_images_and_geometry_buffers_unchanged':True,'red_base_color_factor':[1,.075,.05,1]};destination.with_suffix('.validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
