"""Capture approved attachment transforms from a local Blender scene.

Blender --python SCRIPT -- APPROVED.blend REFERENCE.json OUTPUT.json
The output references private artwork and belongs outside Git.
"""
import bpy,json,sys
from pathlib import Path

def capture(scene,reference,output):
 bpy.ops.wm.open_mainfile(filepath=str(Path(scene).resolve()));rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');bpy.context.scene.frame_set(0);bpy.context.view_layer.update();ref=json.loads(Path(reference).read_text());result=[]
 for item in ref['equipment']:
  matches=[o for o in bpy.data.objects if o.get('d1r_asset')==Path(item['path']).name];assert len(matches)==1;local=(rig.matrix_world@rig.pose.bones[item['bone']].matrix).inverted()@matches[0].matrix_world;copy=dict(item);copy['local_transform']=[list(row) for row in local];result.append(copy)
 Path(output).write_text(json.dumps(result,indent=2))

if __name__=='__main__':capture(*sys.argv[sys.argv.index('--')+1:])
