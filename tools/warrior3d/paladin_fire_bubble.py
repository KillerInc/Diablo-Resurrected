"""A translucent three-dimensional burning bubble around the caster."""
import math
import bpy
import numpy as np
from mathutils import Vector


class FireBubble:
    def __init__(self,scene,settings=None):
        settings=settings or {}
        self.wobble=float(settings.get('bubble_wobble',.015))
        noise_scale=float(settings.get('bubble_noise_scale',3))
        noise_detail=float(settings.get('bubble_noise_detail',3))
        half_width=float(settings.get('bubble_band_half_width',.024))
        interior=float(settings.get('bubble_interior_fill',1))
        band_gain=float(settings.get('bubble_band_gain',.25))
        assert 0<=self.wobble<=.1 and 0<noise_scale<=10 and 0<half_width<.2
        material=bpy.data.materials.new('Procedural fiery bubble');material.use_nodes=True;material.surface_render_method='DITHERED';material.use_backface_culling=False
        nodes=material.node_tree.nodes;nodes.clear();links=material.node_tree.links
        def node(kind):return nodes.new(kind)
        def op(kind,a,b=None):
            n=node('ShaderNodeMath');n.operation=kind
            for i,v in enumerate([a] if b is None else [a,b]):
                if isinstance(v,(float,int)):n.inputs[i].default_value=v
                else:links.new(v,n.inputs[i])
            return n.outputs[0]
        geometry=node('ShaderNodeNewGeometry');stretch=node('ShaderNodeVectorMath');stretch.operation='MULTIPLY';stretch.inputs[1].default_value=(2.5,2.5,1.5);links.new(geometry.outputs['Position'],stretch.inputs[0]);noise=node('ShaderNodeTexNoise');noise.noise_dimensions='4D';noise.inputs['Scale'].default_value=noise_scale;noise.inputs['Detail'].default_value=noise_detail;noise.inputs['Roughness'].default_value=.7;links.new(stretch.outputs[0],noise.inputs['Vector']);self.noise=noise
        band=node('ShaderNodeValToRGB');links.new(noise.outputs['Fac'],band.inputs[0]);band.color_ramp.elements.remove(band.color_ramp.elements[1])
        for i,(p,color) in enumerate([(.30,(0,0,0,1)),(.50-half_width,(0,0,0,1)),(.50,(1,1,1,1)),(.50+half_width,(0,0,0,1)),(.75,(0,0,0,1))]):
            e=band.color_ramp.elements[0] if i==0 else band.color_ramp.elements.new(p);e.position=p;e.color=color
        fresnel=node('ShaderNodeFresnel');fresnel.inputs['IOR'].default_value=1.15;rim=op('POWER',fresnel.outputs[0],.5);value=node('ShaderNodeValue');value.outputs[0].default_value=0;self.strength=value
        alpha=op('MINIMUM',op('MULTIPLY',op('ADD',op('MULTIPLY',op('MULTIPLY',rim,op('ADD',.35,op('MULTIPLY',noise.outputs['Fac'],.65))),interior),op('MULTIPLY',band.outputs['Color'],band_gain)),value.outputs[0]),.95)
        temperature=op('ADD',op('ADD',op('MULTIPLY',band.outputs['Color'],.65),op('MULTIPLY',rim,.35)),op('MULTIPLY',noise.outputs['Fac'],.15));ramp=node('ShaderNodeValToRGB');links.new(temperature,ramp.inputs[0]);ramp.color_ramp.elements.remove(ramp.color_ramp.elements[1])
        for i,(p,color) in enumerate([(0,(.3,.002,0,1)),(.3,(.9,.01,0,1)),(.6,(1,.20,.002,1)),(.85,(1,.75,.02,1)),(1,(1,1,.1,1))]):
            e=ramp.color_ramp.elements[0] if i==0 else ramp.color_ramp.elements.new(p);e.position=p;e.color=color
        emit=node('ShaderNodeEmission');links.new(ramp.outputs['Color'],emit.inputs['Color']);links.new(op('ADD',2,op('ADD',op('MULTIPLY',band.outputs['Color'],4),op('MULTIPLY',rim,3))),emit.inputs['Strength']);transparent=node('ShaderNodeBsdfTransparent');mix=node('ShaderNodeMixShader');links.new(alpha,mix.inputs[0]);links.new(transparent.outputs[0],mix.inputs[1]);links.new(emit.outputs[0],mix.inputs[2]);output=node('ShaderNodeOutputMaterial');links.new(mix.outputs[0],output.inputs['Surface'])
        bpy.ops.mesh.primitive_uv_sphere_add(segments=64,ring_count=32,radius=1);self.obj=bpy.context.object;self.obj.name='Fiery bubble shell';self.obj.data.materials.append(material)
        if hasattr(self.obj,'visible_shadow'):self.obj.visible_shadow=False
        for face in self.obj.data.polygons:face.use_smooth=True
        self.original=np.empty(len(self.obj.data.vertices)*3,dtype=np.float32);self.obj.data.vertices.foreach_get('co',self.original);self.original=self.original.reshape(-1,3)

    def update(self,phase,envelope,matrix,tongue,seeds):
        t=max(0,min(1,(phase-.02)/.28));growth=.55+.45*t*t*(3-2*t);self.obj.location=matrix@Vector((0,0,.90));self.obj.scale=(.78*growth,.72*growth,1.08*growth);self.strength.outputs[0].default_value=envelope;self.noise.inputs['W'].default_value=phase*7;self.obj.hide_render=envelope==0
        p=self.original;wobble=1+self.wobble*np.sin(p[:,0]*6+p[:,1]*7+phase*20)*np.sin(p[:,2]*8-phase*13);self.obj.data.vertices.foreach_set('co',(p*wobble[:,None]).astype(np.float32).ravel());self.obj.data.update()
        camera=Vector((0,-.866,.5))
        for i in range(84):
            seed=seeds[i];nz=1-2*(i+.5)/84;radius=math.sqrt(max(0,1-nz*nz));a=i*math.pi*(3-math.sqrt(5))+phase*.4;nx=radius*math.cos(a);ny=radius*math.sin(a);normal=Vector((nx/.78,ny/.72,nz/1.08)).normalized();rim=1-abs(normal.dot(camera));life=(phase*4+seed[0])%1;power=envelope*(.16+.84*rim*rim)*(.45+.55*math.sin(math.pi*life));local=(.78*growth*nx,.72*growth*ny,.90+1.08*growth*nz)
            tongue(local,.055+.065*seed[1],.10+.10*seed[2],power,seed[0],(normal.x*.25,normal.y*.25,.9+normal.z*.25))
