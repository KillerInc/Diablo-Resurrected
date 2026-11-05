"""Blender material pass: dark gray armor, optional dark silver trim; preserve detail."""
import bpy,numpy as np,json,hashlib
from pathlib import Path

def apply(output,gold_to_silver=False,helm_to_silver=False,bake_surface=False,black_style="none"):
 output=Path(output);output.mkdir(parents=True,exist_ok=True);records=[];seen=set()
 for obj in bpy.context.scene.objects:
  if obj.type!='MESH' or obj.hide_render:continue
  for slot in obj.material_slots:
   material=slot.material
   if not material or material.name in seen:continue
   helmet='hlm' in material.name.lower()
   if 'sets57' not in material.name.lower() and not (helm_to_silver and helmet):continue
   seen.add(material.name);bsdf=next(n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED');socket=bsdf.inputs['Base Color'];assert socket.is_linked
   node=socket.links[0].from_node;assert node.type=='TEX_IMAGE' and node.image
   original=node.image;image=bpy.data.images.new(original.name+' dark gray armor',width=original.size[0],height=original.size[1],alpha=True);image.colorspace_settings.name=original.colorspace_settings.name
   pixels=np.empty(len(original.pixels),dtype=np.float32);original.pixels.foreach_get(pixels);rgba=pixels.reshape(-1,4);rgb=rgba[:,:3];before_alpha=rgba[:,3].copy();r,g,b=rgb[:,0].copy(),rgb[:,1].copy(),rgb[:,2].copy();den=np.maximum(r,1e-6)
   red=np.clip(((r-g)/den-.20)/.18,0,1)*np.clip(((r-b)/den-.08)/.18,0,1)
   gold=(g/den>.58)&(r>b*1.15)
   if helmet and helm_to_silver:gold=np.ones_like(gold);red[:]=0
   red[gold]=0
   luminance=rgb@np.array([.2126,.7152,.0722],dtype=np.float32);gray=luminance[:,None]*np.array([.60,.63,.67],dtype=np.float32)
   rgb[:]=np.clip(rgb*(1-red[:,None])+gray*red[:,None],0,1)
   if gold_to_silver:
    silver=(luminance[:,None]*1.05+.035)*np.array([.88,.94,1.0],dtype=np.float32)
    rgb[gold]=np.clip(silver[gold],0,1)
    # Keep the original surface variation while making the trim reflective metal.
    if bake_surface:
     surfaces={}
     for socket_name,target,channel in [('Metallic',.95,2),('Roughness',.28,1)]:
      socket=bsdf.inputs[socket_name];separate=socket.links[0].from_node;assert separate.type=='SEPARATE_COLOR'
      texture=separate.inputs[0].links[0].from_node;assert texture.type=='TEX_IMAGE'
      if texture.name not in surfaces:
       source_surface=texture.image;surface=bpy.data.images.new(source_surface.name+' silver surface',width=source_surface.size[0],height=source_surface.size[1],alpha=True);surface.colorspace_settings.name=source_surface.colorspace_settings.name;initial=np.empty(len(source_surface.pixels),dtype=np.float32);source_surface.pixels.foreach_get(initial);surface.pixels.foreach_set(initial);surface.update();surfaces[texture.name]=surface;texture.image=surface
      surface=surfaces[texture.name];values=np.empty(len(surface.pixels),dtype=np.float32);surface.pixels.foreach_get(values);values=values.reshape(-1,4)
      h,w=surface.size[1],surface.size[0];mask=gold.reshape(image.size[1],image.size[0]);ys=np.minimum((np.arange(h)*mask.shape[0]/h).astype(int),mask.shape[0]-1);xs=np.minimum((np.arange(w)*mask.shape[1]/w).astype(int),mask.shape[1]-1);weight=mask[ys[:,None],xs[None,:]].ravel().astype(np.float32)
      values[:,channel]=values[:,channel]*(1-weight)+target*weight;surface.pixels.foreach_set(values.ravel());surface.update()
     for index,surface in enumerate(surfaces.values()):
      surface.filepath_raw=str(output/(material.name+f'-silver-surface-{index}.png'));surface.file_format='PNG';surface.save();surface.pack()
    else:
     nodes=material.node_tree.nodes;links=material.node_tree.links
     mask_image=bpy.data.images.new(material.name+' silver trim mask',width=image.size[0],height=image.size[1],alpha=True)
     mask_pixels=np.ones_like(rgba);mask_pixels[:,:3]=gold[:,None];mask_image.pixels.foreach_set(mask_pixels.ravel());mask_image.update();mask_image.colorspace_settings.name='Non-Color';mask_image.filepath_raw=str(output/(material.name+'-silver-mask.png'));mask_image.file_format='PNG';mask_image.save();mask_image.pack()
     mask=nodes.new('ShaderNodeTexImage');mask.image=mask_image
     for socket_name,target in [('Metallic',.95),('Roughness',.28)]:
      socket=bsdf.inputs[socket_name];mix=nodes.new('ShaderNodeMixRGB');mix.blend_type='MIX';links.new(mask.outputs['Color'],mix.inputs[0]);mix.inputs[2].default_value=(target,target,target,1)
      if socket.is_linked:links.new(socket.links[0].from_socket,mix.inputs[1])
      else:
       value=socket.default_value;mix.inputs[1].default_value=(value,value,value,1)
      links.new(mix.outputs[0],socket)
   if black_style!='none' and not helmet:
    assert black_style in ('undersuit','plates','both')
    undersuit=(1-gold.astype(np.float32))*(1-red)*np.clip((.65-np.maximum.reduce([r,g,b]))/.35,0,1)
    plates=red*(1-gold.astype(np.float32))
    accent=undersuit if black_style=='undersuit' else (plates if black_style=='plates' else np.maximum(undersuit,plates))
    black=(rgb@np.array([.2126,.7152,.0722],dtype=np.float32))[:,None]*np.array([.10,.10,.10],dtype=np.float32);rgb[:]=rgb*(1-accent[:,None])+black*accent[:,None]
   assert np.array_equal(rgba[:,3],before_alpha)
   image.pixels.foreach_set(pixels);image.update();image.filepath_raw=str(output/(material.name.replace('/','_')+'-dark-gray.png'));image.file_format='PNG';image.save();image.pack();node.image=image
   records.append({'material':material.name,'changed_texels':int((red>.01).sum()),'gold_texels_protected':int(gold.sum()),'alpha_unchanged':True})
 (output/'material-pass.json').write_text(json.dumps({'black_style':black_style,'surface_parameters_baked':bake_surface,'pass':'red armor to dark gray','helm_to_silver':helm_to_silver,'materials':records,'geometry_uv_weights_modified':False,'gold_trim_protected':not gold_to_silver,'gold_to_dark_silver':gold_to_silver,'normal_maps_unchanged':True,'trim_metallic':.95 if gold_to_silver else None,'trim_roughness':.28 if gold_to_silver else None},indent=2));return records
