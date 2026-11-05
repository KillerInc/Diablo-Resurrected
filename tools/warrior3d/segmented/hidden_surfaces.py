"""Reconstruct concealed torso, neck and skull surfaces missing behind equipment."""
import bpy,math
from mathutils import Vector

def fill_hidden_surfaces(rig):
    objects=[]
    def material(name,color,grain=0):
        mat=bpy.data.materials.new(name);mat.use_nodes=True;nodes=mat.node_tree.nodes;links=mat.node_tree.links;shader=nodes['Principled BSDF'];shader.inputs['Base Color'].default_value=(*color,1);shader.inputs['Roughness'].default_value=.85
        if grain:
            noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=grain
            bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.12;bump.inputs['Distance'].default_value=.0015
            links.new(noise.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs['Normal'],shader.inputs['Normal'])
            broad=nodes.new('ShaderNodeTexNoise');broad.inputs['Scale'].default_value=28
            ramp=nodes.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(*(c*.65 for c in color),1);ramp.color_ramp.elements[1].color=(*(c*1.3 for c in color),1)
            links.new(broad.outputs['Fac'],ramp.inputs['Fac']);links.new(ramp.outputs['Color'],shader.inputs['Base Color'])
        return mat
    leather=material('Reconstructed back worn leather',(.035,.012,.008),100)
    skin=material('Reconstructed concealed skin',(.18,.145,.12),0)
    hair=material('Concealed dark brown hair',(.018,.009,.005),90)
    def loft(name,rings,mat,bone,back_only=False):
        vertices=[];faces=[];cols=40
        for x,y,z,rx,ry in rings:
            for col in range(cols):
                if back_only:
                    if col<=cols//2:
                        angle=math.pi*col/(cols//2);px=rx*math.cos(angle);py=ry*math.sin(angle)
                    else:px=-rx+2*rx*(col-cols//2)/(cols//2);py=0
                    vertices.append((x+px,y+py,z))
                else:
                    angle=2*math.pi*col/cols;vertices.append((x+rx*math.cos(angle),y+ry*math.sin(angle),z))
        for row in range(len(rings)-1):
            for col in range(cols):
                a=row*cols+col;b=row*cols+(col+1)%cols;faces.append((a,b,b+cols,a+cols))
        faces.extend([tuple(range(cols-1,-1,-1)),tuple((len(rings)-1)*cols+i for i in range(cols))])
        mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces);mesh.update();obj=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(obj);obj.matrix_world=rig.matrix_world.copy();mesh.materials.append(mat)
        for face in mesh.polygons:face.use_smooth=True
        group=obj.vertex_groups.new(name=bone);group.add(list(range(len(vertices))),1,'REPLACE')
        mod=obj.modifiers.new('Concealed surface deformation','ARMATURE');mod.object=rig
        obj['purpose']='Closed under-surface for missing source geometry, tucked beneath original artwork'
        objects.append(obj)
    loft('Reconstructed closed torso back',[(.014,-.025,.575,.075,.060),(.014,-.025,.62,.09,.067),(.014,-.025,.69,.103,.077),(.014,-.025,.75,.106,.076),(.014,-.025,.785,.09,.065),(.014,-.02,.81,.043,.035)],leather,'Spine02',back_only=True)
    loft('Reconstructed neck',[(.013,-.012,.785,.033,.029),(.013,-.012,.81,.035,.031),(.013,-.012,.855,.032,.029),(.013,-.012,.88,.034,.03)],skin,'Head')
    rings=[]
    for row in range(17):
        t=math.pi*row/16;radius=max(.001,math.sin(t));rings.append((.007,-.008,.891+.067*math.cos(t),.044*radius,.046*radius))
    loft('Reconstructed skull beneath hair',rings,hair,'Head')
    return objects
