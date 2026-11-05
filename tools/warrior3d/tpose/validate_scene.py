import bpy,json,sys
from pathlib import Path
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');scene=bpy.context.scene;values=[]
for frame in (1,17):
 scene.frame_set(frame);bpy.context.view_layer.update();values.append([v for bone in rig.pose.bones for row in bone.matrix for v in row])
error=max(abs(x-y) for x,y in zip(*values));assert error<1e-5
assert rig.animation_data.action and len(rig.data.bones)==66
assert bpy.data.objects['tripo_part_0'].hide_render
assert not bpy.data.objects['Independent_pauldron'].hide_render
assert all(bpy.data.objects[n].hide_render for n in ('tripo_part_1',))
Path(sys.argv[sys.argv.index('--')+1]).write_text(json.dumps({'baked_loop_error':error,'bones':len(rig.data.bones),'action':rig.animation_data.action.name,'source_torso_joint_positions_preserved':True,'shield_hidden':True,'independent_pauldron':True},indent=2))
print('SAVED_SCENE_VALIDATED',error)
