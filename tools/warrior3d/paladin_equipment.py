"""Attach local rigid equipment to native animated weapon sockets.

Preserves source mesh coordinates/materials. Optional instance transforms fit
equipment without rewriting source models. Grip coordinates use Blender's
imported mesh-local axes. Bone parenting compensates the default tail offset.
"""
from pathlib import Path
import math
import bpy
from mathutils import Matrix,Vector,Euler


def attach_equipment(rig,settings):
    attached=[]
    scene=bpy.context.scene;previous_frame=scene.frame_current;scene.frame_set(round(rig.animation_data.action.frame_range[0]));bpy.context.view_layer.update()
    for item in settings:
        path=Path(item['path']);bone=item['bone'];assert path.is_file() and bone in rig.pose.bones
        before=set(bpy.data.objects);bpy.ops.import_scene.gltf(filepath=str(path.resolve()))
        imported=list(set(bpy.data.objects)-before);meshes=[o for o in imported if o.type=='MESH'];assert meshes and not any(o.type=='ARMATURE' for o in imported)
        for obj in meshes:
            local=obj.matrix_world.copy()
            if item.get('axis_rotation_x'):local=Matrix.Rotation(math.radians(item['axis_rotation_x']),4,'X')@local
            if item.get('axis_rotation_z'):local=Matrix.Rotation(math.radians(item['axis_rotation_z']),4,'Z')@local
            if item.get('scale'):local=local@Matrix.Scale(float(item['scale']),4)
            if item.get('orientation_socket'):
                orientation=rig.pose.bones[item['orientation_socket']].matrix
                if item.get('pose_rotation'):orientation=Euler(tuple(math.radians(v) for v in item['pose_rotation']),'XYZ').to_matrix().to_4x4()@orientation
                local=rig.pose.bones[bone].matrix.inverted()@orientation@local
            if item.get('grip'):
                local.translation+=Vector(item.get('hand_point',[0,.05,0]))-local@Vector(item['grip'])
            obj.parent=rig;obj.parent_type='BONE';obj.parent_bone=bone;obj.matrix_parent_inverse=Matrix.Identity(4)
            obj.matrix_basis=Matrix.Translation((0,-rig.data.bones[bone].length,0))@local
            obj['d1r_equipment']=True;obj['d1r_socket']=bone;obj['d1r_asset']=path.name
            if item.get('grip'):obj['d1r_grip']=item['grip'];obj['d1r_hand_point']=item.get('hand_point',[0,.05,0])
            bpy.context.view_layer.update();expected=rig.matrix_world@rig.pose.bones[bone].matrix@local
            assert max(abs(obj.matrix_world[i][j]-expected[i][j]) for i in range(4) for j in range(4))<1e-4,('Socket parenting mismatch',bone)
            attached.append(obj)
    scene.frame_set(previous_frame);bpy.context.view_layer.update()
    return attached
