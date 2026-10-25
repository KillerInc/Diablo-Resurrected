"""Deterministic blue particle spirals for the original QM casting atlas.

Shares the casting emission-mask pipeline; contains no extracted artwork.
"""
import math
import bpy
import numpy as np
from mathutils import Vector
from paladin_fire_effect import FireEffect,smooth


class MagicEffect(FireEffect):
    def __init__(self,scene,rig,output,settings):
        super().__init__(scene,rig,output,{**settings,'style':'magic'})
        self.particles=np.random.default_rng(settings.get('seed',1447)).random((640,5))
        material=self.mesh.materials[0];material.name='Procedural blue casting motes'
        nodes=material.node_tree.nodes;nodes.clear();links=material.node_tree.links
        def op(kind,a,b=None):
            n=nodes.new('ShaderNodeMath');n.operation=kind
            for i,v in enumerate([a] if b is None else [a,b]):
                if isinstance(v,(int,float)):n.inputs[i].default_value=v
                else:links.new(v,n.inputs[i])
            return n.outputs[0]
        uv=nodes.new('ShaderNodeTexCoord');xy=nodes.new('ShaderNodeSeparateXYZ');links.new(uv.outputs['UV'],xy.inputs[0])
        center=op('MULTIPLY',op('SINE',op('MULTIPLY',xy.outputs['X'],math.pi)),op('SINE',op('MULTIPLY',xy.outputs['Y'],math.pi)))
        strength=nodes.new('ShaderNodeAttribute');strength.attribute_name='fire_strength'
        alpha=op('MULTIPLY',op('POWER',center,.65),strength.outputs['Fac'])
        ramp=nodes.new('ShaderNodeValToRGB');links.new(center,ramp.inputs[0]);ramp.color_ramp.elements[0].color=(.025,.07,.55,1);ramp.color_ramp.elements[1].color=(.30,.52,1,1)
        emission=nodes.new('ShaderNodeEmission');links.new(ramp.outputs[0],emission.inputs['Color']);emission.inputs['Strength'].default_value=2.5
        transparent=nodes.new('ShaderNodeBsdfTransparent');mix=nodes.new('ShaderNodeMixShader');links.new(alpha,mix.inputs[0]);links.new(transparent.outputs[0],mix.inputs[1]);links.new(emission.outputs[0],mix.inputs[2]);surface=nodes.new('ShaderNodeOutputMaterial');links.new(mix.outputs[0],surface.inputs['Surface'])
        self.light.data.color=(.12,.28,1)

    def update(self,direction,row,rows):
        phase=row/(rows-1);envelope=smooth(.025,.24,phase)*(1-smooth(.82,1,phase))
        self.light.data.energy=15*envelope;self.light.location=(0,-.2,.8)
        verts=[];faces=[];uv=[];strength=[]
        right=Vector((1,0,0));up=Vector((0,.5,.866))
        rise=smooth(.03,.65,phase);radius=.20+.40*smooth(.03,.5,phase)
        for i,seed in enumerate(self.particles):
            t=(seed[0]+phase*.70)%1
            # Four winding streams of separate motes, rather than an opaque shell.
            angle=(i%4)*math.pi/2+t*math.tau*1.5+phase*math.tau*1.6+(seed[1]-.5)*.23
            r=radius+.07*math.sin(t*8+phase*7)+(seed[2]-.5)*.12
            p=Vector((r*math.cos(angle),r*math.sin(angle),.035+t*(.12+1.75*rise)))
            p+=Vector((self.rig.location.x,self.rig.location.y,0))
            size=.010+.014*seed[3];power=envelope*(.40+.60*seed[4])*(.6+.4*math.sin(math.pi*t))
            start=len(verts)
            for x,y in [(0,0),(1,0),(1,1),(0,1)]:verts.append(tuple(p+right*((x-.5)*size)+up*((y-.5)*size)));uv.append((x,y));strength.append(power)
            faces.append((start,start+1,start+2,start+3))
        self.mesh.clear_geometry();self.mesh.from_pydata(verts,[],faces);self.mesh.update()
        layer=self.mesh.uv_layers.get('UVMap') or self.mesh.uv_layers.new(name='UVMap');layer.data.foreach_set('uv',np.asarray([uv[x.vertex_index] for x in self.mesh.loops],dtype=np.float32).ravel())
        attr=self.mesh.attributes.get('fire_strength') or self.mesh.attributes.new('fire_strength','FLOAT','POINT');attr.data.foreach_set('value',np.asarray(strength,dtype=np.float32));self.obj.hide_render=envelope==0
        folder=self.output/f'{direction}-{row}';folder.mkdir(parents=True,exist_ok=True);self.file.directory=str(folder.resolve());self.file.file_name='mask'
