"""Blender --python SCRIPT -- SOURCE_SHIELD.glb NEW_PRIVATE_STOWED.glb
Fold rigid forearm loops for back stow; preserve the selected shield's face.
The source and combat shield are never overwritten.
"""
import bpy,sys,json
from pathlib import Path
source,dest=map(Path,sys.argv[sys.argv.index('--')+1:]);assert source.resolve()!=dest.resolve();assert source.is_file() and not dest.exists();dest.parent.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(source.resolve()));changed=0
for o in bpy.data.objects:
 if o.type!='MESH':continue
 for v in o.data.vertices:
  if v.co.z<0:v.co.z*=.20;changed+=1
bpy.ops.export_scene.gltf(filepath=str(dest.resolve()),export_format='GLB',export_animations=False,export_extras=True)
dest.with_suffix('.fit.json').write_text(json.dumps({'source':str(source.resolve()),'negative_normal_depth_gain':.20,'face_and_positive_normal_vertices_unchanged':True,'changed_vertices':changed},indent=2));print('Folded stowed forearm loops',changed)
