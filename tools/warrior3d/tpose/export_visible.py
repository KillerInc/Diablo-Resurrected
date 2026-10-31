"""Export the visible repaired character and rig from the loaded Blender scene."""
import bpy,sys
from pathlib import Path
out=Path(sys.argv[sys.argv.index('--')+1]).resolve();out.parent.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='DESELECT')
for obj in bpy.data.objects:
    if obj.type=='ARMATURE' or (obj.type=='MESH' and not obj.hide_render):obj.select_set(True)
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.gltf(filepath=str(out),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='ACTIONS')
print('EXPORTED_VISIBLE_CHARACTER',out)
