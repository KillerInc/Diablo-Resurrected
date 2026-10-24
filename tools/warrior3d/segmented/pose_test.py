"""Repeatable joint-range exercise, not a locomotion animation."""
import bpy,math
from mathutils import Matrix,Quaternion
from pauldron_control import set_control,clear_body
from knee_control import bend

def apply_test_pose(rig,amount,repair_active=False,bridges=(),collision_results=None):
    for bone in rig.pose.bones:bone.matrix_basis.identity()
    bpy.context.view_layer.update()
    for side,sign in [('L',-1),('R',1)]:
        bone=rig.pose.bones[side+'_Upperarm'];pivot=bone.head.copy()
        rotation=Quaternion((0,1,0),sign*math.radians(65)*amount).to_matrix().to_4x4()
        bone.matrix=Matrix.Translation(pivot)@rotation@Matrix.Translation(-pivot)@bone.matrix
        bpy.context.view_layer.update()
        elbow=rig.pose.bones[side+'_Forearm'];elbow.rotation_mode='QUATERNION';elbow.rotation_quaternion=Quaternion((1,0,0),math.radians(25)*amount)
        bpy.context.view_layer.update();bend(rig,side,60*amount)
    set_control(rig,amount)
    if repair_active:
        colliders=[bpy.data.objects[f'tripo_part_{i}'] for i in (2,6,8,15,17,18,21,26,35,37,38)]+list(bridges)
        colliders += [o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith('Reconstructed ')]
        clearance=clear_body(rig,colliders)
        assert clearance['intersections']==0,('Pauldron collision',clearance)
        if collision_results is not None:collision_results.append(clearance)
