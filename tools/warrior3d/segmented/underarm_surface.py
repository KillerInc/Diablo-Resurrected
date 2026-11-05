"""Rounded shoulder sockets; hidden endpoint rings follow torso/upper arm exactly."""
import bpy,math
from mathutils import Vector

def connect_underarms(rig):
    objects=[];report=[]
    for side,sign in [('R',-1),('L',1)]:
        shoulder=rig.data.bones[side+'_Upperarm'].head_local.copy()
        elbow=rig.data.bones[side+'_Forearm'].head_local.copy()
        start=shoulder+Vector((-sign*.035,0,-.012))
        end=shoulder+(elbow-shoulder).normalized()*.052
        control=shoulder+Vector((0,0,-.006))
        vertices=[];faces=[];weights=[];rows=9;cols=24
        for row in range(rows):
            t=row/(rows-1)
            center=(1-t)**2*start+2*(1-t)*t*control+t*t*end
            center.y-=.018
            tangent=(2*(1-t)*(control-start)+2*t*(end-control)).normalized()
            axis_y=Vector((0,1,0));axis_v=tangent.cross(axis_y).normalized()
            # Concealed ends and broad rounded deltoid preserve a real volume.
            radius=(.019+.003*math.sin(math.pi*t)) if side=='R' else (.017+.002*math.sin(math.pi*t))
            for col in range(cols):
                angle=2*math.pi*col/cols
                point=center+axis_y*(radius*1.45*math.cos(angle))+axis_v*(radius*math.sin(angle))
                vertices.append(tuple(point));u=t*t*(3-2*t);weights.append(u)
        for row in range(rows-1):
            for col in range(cols):
                a=row*cols+col;b=row*cols+(col+1)%cols
                faces.append((a,b,b+cols,a+cols))
        faces.extend([tuple(range(cols-1,-1,-1)),tuple((rows-1)*cols+i for i in range(cols))])
        mesh=bpy.data.meshes.new(f'{side} rounded underarm');mesh.from_pydata(vertices,[],faces);mesh.update()
        obj=bpy.data.objects.new(mesh.name,mesh);bpy.context.scene.collection.objects.link(obj);obj.matrix_world=rig.matrix_world.copy()
        mat=bpy.data.materials.new(f'{side} subdued underarm');mat.use_nodes=True
        shader=mat.node_tree.nodes['Principled BSDF'];shader.inputs['Base Color'].default_value=(.18,.145,.12,1) if side=='R' else (.055,.047,.04,1);shader.inputs['Roughness'].default_value=.85
        mesh.materials.append(mat)
        for face in mesh.polygons:face.use_smooth=True
        torso=obj.vertex_groups.new(name='Spine02');arm=obj.vertex_groups.new(name=side+'_Upperarm')
        for i,t in enumerate(weights):
            if t<1:torso.add([i],1-t,'REPLACE')
            if t>0:arm.add([i],t,'REPLACE')
        mod=obj.modifiers.new('Volume-preserving shoulder skin','ARMATURE');mod.object=rig;mod.use_deform_preserve_volume=True
        obj['endpoint_ring_size']=cols;obj['endpoint_arm_bone']=side+'_Upperarm'
        obj['join_method']='Rounded closed socket; endpoint rings concealed inside torso and upper arm'
        objects.append(obj);report.append({'side':side,'surface':'rounded closed socket','vertices':len(vertices),'volume_preserving_skinning':True})
    return objects,report

def endpoint_error(rig,bridges):
    deps=bpy.context.evaluated_depsgraph_get();maximum=0
    for obj in bridges:
        ev=obj.evaluated_get(deps);mesh=ev.to_mesh();count=int(obj['endpoint_ring_size'])
        for i in list(range(count))+list(range(len(mesh.vertices)-count,len(mesh.vertices))):
            name='Spine02' if i<count else obj['endpoint_arm_bone']
            transform=rig.pose.bones[name].matrix@rig.data.bones[name].matrix_local.inverted()
            expected=rig.matrix_world@transform@obj.data.vertices[i].co
            maximum=max(maximum,(ev.matrix_world@mesh.vertices[i].co-expected).length)
        ev.to_mesh_clear()
    return maximum
