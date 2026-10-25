"""Seeded 3D casting arcs, sharing the fire pipeline's separate emission mask.

No artwork is embedded. The body, shadow projection and gameplay spell remain
independent; this effect is baked only into the lightning casting atlas.
"""
import math
import bpy
import numpy as np
from mathutils import Vector
from paladin_fire_effect import FireEffect,smooth


class LightningEffect(FireEffect):
    def __init__(self,scene,rig,output,settings):
        super().__init__(scene,rig,output,{**settings,'style':'lightning'})
        self.seed=settings.get('seed',811)
        material=self.mesh.materials[0];material.name='Procedural casting lightning'
        nodes=material.node_tree.nodes;nodes.clear();links=material.node_tree.links
        uv=nodes.new('ShaderNodeTexCoord');xy=nodes.new('ShaderNodeSeparateXYZ');links.new(uv.outputs['UV'],xy.inputs[0])
        def op(kind,a,b=None):
            n=nodes.new('ShaderNodeMath');n.operation=kind
            for i,v in enumerate([a] if b is None else [a,b]):
                if isinstance(v,(int,float)):n.inputs[i].default_value=v
                else:links.new(v,n.inputs[i])
            return n.outputs[0]
        core=op('POWER',op('SINE',op('MULTIPLY',xy.outputs['X'],math.pi)),5)
        strength=nodes.new('ShaderNodeAttribute');strength.attribute_name='fire_strength'
        alpha=op('MULTIPLY',op('SINE',op('MULTIPLY',xy.outputs['X'],math.pi)),strength.outputs['Fac'])
        ramp=nodes.new('ShaderNodeValToRGB');links.new(core,ramp.inputs[0]);ramp.color_ramp.elements[0].color=(.075,.035,1,1);ramp.color_ramp.elements[1].color=(.8,.9,1,1)
        emission=nodes.new('ShaderNodeEmission');links.new(ramp.outputs[0],emission.inputs['Color']);links.new(op('ADD',2,op('MULTIPLY',core,5)),emission.inputs['Strength'])
        transparent=nodes.new('ShaderNodeBsdfTransparent');mix=nodes.new('ShaderNodeMixShader');links.new(alpha,mix.inputs[0]);links.new(transparent.outputs[0],mix.inputs[1]);links.new(emission.outputs[0],mix.inputs[2]);surface=nodes.new('ShaderNodeOutputMaterial');links.new(mix.outputs[0],surface.inputs['Surface'])
        self.light.data.color=(.34,.42,1)

    def update(self,direction,row,rows):
        # LM has 21 stored rows; gameplay uses 20. The spare last row stays idle.
        phase=min(row,19)/19;envelope=smooth(.04,.24,phase)*(1-smooth(.76,1,phase))
        rng=np.random.default_rng(self.seed+min(row,19)*73)
        self.light.data.energy=24*envelope;self.light.location=(0,-.2,.85)
        verts=[];faces=[];uv=[];strength=[]
        camera=Vector((0,-.866,.5))
        def bolt(points,width,power):
            start=len(verts)
            for j,p in enumerate(points):
                tangent=points[min(j+1,len(points)-1)]-points[max(0,j-1)];side=tangent.cross(camera)
                if side.length<1e-6:side=Vector((1,0,0))
                side.normalize();fade=math.sin(math.pi*j/(len(points)-1))**.3
                for u in [0,1]:verts.append(tuple(p+side*((u-.5)*width)));uv.append((u,j/(len(points)-1)));strength.append(power*fade)
            for j in range(len(points)-1):faces.append((start+2*j,start+2*j+1,start+2*j+3,start+2*j+2))
        hands=[self.rig.matrix_world@self.rig.pose.bones['hand.'+s].head for s in ['L','R']]
        # Two irregular side arcs descend from the hands and curl around the feet.
        for k in range(6):
            points=[];a=k*math.tau/6+phase*1.5
            for j in range(25):
                t=j/24;angle=a+t*2.6;r=.36+.17*math.sin(math.pi*t)
                p=Vector((r*math.cos(angle),r*math.sin(angle),1.25*(1-t)+.08))
                if t<.22:p=p.lerp(hands[k%2],(1-t/.22)*.75)
                p+=Vector((rng.uniform(-.04,.04),rng.uniform(-.04,.04),rng.uniform(-.035,.035)))*math.sin(math.pi*t)
                points.append(p)
            bolt(points,.025 if k%2 else .035,envelope*(.65+.35*rng.random()))
            # A short fork makes the electric paths read as lightning, not rings.
            pivot=points[12];end=pivot+Vector((.17*math.cos(a+1),.17*math.sin(a+1),-.2))
            branch=[pivot.lerp(end,j/7)+Vector((rng.uniform(-.025,.025),0,rng.uniform(-.02,.02))) for j in range(8)]
            bolt(branch,.018,envelope*.65)
        self.mesh.clear_geometry();self.mesh.from_pydata(verts,[],faces);self.mesh.update()
        layer=self.mesh.uv_layers.get('UVMap') or self.mesh.uv_layers.new(name='UVMap');layer.data.foreach_set('uv',np.asarray([uv[x.vertex_index] for x in self.mesh.loops],dtype=np.float32).ravel())
        attr=self.mesh.attributes.get('fire_strength') or self.mesh.attributes.new('fire_strength','FLOAT','POINT');attr.data.foreach_set('value',np.asarray(strength,dtype=np.float32));self.obj.hide_render=envelope==0
        folder=self.output/f'{direction}-{row}';folder.mkdir(parents=True,exist_ok=True);self.file.directory=str(folder.resolve());self.file.file_name='mask'
