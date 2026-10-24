"""Validate that the outer pauldron rim lowers with the arm, without hinge drift."""
import bpy,json,sys
from pathlib import Path
from mathutils import Vector
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');plate=bpy.data.objects['Independent_pauldron'];scene=bpy.context.scene;up=(rig.matrix_world.to_3x3()@Vector((0,0,1))).normalized();inv=rig.matrix_world.inverted();ids=[v.index for v in plate.data.vertices if (inv@plate.matrix_world@v.co).x>.17];heights=[];drift=[]
for frame in range(1,10):
 scene.frame_set(frame);bpy.context.view_layer.update();ev=plate.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh();heights.append(sum((ev.matrix_world@mesh.vertices[i].co).dot(up) for i in ids)/len(ids));ev.to_mesh_clear()
 bone=rig.pose.bones['Pauldron_Hinge'];drift.append((bone.matrix.translation-rig.data.bones[bone.name].head_local).length)
assert all(b>=a-1e-6 for a,b in zip(heights,heights[1:])),('Reversed pauldron follow',heights)
assert heights[-1]-heights[0]>.005
assert max(drift)<1e-6
report={'outer_rim_heights_arms_down_to_raised':heights,'outer_rim_drop_when_arm_lowers':heights[-1]-heights[0],'maximum_hinge_drift':max(drift),'monotonic_arm_follow':True}
Path(sys.argv[sys.argv.index('--')+1]).write_text(json.dumps(report,indent=2));print('PAULDRON_FOLLOW_PASS',json.dumps(report))
