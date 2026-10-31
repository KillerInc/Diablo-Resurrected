"""Blender material pass: replace red armor paint with dark gray; keep gold and detail."""
import bpy,numpy as np,json,hashlib
from pathlib import Path

def apply(output):
 output=Path(output);output.mkdir(parents=True,exist_ok=True);records=[];seen=set()
 for obj in bpy.context.scene.objects:
  if obj.type!='MESH' or obj.hide_render:continue
  for slot in obj.material_slots:
   material=slot.material
   if not material or material.name in seen or 'sets57' not in material.name.lower():continue
   seen.add(material.name);bsdf=next(n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED');socket=bsdf.inputs['Base Color'];assert socket.is_linked
   node=socket.links[0].from_node;assert node.type=='TEX_IMAGE' and node.image
   original=node.image;image=original.copy();image.name=original.name+' dark gray armor'
   pixels=np.empty(len(image.pixels),dtype=np.float32);image.pixels.foreach_get(pixels);rgba=pixels.reshape(-1,4);rgb=rgba[:,:3];before_alpha=rgba[:,3].copy();r,g,b=rgb[:,0].copy(),rgb[:,1].copy(),rgb[:,2].copy();den=np.maximum(r,1e-6)
   red=np.clip(((r-g)/den-.20)/.18,0,1)*np.clip(((r-b)/den-.08)/.18,0,1)
   gold=(g/den>.58)&(r>b*1.15);red[gold]=0
   luminance=rgb@np.array([.2126,.7152,.0722],dtype=np.float32);gray=luminance[:,None]*np.array([.60,.63,.67],dtype=np.float32)
   rgb[:]=np.clip(rgb*(1-red[:,None])+gray*red[:,None],0,1);assert np.array_equal(rgba[:,3],before_alpha)
   image.pixels.foreach_set(pixels);image.update();image.filepath_raw=str(output/(material.name.replace('/','_')+'-dark-gray.png'));image.file_format='PNG';image.save();image.pack();node.image=image
   records.append({'material':material.name,'changed_texels':int((red>.01).sum()),'gold_texels_protected':int(gold.sum()),'alpha_unchanged':True})
 (output/'material-pass.json').write_text(json.dumps({'pass':'red armor to dark gray','materials':records,'geometry_uv_weights_modified':False,'gold_trim_protected':True,'normal_roughness_metallic_maps_unchanged':True},indent=2));return records
