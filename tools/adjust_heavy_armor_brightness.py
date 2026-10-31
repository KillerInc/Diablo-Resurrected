"""Lift heavy armor base-color exposure; preserve geometry, alpha and other maps."""
import argparse,copy,hashlib,io,json,struct
from pathlib import Path
import numpy as np
from PIL import Image
from warrior3d.merge_paladin_walk import read

def adjust(source,destination,stops=.5):
 source,destination=map(Path,(source,destination));assert source.resolve()!=destination.resolve() and not destination.exists()
 document,blob=read(source);original=copy.deepcopy(document);prefix=bytes(blob);assert len(document['buffers'])==1
 gain=2**stops;changed=[];textures={}
 for material in document.get('materials',[]):
  if not any(token in material.get('name','').lower() for token in ('sets57','hlm')):continue
  pbr=material.get('pbrMetallicRoughness',{});info=pbr.get('baseColorTexture')
  if not info:continue
  old_index=info['index'];texture=document['textures'][old_index];assert 'source' in texture
  image_index=texture['source']
  if image_index not in textures:
   image=document['images'][image_index];assert 'bufferView' in image;view=document['bufferViews'][image['bufferView']];start=view.get('byteOffset',0);raw=blob[start:start+view['byteLength']]
   with Image.open(io.BytesIO(raw)) as im:rgba=np.array(im.convert('RGBA'))
   alpha=rgba[:,:,3].copy();rgb=rgba[:,:,:3].astype(np.float32)/255;linear=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4);linear=np.minimum(linear*gain,1);encoded=np.where(linear<=.0031308,linear*12.92,1.055*linear**(1/2.4)-.055);rgba[:,:,:3]=np.rint(np.clip(encoded,0,1)*255).astype(np.uint8);assert np.array_equal(rgba[:,:,3],alpha)
   output=io.BytesIO();Image.fromarray(rgba).save(output,format='PNG');data=output.getvalue();blob+=b'\0'*((-len(blob))%4);offset=len(blob);blob+=data
   view_index=len(document['bufferViews']);document['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':len(data)});new_image=copy.deepcopy(image);new_image.update(bufferView=view_index,mimeType='image/png',name=image.get('name','Armor')+f' exposure {stops:+g} EV');new_image.pop('uri',None);new_image_index=len(document['images']);document['images'].append(new_image)
   new_texture=copy.deepcopy(texture);new_texture['source']=new_image_index;new_texture_index=len(document['textures']);document['textures'].append(new_texture);textures[image_index]=new_texture_index
  info['index']=textures[image_index];changed.append(material['name'])
 assert len(changed)==5,('Unexpected armor materials; inspect source',changed)
 for key in ('meshes','nodes','skins','accessors','animations'):assert document.get(key)==original.get(key)
 for before,after in zip(original['materials'],document['materials']):
  expected=copy.deepcopy(after)
  if before.get('pbrMetallicRoughness',{}).get('baseColorTexture'):expected['pbrMetallicRoughness']['baseColorTexture']['index']=before['pbrMetallicRoughness']['baseColorTexture']['index']
  assert expected==before
 assert blob[:len(prefix)]==prefix
 document['buffers'][0]['byteLength']=len(blob);header=json.dumps(document,separators=(',',':')).encode();header+=b' '*((-len(header))%4);blob+=b'\0'*((-len(blob))%4)
 packed=struct.pack('<III',0x46546c67,2,28+len(header)+len(blob))+struct.pack('<II',len(header),0x4e4f534a)+header+struct.pack('<II',len(blob),0x004e4942)+blob;destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(packed)
 proof={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'output_sha256':hashlib.sha256(packed).hexdigest(),'exposure_stops':stops,'scene_linear_gain':gain,'materials':changed,'geometry_uv_weights_nodes_unchanged':True,'alpha_unchanged':True,'normals_metallic_roughness_unchanged':True,'original_binary_prefix_unchanged':True,'source_untouched':True};destination.with_suffix('.brightness.json').write_text(json.dumps(proof,indent=2));print(json.dumps(proof));return proof
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('destination',type=Path);p.add_argument('--stops',type=float,default=.5);a=p.parse_args();adjust(a.source,a.destination,a.stops)
