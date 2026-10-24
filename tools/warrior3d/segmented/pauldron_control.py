"""Independent pauldron control and mesh-intersection clearance for test poses."""
import bpy,math
from mathutils import Vector,Matrix,Quaternion
from mathutils.bvhtree import BVHTree
NAME='Pauldron_L_Control'
def add_control(rig):
    bpy.context.view_layer.objects.active=rig;bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    b=rig.data.edit_bones.new(NAME);b.head=(.058,-.025,.845);b.tail=(.058,.035,.845);b.parent=rig.data.edit_bones['Spine02'];b.use_deform=True
    bpy.ops.object.mode_set(mode='OBJECT')
    rig.pose.bones[NAME]['purpose']='Inner-edge hinge; rotation only, no outward translation'

def set_control(rig,amount):
    bone=rig.pose.bones[NAME];rest=rig.data.bones[NAME].matrix_local.copy();pivot=rest.translation.copy()
    rotation=Quaternion((0,1,0),-math.radians(20)*amount).to_matrix().to_4x4()
    bone.matrix=Matrix.Translation(pivot)@rotation@Matrix.Translation(-pivot)@rest
    bone['test_hinge_angle_degrees']=20*amount
    bpy.context.view_layer.update()

def mesh_tree(obj,deps):
    ev=obj.evaluated_get(deps);mesh=ev.to_mesh();mesh.calc_loop_triangles()
    vertices=[ev.matrix_world@v.co for v in mesh.vertices];faces=[tuple(t.vertices) for t in mesh.loop_triangles]
    tree=BVHTree.FromPolygons(vertices,faces,all_triangles=True);ev.to_mesh_clear();return tree

def clear_body(rig,colliders):
    plate=bpy.data.objects['tripo_part_12'];bone=rig.pose.bones[NAME]
    deps=bpy.context.evaluated_depsgraph_get();trees=[mesh_tree(o,deps) for o in colliders]
    count=0;start=bone.matrix.copy();pivot=start.translation.copy()
    for step in range(61):
        tree=mesh_tree(plate,bpy.context.evaluated_depsgraph_get());count=sum(len(tree.overlap(other)) for other in trees)
        if count==0:
            error=(bone.matrix.translation-pivot).length
            assert error<1e-6,('Hinge drift',error)
            return {'intersections':0,'clearance_steps':step,'hinge_drift':error,'additional_rotation_degrees':step}
        rotation=Quaternion((0,1,0),-math.radians(step+1)).to_matrix().to_4x4()
        bone.matrix=Matrix.Translation(pivot)@rotation@Matrix.Translation(-pivot)@start
        bpy.context.view_layer.update()
    return {'intersections':count,'clearance_steps':61}
