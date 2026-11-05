"""Anatomical knee hinge axis and patella follow control for the inspected rig."""
import bpy,math
from mathutils import Vector,Matrix,Quaternion

def add_knees(rig):
    bpy.context.view_layer.objects.active=rig;bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
    for side in ('L','R'):
        knee=rig.data.edit_bones[side+'_Calf'].head.copy();bone=rig.data.edit_bones.new(side+'_Patella_Control');bone.head=knee;bone.tail=knee+Vector((0,-.04,0));bone.parent=rig.data.edit_bones[side+'_Thigh']
    bpy.ops.object.mode_set(mode='OBJECT')

def bend(rig,side,degrees):
    # Armature-space mediolateral hinge, independent of imported bone roll.
    bone=rig.pose.bones[side+'_Calf'];pivot=bone.head.copy()
    rotation=Quaternion((1,0,0),math.radians(degrees)).to_matrix().to_4x4()
    bone.matrix=Matrix.Translation(pivot)@rotation@Matrix.Translation(-pivot)@bone.matrix
    bpy.context.view_layer.update()
    plate=rig.pose.bones[side+'_Patella_Control'];pivot=plate.head.copy()
    rotation=Quaternion((1,0,0),math.radians(degrees*.5)).to_matrix().to_4x4()
    plate.matrix=Matrix.Translation(pivot)@rotation@Matrix.Translation(-pivot)@plate.matrix
    bpy.context.view_layer.update()

def plate_weights(rig):
    obj=bpy.data.objects['tripo_part_10'];inv=rig.matrix_world.inverted()
    for group in list(obj.vertex_groups):obj.vertex_groups.remove(group)
    groups={n:obj.vertex_groups.new(name=n) for n in ('L_Thigh','L_Patella_Control','L_Calf')}
    knee=rig.data.bones['L_Calf'].head_local.z
    for vertex in obj.data.vertices:
        z=(inv@obj.matrix_world@vertex.co).z-knee
        if z>.035:ws={'L_Thigh':1}
        elif z<-.035:ws={'L_Calf':1}
        elif z>=0:
            t=z/.035;ws={'L_Thigh':t,'L_Patella_Control':1-t}
        else:
            t=-z/.035;ws={'L_Calf':t,'L_Patella_Control':1-t}
        for name,w in ws.items():
            if w>0:groups[name].add([vertex.index],w,'REPLACE')
    # Replace scattered imported knee weights with a monotonic bend transition.
    for index,side in ((22,'R'),(29,'L')):
        obj=bpy.data.objects[f'tripo_part_{index}'];knee=rig.data.bones[side+'_Calf'].head_local.z
        for group in list(obj.vertex_groups):obj.vertex_groups.remove(group)
        thigh=obj.vertex_groups.new(name=side+'_Thigh');calf=obj.vertex_groups.new(name=side+'_Calf')
        for vertex in obj.data.vertices:
            z=(inv@obj.matrix_world@vertex.co).z
            t=max(0,min(1,(knee+.045-z)/.09));t=t*t*(3-2*t)
            if t<1:thigh.add([vertex.index],1-t,'REPLACE')
            if t>0:calf.add([vertex.index],t,'REPLACE')
    for obj in bpy.data.objects:
        if obj.type=='MESH' and obj.name.startswith('tripo_part_'):
            for mod in obj.modifiers:
                if mod.type=='ARMATURE':mod.use_deform_preserve_volume=True
