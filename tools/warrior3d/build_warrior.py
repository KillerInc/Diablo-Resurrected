"""Run inside Blender: construct an editable Warrior rig and render sprite frames.

No original image is embedded or used as a texture. All mesh/material assets
are created here. References are optional local numeric measurements.
"""
import argparse
import json
import math
from pathlib import Path
import sys

import bpy
import bmesh
import numpy as np
from mathutils import Vector, Matrix


def arguments():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--reference',type=Path)
    parser.add_argument('--calibration',type=Path,help='Reuse numeric camera/root fit without any original artwork')
    parser.add_argument('--render',choices=['none','preview','all'],default='preview')
    parser.add_argument('--resolution',type=int,default=768)
    return parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])


args=arguments()
args.out=args.out.resolve()
if args.reference: args.reference=args.reference.resolve()
if args.calibration: args.calibration=args.calibration.resolve()
if args.reference and args.calibration: raise ValueError('Use either --reference or --calibration')
args.out.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
scene.unit_settings.system='METRIC'
scene.render.engine='BLENDER_EEVEE'
scene.render.resolution_x=args.resolution
scene.render.resolution_y=args.resolution
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.render.image_settings.color_mode='RGBA'
scene.render.image_settings.color_depth='8'
scene.render.film_transparent=True
scene.render.fps=20
scene.render.image_settings.compression=50
scene.view_settings.view_transform='AgX'
scene.view_settings.look='AgX - Medium High Contrast'
scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(0.15,0.17,0.21,1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=0.38


def material(name,color,roughness=0.5,metallic=0,texture=0,variation_strength=.22):
    mat=bpy.data.materials.new(name)
    mat.diffuse_color=(*color,1)
    mat.use_nodes=True
    nodes=mat.node_tree.nodes
    shader=nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value=(*color,1)
    shader.inputs['Roughness'].default_value=roughness
    shader.inputs['Metallic'].default_value=metallic
    if texture:
        noise=nodes.new('ShaderNodeTexNoise')
        noise.inputs['Scale'].default_value=texture
        noise.inputs['Detail'].default_value=3
        bump=nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value=0.12
        bump.inputs['Distance'].default_value=0.008
        mat.node_tree.links.new(noise.outputs['Fac'],bump.inputs['Height'])
        mat.node_tree.links.new(bump.outputs['Normal'],shader.inputs['Normal'])
        variation=nodes.new('ShaderNodeValToRGB')
        variation.color_ramp.elements[0].position=.15
        variation.color_ramp.elements[0].color=(*(channel*(1-variation_strength) for channel in color),1)
        variation.color_ramp.elements[1].position=.85
        variation.color_ramp.elements[1].color=(*(min(1,channel*(1+variation_strength*.5)) for channel in color),1)
        mat.node_tree.links.new(noise.outputs['Fac'],variation.inputs['Fac'])
        mat.node_tree.links.new(variation.outputs['Color'],shader.inputs['Base Color'])
    return mat


skin=material('Warm weathered skin',(0.265,0.15,0.09),0.64,texture=95,variation_strength=.05)
skin_dark=material('Skin recess',(0.15,0.062,0.034),0.65)
leather=material('Reddish brown worn leather',(0.16,0.043,0.017),0.63,texture=85)
leather_edge=material('Leather seam and edging',(0.28,0.095,0.029),0.67,texture=100)
belt_mat=material('Belt dark leather',(0.045,0.016,0.008),0.72,texture=60)
navy=material('Dark navy woven trousers',(0.018,0.030,0.075),0.85,texture=125)
steel=material('Worn forged steel',(0.24,0.27,0.29),0.57,0.72,90)
steel_edge=material('Polished steel edges',(0.38,0.40,0.41),0.43,0.76)
brass=material('Dull brass rivets',(0.27,0.17,0.065),0.44,0.72)
hair=material('Short dark brown hair',(0.025,0.014,0.008),0.82,texture=110)
eye_white=material('Muted eye white',(0.34,0.30,0.23),0.50)
eye_dark=material('Dark eyes',(0.012,0.009,0.006),0.35)
parts=[]
skin_parts=[]


def finish(obj,name,mat,bone=None,body=False):
    obj.name=name
    obj.data.materials.append(mat)
    for face in obj.data.polygons: face.use_smooth=True
    if bone: obj['deform_bone']=bone
    parts.append(obj)
    if body: skin_parts.append(obj)
    return obj


def ellipsoid(name,center,size,mat,bone=None,body=False,segments=24,rings=16):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments,ring_count=rings,location=center)
    obj=bpy.context.object
    obj.scale=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    return finish(obj,name,mat,bone,body)


def loft(name,rings,mat,bone=None,body=False,sides=32):
    # Each ring: center XYZ and radii X/Y; body axis is Z.
    vertices=[]
    for x,y,z,rx,ry in rings:
        for i in range(sides):
            angle=2*math.pi*i/sides
            vertices.append((x+rx*math.cos(angle),y+ry*math.sin(angle),z))
    faces=[]
    for row in range(len(rings)-1):
        for i in range(sides):
            a=row*sides+i; b=row*sides+(i+1)%sides
            faces.append((a,b,b+sides,a+sides))
    faces.extend([tuple(range(sides-1,-1,-1)),tuple((len(rings)-1)*sides+i for i in range(sides))])
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata(vertices,[],faces); mesh.update()
    obj=bpy.data.objects.new(name,mesh); scene.collection.objects.link(obj)
    return finish(obj,name,mat,bone,body)


def segment(name,start,end,radii,mat,bone=None,body=False,sides=20):
    start,end=Vector(start),Vector(end)
    axis=end-start; orientation=Vector((0,1,0)).rotation_difference(axis)
    vertices=[]
    for t,rx,rz in radii:
        for i in range(sides):
            a=2*math.pi*i/sides
            local=Vector((math.cos(a)*rx,t*axis.length,math.sin(a)*rz))
            vertices.append(start+orientation@local)
    faces=[]
    for r in range(len(radii)-1):
        for i in range(sides):
            a=r*sides+i; b=r*sides+(i+1)%sides
            faces.append((a,b,b+sides,a+sides))
    faces.extend([tuple(range(sides-1,-1,-1)),tuple((len(radii)-1)*sides+i for i in range(sides))])
    mesh=bpy.data.meshes.new(name); mesh.from_pydata(vertices,[],faces); mesh.update()
    obj=bpy.data.objects.new(name,mesh); scene.collection.objects.link(obj)
    return finish(obj,name,mat,bone,body)


def strap(name,points,radius,mat,bone):
    curve=bpy.data.curves.new(name,'CURVE'); curve.dimensions='3D'
    curve.bevel_depth=radius; curve.bevel_resolution=3
    spline=curve.splines.new('POLY'); spline.points.add(len(points)-1)
    for point,coordinate in zip(spline.points,points): point.co=(*coordinate,1)
    obj=bpy.data.objects.new(name,curve); scene.collection.objects.link(obj)
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active=obj; obj.select_set(True)
    bpy.ops.object.convert(target='MESH'); obj.select_set(False)
    return finish(obj,name,mat,bone)


# Anatomy proportions in metres, front toward world -Y.
torso_rings=[(0,0,.94,.14,.11),(0,0,1.01,.17,.12),(0,0,1.10,.16,.115),
             (0,0,1.20,.18,.125),(0,0,1.32,.235,.145),(0,.005,1.43,.265,.15),
             (0,.008,1.50,.25,.12),(0,.008,1.55,.12,.09)]
loft('Anatomy torso',torso_rings,skin,body=True)
ellipsoid('Pelvis',(0,.005,.96),(.18,.125,.17),skin,body=True)
segment('Neck',(0,.015,1.48),(0,.015,1.69),[(0,.085,.075),(.5,.075,.07),(1,.07,.065)],skin,body=True)
ellipsoid('Skull',(0,.008,1.765),(.097,.095,.132),skin,body=True)
ellipsoid('Jaw',(0,-.025,1.71),(.078,.073,.064),skin,body=True)
ellipsoid('Trouser pelvis',(0,.005,.975),(.185,.136,.15),navy,'hips')

rest={
    'root':((0,0,0),(0,0,.25),None),
    'hips':((0,0,.90),(0,0,1.05),'root'),
    'spine':((0,0,1.05),(0,0,1.28),'hips'),
    'chest':((0,0,1.28),(0,0,1.54),'spine'),
    'neck':((0,0,1.54),(0,0,1.67),'chest'),
    'head':((0,0,1.67),(0,0,1.91),'neck'),
}
for side,sign in [('L',1),('R',-1)]:
    shoulder=(sign*.265,.006,1.47); elbow=(sign*.43,-.015,1.18)
    wrist=(sign*.40,-.16,.965); hand=(sign*.385,-.20,.87)
    hip=(sign*.105,0,.97); knee=(sign*.14,-.025,.55)
    ankle=(sign*.15,.01,.13); toe=(sign*.15,-.19,.075)
    rest[f'upper_arm.{side}']=(shoulder,elbow,'chest')
    rest[f'forearm.{side}']=(elbow,wrist,f'upper_arm.{side}')
    rest[f'hand.{side}']=(wrist,hand,f'forearm.{side}')
    rest[f'thigh.{side}']=(hip,knee,'hips')
    rest[f'shin.{side}']=(knee,ankle,f'thigh.{side}')
    rest[f'foot.{side}']=(ankle,toe,f'shin.{side}')
    ellipsoid(f'Deltoid {side}',shoulder,(.115,.105,.12),skin,body=True)
    segment(f'Upper arm {side}',shoulder,elbow,[(0,.08,.08),(.3,.094,.087),(.7,.077,.068),(1,.055,.055)],skin,body=True)
    ellipsoid(f'Elbow {side}',elbow,(.058,.058,.058),skin,body=True)
    segment(f'Forearm {side}',elbow,wrist,[(0,.065,.062),(.25,.078,.066),(.7,.055,.046),(1,.036,.032)],skin,body=True)
    # Palms and articulated-looking curled fingers remain rigid to the hand bone.
    palm=(Vector(wrist)+Vector(hand))*.5
    obj=ellipsoid(f'Palm {side}',palm,(.043,.031,.067),skin,f'hand.{side}')
    obj.rotation_mode='QUATERNION'; obj.rotation_quaternion=Vector((0,0,1)).rotation_difference(Vector(hand)-Vector(wrist))
    for digit in range(4):
        x=palm.x+sign*(digit-1.5)*.018
        base=(x,palm.y-.006,palm.z-.035)
        joint=(x,palm.y-.025,palm.z-.069+(abs(digit-1.5)*.006))
        tip=(x,palm.y-.042,palm.z-.056+(abs(digit-1.5)*.006))
        segment(f'Finger {side} {digit} A',base,joint,[(0,.010,.010),(1,.009,.009)],skin,f'hand.{side}',sides=10)
        segment(f'Finger {side} {digit} B',joint,tip,[(0,.009,.009),(1,.007,.007)],skin,f'hand.{side}',sides=10)
    segment(f'Thumb {side}',(palm.x-sign*.032,palm.y-.01,palm.z+.015),
            (palm.x-sign*.047,palm.y-.044,palm.z-.025),[(0,.016,.013),(1,.012,.010)],skin,f'hand.{side}',sides=12)
    segment(f'Thigh anatomy {side}',hip,knee,[(0,.105,.105),(.3,.11,.11),(.8,.077,.075),(1,.065,.06)],skin,body=True)
    segment(f'Shin anatomy {side}',knee,ankle,[(0,.06,.06),(.3,.074,.078),(.8,.043,.045),(1,.037,.04)],skin,body=True)
    # Navy trousers and tall worn boots.
    segment(f'Trouser leg {side}',hip,knee,[(0,.115,.12),(.2,.12,.123),(.6,.102,.10),(1,.075,.075)],navy,f'thigh.{side}')
    segment(f'Boot shaft {side}',ankle,(sign*.14,-.02,.575),[(0,.055,.061),(.16,.064,.07),(.6,.083,.09),(.93,.078,.078),(1,.084,.084)],leather,f'shin.{side}')
    segment(f'Boot cuff {side}',(sign*.14,-.02,.54),(sign*.14,-.02,.58),[(0,.086,.086),(1,.087,.087)],leather_edge,f'shin.{side}')
    segment(f'Boot foot {side}',(sign*.15,.035,.075),(sign*.15,-.205,.055),
            [(0,.047,.05),(.18,.061,.061),(.55,.066,.049),(.90,.054,.03),(1,.025,.018)],leather,f'foot.{side}')
    segment(f'Boot sole {side}',(sign*.15,.04,.025),(sign*.15,-.21,.023),
            [(0,.05,.012),(.2,.065,.014),(.75,.067,.014),(1,.03,.01)],belt_mat,f'foot.{side}')
    strap(f'Boot seam {side}',[(sign*.15,-.10,.16),(sign*.145,-.103,.32),(sign*.14,-.10,.53)],.005,leather_edge,f'shin.{side}')

# Merge only skin anatomy, preserving editable garments and metal pieces.
parts=[obj for obj in parts if obj not in skin_parts]
bpy.ops.object.select_all(action='DESELECT')
for obj in skin_parts: obj.select_set(True)
bpy.context.view_layer.objects.active=skin_parts[0]
bpy.ops.object.join()
body=bpy.context.object; body.name='Warrior unified body'
parts.append(body)
remesh=body.modifiers.new('Unified anatomical surface','REMESH'); remesh.mode='VOXEL'; remesh.voxel_size=.018
bpy.ops.object.modifier_apply(modifier=remesh.name)
smooth=body.modifiers.new('Anatomical smoothing','SMOOTH'); smooth.factor=.65; smooth.iterations=4
bpy.ops.object.modifier_apply(modifier=smooth.name)
# Remove concealed skin surfaces rather than allowing independently skinned
# clothing layers to reveal skin through the trouser/cuirass joins.
bm=bmesh.new(); bm.from_mesh(body.data)
hidden=[]
for face in bm.faces:
    center=body.matrix_world@face.calc_center_median()
    if center.z<1.10 or (center.z<1.49 and abs(center.x)<.215):
        hidden.append(face)
bmesh.ops.delete(bm,geom=hidden,context='FACES')
bm.to_mesh(body.data); bm.free(); body.data.update()
sub=body.modifiers.new('Skin subdivision','SUBSURF'); sub.levels=1; sub.render_levels=1
for face in body.data.polygons: face.use_smooth=True

# Leather cuirass follows the torso, with metal shoulder armor and bracers.
vest=loft('Light leather cuirass',[(x,y-.003,z,rx*1.035,ry*1.055) for x,y,z,rx,ry in torso_rings[1:-1]],leather)
vest['soft_torso']=True


def cloth_front(x,z):
    for low,high in zip(torso_rings,torso_rings[1:]):
        if low[2]<=z<=high[2]:
            t=(z-low[2])/(high[2]-low[2])
            cy=low[1]*(1-t)+high[1]*t
            rx=(low[3]*(1-t)+high[3]*t)*1.035
            ry=(low[4]*(1-t)+high[4]*t)*1.055
            return (x,cy-.003-ry*math.sqrt(max(.01,1-(x/rx)**2))-.002,z)
    raise ValueError('Cuirass decoration outside torso')


loft('Waist belt',[(0,-.003,1.02,.182,.137),(0,-.003,1.09,.176,.134)],belt_mat,'hips')
ellipsoid('Belt buckle',(0,-.14,1.055),(.035,.012,.027),brass,'hips',segments=16,rings=8)
strap('Chest central seam',[cloth_front(0,z) for z in (1.13,1.32,1.44)],.003,leather_edge,'chest')
for sign in (-1,1):
    strap('Leather chest seam',[cloth_front(sign*x,z) for x,z in ((.04,1.12),(.14,1.30),(.21,1.44))],.004,leather_edge,'chest')
    for z in (1.15,1.23,1.31,1.39):
        ellipsoid('Cuirass rivet',cloth_front(sign*.105,z),(.005,.003,.005),brass,'chest',segments=10,rings=8)
for side,sign in [('L',1),('R',-1)]:
    shoulder,elbow,_=rest[f'upper_arm.{side}']; wrist=rest[f'forearm.{side}'][1]
    # Light Warrior wears one pauldron, on his left shoulder.
    if side=='L':
        pauldron=ellipsoid(f'Steel shoulder {side}',(sign*.278,.005,1.53),(.125,.117,.102),steel,f'upper_arm.{side}')
        ellipsoid(f'Pauldron lower plate {side}',(sign*.302,.005,1.455),(.113,.111,.036),steel,f'upper_arm.{side}')
        for y in (-.078,.078):
            ellipsoid(f'Shoulder rivet {side}',(sign*.325,y,1.49),(.009,.007,.009),brass,f'upper_arm.{side}',segments=10,rings=8)
    start=Vector(elbow).lerp(Vector(wrist),.36)
    end=Vector(elbow).lerp(Vector(wrist),.94)
    segment(f'Forged bracer {side}',start,end,[(0,.073,.066),(.12,.075,.068),(.85,.047,.041),(1,.047,.041)],steel,f'forearm.{side}')
    segment(f'Bracer rim {side}',start,start.lerp(end,.10),[(0,.077,.071),(1,.078,.072)],steel_edge,f'forearm.{side}')

# Facial structure and short hair: no image textures or packed reference art.
ellipsoid('Nose bridge',(0,-.096,1.762),(.012,.017,.030),skin,'head')
ellipsoid('Nose tip',(0,-.110,1.746),(.017,.017,.013),skin,'head')
for sign in (-1,1):
    ellipsoid('Cheek',(sign*.05,-.07,1.75),(.034,.022,.029),skin,'head')
    ellipsoid('Eye socket',(sign*.033,-.084,1.785),(.018,.008,.010),skin_dark,'head')
    ellipsoid('Eye',(sign*.033,-.091,1.785),(.010,.004,.0045),eye_white,'head')
    ellipsoid('Iris',(sign*.033,-.095,1.785),(.0035,.002,.0035),eye_dark,'head',segments=12,rings=8)
    segment('Brow',(sign*.014,-.09,1.800),(sign*.052,-.079,1.802),[(0,.007,.005),(1,.006,.004)],hair,'head',sides=12)
    ellipsoid('Ear',(sign*.095,.005,1.764),(.018,.014,.029),skin,'head')
strap('Mouth',[(-.026,-.09,1.705),(0,-.101,1.708),(.026,-.09,1.705)],.0022,skin_dark,'head')
loft('Short hair cap',[(0,.018,1.803,.095,.085),(0,.019,1.85,.095,.081),
                       (0,.019,1.88,.075,.066),(0,.019,1.9,.025,.025)],hair,'head')
for sign in (-1,1):
    ellipsoid('Sideburn',(sign*.088,-.007,1.793),(.011,.025,.035),hair,'head')

# Build the shared skeleton and deterministic skinning.
armature=bpy.data.armatures.new('Warrior skeleton')
rig=bpy.data.objects.new('Warrior_Rig',armature); scene.collection.objects.link(rig)
bpy.context.view_layer.objects.active=rig
bpy.ops.object.select_all(action='DESELECT'); rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
for name,(head,tail,parent) in rest.items():
    bone=armature.edit_bones.new(name); bone.head=head; bone.tail=tail
    if parent: bone.parent=armature.edit_bones[parent]
bpy.ops.object.mode_set(mode='OBJECT'); rig.show_in_front=True


def distance_to_segment(point,a,b):
    a,b=Vector(a),Vector(b); axis=b-a
    t=max(0,min(1,(point-a).dot(axis)/axis.length_squared))
    return (point-a-axis*t).length


for obj in parts:
    if obj.type!='MESH': continue
    if obj==body:
        candidates=[name for name in rest if name!='root']
    elif obj.get('soft_torso'):
        candidates=['hips','spine','chest']
    else:
        candidates=[obj.get('deform_bone','hips')]
    groups={name:obj.vertex_groups.new(name=name) for name in candidates}
    for vertex in obj.data.vertices:
        point=obj.matrix_world@vertex.co
        distances=sorted((distance_to_segment(point,*rest[name][:2]),name) for name in candidates)[:3]
        weights=[(1/max(.015,distance)**5,name) for distance,name in distances]
        total=sum(value for value,name in weights)
        for value,name in weights:
            if value/total>.001: groups[name].add([vertex.index],value/total,'REPLACE')
    modifier=obj.modifiers.new('Warrior skeletal deformation','ARMATURE'); modifier.object=rig
    # Apply deformation before the final subdivision modifier.
    if obj==body:
        bpy.context.view_layer.objects.active=obj
        bpy.ops.object.modifier_move_up(modifier=modifier.name)
    obj.parent=rig


def solve_joint(start,end,length1,length2,pole):
    start,end=Vector(start),Vector(end)
    axis=end-start; distance=min(axis.length,length1+length2-.001); direction=axis.normalized()
    a=(length1*length1-length2*length2+distance*distance)/(2*distance)
    height=math.sqrt(max(0,length1*length1-a*a))
    bend=Vector(pole)-direction*Vector(pole).dot(direction)
    return start+direction*a+bend.normalized()*height


model_offset=Vector((0,0,0))


def pose(action,phase):
    walk=action=='walk'; bob=.015*math.cos(2*phase) if walk else .004*math.sin(phase)
    targets={name:(Vector(head),Vector(tail)) for name,(head,tail,parent) in rest.items()}
    for name in ['hips','spine','chest','neck','head']:
        head,tail=targets[name]; head.z+=bob; tail.z+=bob
    for side,sign in [('L',1),('R',-1)]:
        p=phase+(math.pi if sign<0 else 0)
        hip=Vector((sign*.105,0,.955+bob))
        foot=Vector((sign*(.15 if walk else .17),(-.19*math.sin(p) if walk else (-.045 if sign>0 else .035)),
                     .13+(.105*max(0,math.cos(p)) if walk else 0)))
        l1=(Vector(rest[f'thigh.{side}'][1])-Vector(rest[f'thigh.{side}'][0])).length
        l2=(Vector(rest[f'shin.{side}'][1])-Vector(rest[f'shin.{side}'][0])).length
        knee=solve_joint(hip,foot,l1,l2,(0,-1,0))
        targets[f'thigh.{side}']=(hip,knee); targets[f'shin.{side}']=(knee,foot)
        targets[f'foot.{side}']=(foot,foot+Vector((0,-.20,-.055)))
        shoulder=Vector((sign*.265,.006,1.47+bob))
        upper=(Vector(rest[f'upper_arm.{side}'][1])-Vector(rest[f'upper_arm.{side}'][0])).length
        lower=(Vector(rest[f'forearm.{side}'][1])-Vector(rest[f'forearm.{side}'][0])).length
        # Shoulder pendulum in the sagittal plane, opposite the same-side leg.
        # Fixed segment lengths prevent the previous wrist-target pumping motion.
        swing=.38*math.sin(p) if walk else .015*math.sin(phase)
        flex=.19+.06*max(0,-math.sin(p)) if walk else .12
        upper_axis=Vector((sign*.085,math.sin(swing),-math.cos(swing))).normalized()
        lower_axis=Vector((sign*.065,math.sin(swing-flex),-math.cos(swing-flex))).normalized()
        elbow=shoulder+upper*upper_axis
        wrist=elbow+lower*lower_axis
        targets[f'upper_arm.{side}']=(shoulder,elbow); targets[f'forearm.{side}']=(elbow,wrist)
        targets[f'hand.{side}']=(wrist,wrist+lower_axis*.09)
    for name,(head,tail) in targets.items():
        head=head+model_offset; tail=tail+model_offset
        bone=rig.pose.bones[name]
        rest_matrix=armature.bones[name].matrix_local
        old_axis=Vector(rest[name][1])-Vector(rest[name][0]); new_axis=tail-head
        rotation=old_axis.rotation_difference(new_axis)@rest_matrix.to_quaternion()
        bone.rotation_mode='QUATERNION'
        bone.matrix=Matrix.LocRotScale(head,rotation,Vector((1,new_axis.length/old_axis.length,1)))
        bpy.context.view_layer.update()


rig.animation_data_create()
actions={}


def bake_actions():
    for name,count in [('idle',10),('walk',8)]:
        if name not in actions:
            actions[name]=bpy.data.actions.new('Warrior_'+name)
            actions[name].use_fake_user=True
        action=actions[name]
        rig.animation_data.action=action
        for frame in range(1,count+2):
            scene.frame_set(frame); pose(name,2*math.pi*(frame-1)/count)
            for bone in rig.pose.bones:
                bone.keyframe_insert(data_path='location',frame=frame,group=bone.name)
                bone.keyframe_insert(data_path='rotation_quaternion',frame=frame,group=bone.name)
                bone.keyframe_insert(data_path='scale',frame=frame,group=bone.name)
        action['sprite_frame_count']=count
        action['loop_endpoint_frame']=count+1
        action['source_sheet']='wlnas.png' if name=='idle' else 'wlnaw.png'


bake_actions()
rig.animation_data.action=actions['idle']; scene.frame_set(1)
scene.frame_start=1; scene.frame_end=10

# The orthographic camera, lighting and ground contact remain fixed for all frames.
bpy.ops.object.camera_add(location=(0,-7,5.1))
camera=bpy.context.object; camera.name='Sprite_Orthographic_Camera'
camera.rotation_euler=(Vector((0,0,1.0))-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.type='ORTHO'; camera.data.ortho_scale=2.75
scene.camera=camera


def light(name,location,power,size,color):
    data=bpy.data.lights.new(name,'AREA'); data.energy=power; data.shape='DISK'; data.size=size; data.color=color
    obj=bpy.data.objects.new(name,data); scene.collection.objects.link(obj); obj.location=location
    obj.rotation_euler=(Vector((0,0,1))-obj.location).to_track_quat('-Z','Y').to_euler()
light('Key soft overhead',(-3,-4,6),600,4.0,(1.0,.88,.74))
light('Cool fill',(3,-1,3),200,3.0,(.70,.80,1.0))
light('Restrained rim',(1,4,4),450,3.0,(1.0,.79,.55))

reference=json.loads(args.reference.read_text()) if args.reference else None
calibration=json.loads(args.calibration.read_text()) if args.calibration else None
yaw_offset=0.0


def projected_bounds():
    bpy.context.view_layer.update()
    deps=bpy.context.evaluated_depsgraph_get()
    inverse=camera.matrix_world.inverted()
    minimum=np.array([np.inf,np.inf]); maximum=-minimum
    for obj in parts:
        evaluated=obj.evaluated_get(deps)
        vertices=evaluated.data.vertices
        points=np.empty(len(vertices)*3,dtype=np.float32)
        vertices.foreach_get('co',points)
        transform=np.array(inverse@evaluated.matrix_world)
        projected=points.reshape(-1,3)@transform[:3,:3].T+transform[:3,3]
        minimum=np.minimum(minimum,projected[:,:2].min(axis=0))
        maximum=np.maximum(maximum,projected[:,:2].max(axis=0))
    # Square orthographic camera: exact projected vertex extrema.
    shift=np.array([camera.data.shift_x,camera.data.shift_y])
    return minimum/camera.data.ortho_scale+.5-shift,maximum/camera.data.ortho_scale+.5-shift


if calibration:
    camera.data.ortho_scale=calibration['camera_ortho_scale']
    camera.data.shift_x=calibration['camera_shift_x']
    camera.data.shift_y=calibration['camera_shift_y']
    yaw_offset=calibration['yaw_offset']
    model_offset=Vector(calibration['model_offset'])
    bake_actions()
    rig.animation_data.action=actions['idle']; scene.frame_set(1)
elif reference:
    boxes=reference['animations']['idle']['bounds_logical'][0]
    # Lock South to the model front (-Y), facing the camera;
    # columns rotate clockwise through S, SW, W, NW, N, NE, E, SE.
    target_ratios=np.array([(box[2]-box[0])/(box[3]-box[1]) for box in boxes])
    candidates=[]
    for candidate in (0.0,):
        ratios=[]
        for direction in range(8):
            rig.rotation_euler.z=math.radians(candidate-direction*45)
            low,high=projected_bounds()
            ratios.append((high[0]-low[0])/(high[1]-low[1]))
        candidates.append((float(np.mean((np.array(ratios)-target_ratios)**2)),candidate))
    yaw_offset=min(candidates)[1]
    target_height=sum(box[3]-box[1] for box in boxes)/len(boxes)/96
    heights=[]; bottoms=[]
    for direction in range(8):
        rig.rotation_euler.z=math.radians(yaw_offset-direction*45)
        low,high=projected_bounds()
        heights.append(high[1]-low[1])
    camera.data.ortho_scale*=sum(heights)/len(heights)/target_height
    # Match average bottom contact from the measured first idle frame; no per-frame rescaling.
    for direction in range(8):
        rig.rotation_euler.z=math.radians(yaw_offset-direction*45)
        low,high=projected_bounds()
        bottoms.append(low[1])
    target_bottom=1-sum(box[3] for box in boxes)/len(boxes)/96
    camera.data.shift_y+=sum(bottoms)/len(bottoms)-target_bottom
    centers=[]
    for direction in range(8):
        rig.rotation_euler.z=math.radians(yaw_offset-direction*45)
        low,high=projected_bounds(); centers.append((low[0]+high[0])*.5)
    target_center=sum((box[0]+box[2])*.5 for box in boxes)/len(boxes)/96
    camera.data.shift_x+=sum(centers)/len(centers)-target_center
    # Fit one constant model-space root offset across all eight views. A single
    # 3D offset reproduces the sinusoidal pivot changes without per-cell edits.
    basis=[]; residuals=[]
    for direction,box in enumerate(boxes):
        angle=math.radians(yaw_offset-direction*45)
        rig.rotation_euler.z=angle
        low,high=projected_bounds()
        basis.append([math.cos(angle),-math.sin(angle)])
        residuals.append(((box[0]+box[2])*.5/96-(low[0]+high[0])*.5)*camera.data.ortho_scale)
    fitted=np.linalg.lstsq(np.array(basis),np.array(residuals),rcond=None)[0]
    model_offset.x=float(fitted[0]); model_offset.y=float(fitted[1])
    bake_actions()
    rig.animation_data.action=actions['idle']; scene.frame_set(1)

rig.rotation_euler.z=0
scene['reference_art_embedded']=False
scene['milestone']='Editable model and export prototype; visual fidelity requires comparison/refinement'
scene['sheet_cell_pixels']=768
scene['logical_cell_pixels']=96
scene['direction_yaws_degrees']=json.dumps([yaw_offset-direction*45 for direction in range(8)])
rig['equipment']='Unarmed, light armor, no shield'
rig['actions']='idle:10 frames; walk:8 frames; loop endpoints excluded from export'
bpy.context.view_layer.objects.active=rig
bpy.ops.object.select_all(action='DESELECT'); rig.select_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(args.out/'Warrior-Light-Unarmed.blend'),compress=True)

calibration_record={'camera_ortho_scale':camera.data.ortho_scale,'camera_shift_x':camera.data.shift_x,
                    'camera_shift_y':camera.data.shift_y,'yaw_offset':yaw_offset,
                    'model_offset':list(model_offset),'reference_art_embedded':False}
(args.out/'calibration.json').write_text(json.dumps(calibration_record,indent=2))

# GLB is a portable mesh/rig copy. Procedural Blender material detail remains
# authoritative in the .blend file; no source images are baked into either.
bpy.ops.object.select_all(action='DESELECT')
for obj in parts: obj.select_set(True)
rig.select_set(True); bpy.context.view_layer.objects.active=rig
export_args={'filepath':str(args.out/'Warrior-Light-Unarmed.glb'),'export_format':'GLB',
             'use_selection':True,'export_animations':True,'export_skins':True}
properties=bpy.ops.export_scene.gltf.get_rna_type().properties
if 'export_animation_mode' in properties: export_args['export_animation_mode']='ACTIONS'
bpy.ops.export_scene.gltf(**export_args)

summary={'blender':bpy.app.version_string,'mesh_objects':len(parts),'bones':len(armature.bones),
         'actions':{name:action['sprite_frame_count'] for name,action in actions.items()},
         'external_images':sum(image.source in {'FILE','SEQUENCE','MOVIE'} and bool(image.filepath) for image in bpy.data.images),'source_art_embedded':False,
         'resolution':args.resolution,'camera_ortho_scale':camera.data.ortho_scale,
         'camera_shift_x':camera.data.shift_x,'camera_shift_y':camera.data.shift_y,
         'direction_yaws':[yaw_offset-direction*45 for direction in range(8)],
         'fitted_model_offset':list(model_offset),'status':'prototype; not installed'}
(args.out/'model-manifest.json').write_text(json.dumps(summary,indent=2))
print('WARRIOR_MODEL',json.dumps(summary),flush=True)
if args.render!='none':
    for name,action in actions.items():
        if args.render=='preview' and name!='idle': continue
        rig.animation_data.action=action
        count=action['sprite_frame_count']
        for frame in range(1,(count if args.render=='all' else 1)+1):
            scene.frame_set(frame)
            for direction in range(8):
                rig.rotation_euler.z=math.radians(yaw_offset-direction*45)
                bpy.context.view_layer.update()
                destination=args.out/'frames'/name/f'{direction}_{frame-1:02d}.png'
                destination.parent.mkdir(parents=True,exist_ok=True)
                scene.render.filepath=str(destination)
                bpy.ops.render.render(write_still=True)
                print(f'WARRIOR_FRAME {name} {direction} {frame-1}',flush=True)
