"""Procedural 3D casting fire, with a separate emission mask for atlas grading.

Blender 5.1. Geometry is deterministic and contains no extracted artwork.
Vertical flame arcs build around the caster, sweep down, and fade with a ground
ring and embers. Fire receives no projected shadow; character shadows stay SE.
"""
import math
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector,Matrix


def smooth(a,b,x):
    t=max(0,min(1,(x-a)/(b-a)))
    return t*t*(3-2*t)


class FireEffect:
    def __init__(self,scene,rig,output,settings):
        self.scene,self.rig=scene,rig
        self.output=Path(output)/'fire-masks'
        self.seeds=np.random.default_rng(settings.get('seed',2718)).random((192,4))
        material=bpy.data.materials.new('Procedural casting fire');material.use_nodes=True
        material.surface_render_method='DITHERED';material.use_backface_culling=False
        n=material.node_tree.nodes;n.clear();links=material.node_tree.links
        def node(kind):return n.new(kind)
        def op(kind,a,b=None):
            obj=node('ShaderNodeMath');obj.operation=kind
            for i,v in enumerate([a,b] if b is not None else [a]):
                if isinstance(v,(float,int)):obj.inputs[i].default_value=v
                else:links.new(v,obj.inputs[i])
            return obj.outputs[0]
        uv=node('ShaderNodeTexCoord');xy=node('ShaderNodeSeparateXYZ');links.new(uv.outputs['UV'],xy.inputs[0])
        geometry=node('ShaderNodeNewGeometry');noise=node('ShaderNodeTexNoise');noise.noise_dimensions='4D';noise.inputs['Scale'].default_value=10;noise.inputs['Detail'].default_value=3;noise.inputs['Roughness'].default_value=.7;links.new(geometry.outputs['Position'],noise.inputs['Vector']);self.noise=noise
        temp=op('ADD',op('SUBTRACT',op('SUBTRACT',.76,op('MULTIPLY',xy.outputs['Y'],.50)),op('MULTIPLY',op('ABSOLUTE',op('SUBTRACT',xy.outputs['X'],.5)),1.2)),op('MULTIPLY',op('SUBTRACT',noise.outputs['Fac'],.5),.45))
        core=op('MULTIPLY',op('POWER',op('SINE',op('MULTIPLY',xy.outputs['X'],math.pi)),8),op('POWER',op('SUBTRACT',1,xy.outputs['Y']),1.3))
        temp=op('ADD',temp,op('MULTIPLY',core,.45))
        ramp=node('ShaderNodeValToRGB');links.new(temp,ramp.inputs[0]);colors=[(0,(.16,.001,0,1)),(.25,(.8,.006,0,1)),(.48,(1,.055,0,1)),(.7,(1,.20,.001,1)),(.9,(1,.48,.003,1)),(1,(1,.82,.025,1))]
        ramp.color_ramp.elements.remove(ramp.color_ramp.elements[1])
        for i,(p,color) in enumerate(colors):
            e=ramp.color_ramp.elements[0] if i==0 else ramp.color_ramp.elements.new(p);e.position=p;e.color=color
        breakup=node('ShaderNodeValToRGB');links.new(noise.outputs['Fac'],breakup.inputs[0]);breakup.color_ramp.elements[0].position=.38;breakup.color_ramp.elements[0].color=(0,0,0,1);breakup.color_ramp.elements[1].position=.64
        strength=node('ShaderNodeAttribute');strength.attribute_name='fire_strength'
        alpha=op('MULTIPLY',op('MULTIPLY',op('POWER',op('SINE',op('MULTIPLY',xy.outputs['X'],math.pi)),.55),op('POWER',op('SUBTRACT',1,xy.outputs['Y']),.35)),op('MULTIPLY',breakup.outputs['Color'],strength.outputs['Fac']))
        alpha=op('MINIMUM',op('MAXIMUM',op('MULTIPLY',alpha,3),op('MULTIPLY',op('MULTIPLY',core,strength.outputs['Fac']),op('MULTIPLY',4,op('ADD',.3,op('MULTIPLY',breakup.outputs['Color'],.7))))),1)
        emission=node('ShaderNodeEmission');links.new(op('ADD',2,op('MULTIPLY',core,6)),emission.inputs['Strength']);links.new(ramp.outputs['Color'],emission.inputs['Color']);transparent=node('ShaderNodeBsdfTransparent');mix=node('ShaderNodeMixShader');links.new(alpha,mix.inputs[0]);links.new(transparent.outputs[0],mix.inputs[1]);links.new(emission.outputs[0],mix.inputs[2]);surface=node('ShaderNodeOutputMaterial');links.new(mix.outputs[0],surface.inputs['Surface'])
        self.mesh=bpy.data.meshes.new('Casting flame ribbons');self.obj=bpy.data.objects.new('Casting flame ribbons',self.mesh);scene.collection.objects.link(self.obj);self.mesh.materials.append(material)
        data=bpy.data.lights.new('Casting fire illumination','POINT');data.color=(1,.16,.015);data.shadow_soft_size=.65;data.use_shadow=False;self.light=bpy.data.objects.new('Casting fire illumination',data);scene.collection.objects.link(self.light)
        scene.view_layers[0].use_pass_emit=True
        tree=bpy.data.node_groups.new('Casting fire emission mask','CompositorNodeTree');scene.compositing_node_group=tree;tree.interface.new_socket(name='Image',in_out='OUTPUT',socket_type='NodeSocketColor');layer=tree.nodes.new('CompositorNodeRLayers');group=tree.nodes.new('NodeGroupOutput');tree.links.new(layer.outputs['Image'],group.inputs['Image']);gray=tree.nodes.new('CompositorNodeRGBToBW');tree.links.new(layer.outputs['Emission'],gray.inputs['Image']);clamp=tree.nodes.new('ShaderNodeMath');clamp.operation='MINIMUM';clamp.inputs[1].default_value=1;tree.links.new(gray.outputs[0],clamp.inputs[0]);file=tree.nodes.new('CompositorNodeOutputFile');file.file_output_items.new('FLOAT','Mask');file.format.media_type='IMAGE';file.format.file_format='PNG';file.format.color_mode='BW';file.format.color_depth='8';file.save_as_render=False;tree.links.new(clamp.outputs[0],file.inputs['Mask']);self.file=file;scene.render.use_compositing=True

    def update(self,direction,row,rows):
        self.matrix=Matrix.Translation(Vector((self.rig.location.x,self.rig.location.y,0)))
        phase=row/(rows-1);envelope=smooth(.025,.20,phase)*(1-smooth(.72,.99,phase));self.noise.inputs['W'].default_value=phase*9
        self.light.data.energy=30*envelope*(.9+.1*math.sin(phase*47));self.light.location=self.matrix@Vector((0,-.25,1))
        vertices=[];faces=[];uv=[];strengths=[]
        def tongue(local,width,length,alpha,seed,flow=None):
            point=self.matrix@Vector(local);start=len(vertices);flow=Vector((0,0,1)) if flow is None else (self.matrix.to_3x3()@Vector(flow)).normalized();side=flow.cross(Vector((0,-.866,.5)))
            if side.length<1e-5:side=Vector((1,0,0))
            side.normalize()
            for k in range(9):
                v=k/8;bulge=(.48+.52*math.sin(math.pi*v))*(1-v)**.4;sway=.25*length*math.sin(v*4+seed*12+phase*17)*v;lift=length*v
                for u in [0,1]:
                    position=point+flow*lift+side*(sway+(u-.5)*width*bulge);vertices.append(tuple(position));uv.append((u,v));strengths.append(alpha)
            for k in range(8):faces.append((start+2*k,start+2*k+1,start+2*k+3,start+2*k+2))
        growth=smooth(.04,.35,phase);rx=.08+.54*growth;rz=.10+.58*growth;cz=1.06-.19*growth
        for i in range(64):
            a=i*math.tau/64+phase*.8;seed=self.seeds[i];life=(phase*5+seed[0])%1;upper=max(0,math.sin(a));power=envelope*(1-smooth(.40,.68,phase)*smooth(0,.4,upper))*(.62+.38*seed[1])*(.35+.65*math.sin(math.pi*life))
            local=(rx*math.cos(a),.20*math.sin(a+phase*3),cz+rz*math.sin(a)+life*.06)
            tongue(local,.075+.10*seed[2],(.15+.20*seed[3])*(.6+.4*math.sin(math.pi*life)),power,seed[0],(-rx*math.sin(a),.20*math.cos(a+phase*3),rz*math.cos(a)+.28))
        ground=smooth(.14,.36,phase)*(1-smooth(.70,.99,phase));radius=.25+.37*smooth(.14,.45,phase)
        for j in range(48):
            seed=self.seeds[96+j];a=j*math.tau/48-phase*1.7;r=radius+.06*math.sin(phase*20+seed[0]*12)+.025*math.sin(a*5+phase*7);tongue((r*math.cos(a),r*math.sin(a),.018),.07+.07*seed[2],.09+.18*seed[3],ground*(.65+.35*seed[1]),seed[0],(-.6*math.sin(a),.6*math.cos(a),1))
        burst=smooth(.40,.58,phase)*(1-smooth(.72,.95,phase))
        for j in range(5):
            tongue((.08*math.sin(j*2),-.15+.04*math.cos(j),.02),.065,.25+.05*j,burst*.8,j*.17)
        for j in range(20):
            seed=self.seeds[160+j];life=(phase*1.8+seed[0])%1;a=seed[1]*math.tau+phase;r=.3+.37*seed[2];tongue((r*math.cos(a),r*math.sin(a),.05+1.35*life),.015+.02*seed[3],.03+.06*seed[2],envelope*(1-life)*.65,seed[0])
        self.mesh.clear_geometry();self.mesh.from_pydata(vertices,[],faces);self.mesh.update();layer=self.mesh.uv_layers.get('UVMap') or self.mesh.uv_layers.new(name='UVMap');layer.data.foreach_set('uv',np.asarray([uv[x.vertex_index] for x in self.mesh.loops],dtype=np.float32).ravel());attribute=self.mesh.attributes.get('fire_strength') or self.mesh.attributes.new('fire_strength','FLOAT','POINT');attribute.data.foreach_set('value',np.asarray(strengths,dtype=np.float32));self.obj.hide_render=envelope==0 and ground==0
        folder=self.output/f'{direction}-{row}';folder.mkdir(parents=True,exist_ok=True);self.file.directory=str(folder.resolve());self.file.file_name='mask'
