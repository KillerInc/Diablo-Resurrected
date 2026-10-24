"""Fixed inner-edge hinge clearance for the T-pose pauldron."""
import bpy,math
from mathutils import Matrix,Quaternion
from mathutils.bvhtree import BVHTree

def tree(obj,deps):
    ev=obj.evaluated_get(deps);mesh=ev.to_mesh();mesh.calc_loop_triangles();vertices=[ev.matrix_world@v.co for v in mesh.vertices];faces=[tuple(t.vertices) for t in mesh.loop_triangles];result=BVHTree.FromPolygons(vertices,faces,all_triangles=True);ev.to_mesh_clear();return result

def clear_hinge(rig,plate,coat,amount):
    bone=rig.pose.bones['Pauldron_Hinge'];rest=rig.data.bones[bone.name].matrix_local.copy();pivot=rest.translation.copy();world_pivot=rig.matrix_world@pivot
    # Check local shoulder/neck/chest geometry rather than distant hands/boots.
    names=('tripo_part_3','tripo_part_6','tripo_part_10','tripo_part_13','tripo_part_20','tripo_part_27','tripo_part_31','tripo_part_36','tripo_part_38','tripo_part_47')
    deps=bpy.context.evaluated_depsgraph_get();trees=[tree(bpy.data.objects[n],deps) for n in names]+[tree(coat,deps)]
    # Negative Y rotation lifts the outer rim. Keep the lowered-arm pose at
    # its clearance limit, then lift progressively as the arm rises.
    base=-20-15*amount;best=None
    for step in range(71):
        angle=base-step;rotation=Quaternion((0,1,0),math.radians(angle)).to_matrix().to_4x4();bone.matrix=Matrix.Translation(pivot)@rotation@Matrix.Translation(-pivot)@rest;bpy.context.view_layer.update()
        current=tree(plate,bpy.context.evaluated_depsgraph_get());count=sum(len(current.overlap(other)) for other in trees)
        if best is None or count<best[0]:best=(count,bone.matrix.copy(),angle)
        if count==0:break
    bone.matrix=best[1];bpy.context.view_layer.update();drift=(bone.matrix.translation-pivot).length;assert drift<1e-6
    return {'intersections':best[0],'hinge_drift':drift,'angle_degrees':best[2]}
