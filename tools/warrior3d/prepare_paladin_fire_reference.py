"""Prepare the grounded original-size FM layout for the authored cast.

Blender --python SCRIPT -- CAST.glb ORIGINAL_REFERENCE.json OUTPUT.json
Inputs stay local/read-only. Geometry supplies floor contact, not image bounds.
"""
import bpy,json,sys
from pathlib import Path
import numpy as np
source,template,destination=map(Path,sys.argv[sys.argv.index('--')+1:]);assert destination.resolve()!=template.resolve();ref=json.loads(template.read_text());assert ref['sheet']=='wlnfm.png' and ref['rows']==20 and ref['cell']==768
bpy.context.scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=str(source.resolve()));rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');rig.rotation_mode='XYZ';rig.rotation_euler=(0,0,0)
parts=[o for o in bpy.data.objects if o.type=='MESH' and o.data.materials and any(t in o.data.materials[0].name for t in ['base16_TRS','armor_skin','P00_HED','base01_GLV','base01_LEG','base05_BTS'])];assert len(parts)==6;floor=[]
for row in range(20):
 bpy.context.scene.frame_set(row);bpy.context.view_layer.update();minimum=float('inf')
 for o in parts:
  ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh();v=np.empty(len(mesh.vertices)*3,dtype=np.float32);mesh.vertices.foreach_get('co',v);mat=np.array(ev.matrix_world);p=v.reshape(-1,3)@mat[:3,:3].T+mat[:3,3];minimum=min(minimum,float(p[:,2].min()));ev.to_mesh_clear()
 floor.append(minimum)
ref.update(source_frames=list(range(20)),preserve_horizontal_root_motion=True,pose_offsets=[[0,0,floor[0]-v] for v in floor],sun_position=[3,-4,6],shadow_distance_gain=1,shadow_overscan=512,fire_effect={'seed':2718},canvas_logical=96,canvas_anchor=[48,96],preview_prefix='fire-remade',preview_anchor=False,preview_contact_row=13,preview_caption='Remade fire | adapted firewall motion | frame 14 release')
destination.parent.mkdir(parents=True,exist_ok=True);destination.write_text(json.dumps(ref,indent=2));destination.with_suffix('.grounding.json').write_text(json.dumps({'native_floor_by_frame':floor,'constant_floor':floor[0],'pose_offsets':ref['pose_offsets'],'model_rescaled':False},indent=2));print('Prepared original FM layout and twenty vertical-only floor offsets')
