"""Preserve the approved shield grip while letting a native block wrist move."""
import bpy,copy
from mathutils import Matrix
def hand_relative(item,idle_model):
 if item.get('bone')!='forearm.L':return copy.deepcopy(item)
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=str(idle_model));rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');bpy.context.scene.frame_set(0);bpy.context.view_layer.update();mount=rig.pose.bones['hand.L'].matrix.inverted()@rig.pose.bones['forearm.L'].matrix@Matrix(item['local_transform']);result=copy.deepcopy(item);result.update(bone='hand.L',local_transform=[list(r) for r in mount],block_mount_revision='native-wrist-approved-grip-v1');result.pop('grip_target_bone',None);return result
