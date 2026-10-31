"""Seeded 3D casting arcs, sharing the fire pipeline's separate emission mask.

No artwork is embedded. The body, shadow projection and gameplay spell remain
independent; this effect is baked only into the lightning casting atlas.
"""
import math
import bpy
import numpy as np
from mathutils import Vector,Matrix
from paladin_fire_effect import FireEffect,smooth


class LightningEffect(FireEffect):
    def __init__(self,scene,rig,output,settings):
        super().__init__(scene,rig,output,{**settings,'style':'lightning'})
        self.seed=settings.get('seed',811)
        self.mode=settings.get('lightning_mode','legacy')
        assert self.mode in ('legacy','grow_hold')
        self.activation_spread=float(settings.get('activation_spread',.51))
        self.bolt_travel=float(settings.get('bolt_travel',.16))
        self.spin_rate=float(settings.get('spin_rate',1.5))
        self.path_style=settings.get('path_style','hand_streams')
        self.tone=settings.get('lightning_tone','blue')
        self.halo_profile=settings.get('halo_profile','full')
        self.plasma_motion=float(settings.get('plasma_motion',1))
        self.plasma_speed=float(settings.get('plasma_speed',1))
        self.plasma_color=settings.get('plasma_color','violet')
        self.body_contacts=bool(settings.get('plasma_body_contacts',False))
        self.filament_count=int(settings.get('plasma_filaments',11))
        self.equipment_contacts=bool(settings.get('plasma_equipment_contacts',False))
        self.blade_contacts=bool(settings.get('plasma_blade_contacts',False))
        self.sword_climbers=int(settings.get('plasma_sword_climbers',0))
        self.contact_vertices=[]
        assert self.path_style in ('hand_streams','halo','plasma') and self.tone in ('blue','vanilla','plasma')
        assert 0<=self.activation_spread<.8 and 0<self.bolt_travel<.5
        self.paths={}
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
        if self.tone=='vanilla':ramp.color_ramp.elements[0].color=(.25,.001,0,1);ramp.color_ramp.elements[1].color=(1,.16,.035,1)
        emission=nodes.new('ShaderNodeEmission');links.new(ramp.outputs[0],emission.inputs['Color']);links.new(op('ADD',2,op('MULTIPLY',core,5)),emission.inputs['Strength'])
        transparent=nodes.new('ShaderNodeBsdfTransparent');mix=nodes.new('ShaderNodeMixShader');links.new(alpha,mix.inputs[0]);links.new(transparent.outputs[0],mix.inputs[1]);links.new(emission.outputs[0],mix.inputs[2]);surface=nodes.new('ShaderNodeOutputMaterial');links.new(mix.outputs[0],surface.inputs['Surface'])
        self.light.data.color=(.34,.42,1)
        if self.tone=='vanilla':self.light.data.color=(1,.08,.025)
        self.tip_mesh=None
        if self.path_style=='plasma':self.create_plasma_material(scene)

    def create_plasma_material(self,scene):
        material=self.mesh.materials[0];material.name='Violet plasma filaments';nodes=material.node_tree.nodes;nodes.clear();links=material.node_tree.links
        def op(kind,a,b=None):
            n=nodes.new('ShaderNodeMath');n.operation=kind
            for i,v in enumerate([a] if b is None else [a,b]):
                if isinstance(v,(int,float)):n.inputs[i].default_value=v
                else:links.new(v,n.inputs[i])
            return n.outputs[0]
        uv=nodes.new('ShaderNodeTexCoord');xy=nodes.new('ShaderNodeSeparateXYZ');links.new(uv.outputs['UV'],xy.inputs[0]);across=op('MAXIMUM',0,op('SINE',op('MULTIPLY',xy.outputs['X'],math.pi)));core=op('POWER',across,28);halo=op('POWER',across,1.5)
        color=nodes.new('ShaderNodeValToRGB');links.new(xy.outputs['Y'],color.inputs[0]);color.color_ramp.elements[0].color=(.85,.32,1,1);color.color_ramp.elements[1].color=(1,.035,.20,1);middle=color.color_ramp.elements.new(.75);middle.color=(.55,.12,1,1)
        if self.plasma_color=='blue':color.color_ramp.elements[0].color=(.3,.65,1,1);middle.color=(.08,.3,1,1);color.color_ramp.elements[-1].color=(.25,.8,1,1)
        mix_color=nodes.new('ShaderNodeMixRGB');mix_color.inputs[1].default_value=(.16,.002,.65,1);links.new(core,mix_color.inputs[0]);links.new(color.outputs[0],mix_color.inputs[2]);strength=nodes.new('ShaderNodeAttribute');strength.attribute_name='fire_strength';alpha=op('MINIMUM',1,op('MULTIPLY',op('ADD',op('MULTIPLY',halo,.16),op('MULTIPLY',core,.9)),strength.outputs['Fac']))
        emission=nodes.new('ShaderNodeEmission');links.new(mix_color.outputs[0],emission.inputs['Color']);links.new(op('ADD',2,op('MULTIPLY',core,5)),emission.inputs['Strength']);transparent=nodes.new('ShaderNodeBsdfTransparent');mix=nodes.new('ShaderNodeMixShader');links.new(alpha,mix.inputs[0]);links.new(transparent.outputs[0],mix.inputs[1]);links.new(emission.outputs[0],mix.inputs[2]);output=nodes.new('ShaderNodeOutputMaterial');links.new(mix.outputs[0],output.inputs['Surface']);self.light.data.color=(.45,.05,1)
        if self.plasma_color=='blue':mix_color.inputs[1].default_value=(.008,.05,.85,1);self.light.data.color=(.07,.25,1)
        tip=bpy.data.materials.new('Plasma boundary contact glow');tip.use_nodes=True;tip.surface_render_method='DITHERED';nodes=tip.node_tree.nodes;links=tip.node_tree.links;nodes.clear();uv=nodes.new('ShaderNodeTexCoord');xy=nodes.new('ShaderNodeSeparateXYZ');links.new(uv.outputs['UV'],xy.inputs[0])
        def op2(kind,a,b):
            n=nodes.new('ShaderNodeMath');n.operation=kind
            for i,v in enumerate((a,b)):
                if isinstance(v,(int,float)):n.inputs[i].default_value=v
                else:links.new(v,n.inputs[i])
            return n.outputs[0]
        x=op2('SUBTRACT',xy.outputs['X'],.5);y=op2('SUBTRACT',xy.outputs['Y'],.5);radius=op2('ADD',op2('MULTIPLY',x,x),op2('MULTIPLY',y,y));alpha=op2('POWER',op2('MAXIMUM',0,op2('SUBTRACT',1,op2('MULTIPLY',radius,4))),3)
        emission=nodes.new('ShaderNodeEmission');emission.inputs['Color'].default_value=(1,.015,.12,1);emission.inputs['Strength'].default_value=3;transparent=nodes.new('ShaderNodeBsdfTransparent');mix=nodes.new('ShaderNodeMixShader');links.new(alpha,mix.inputs[0]);links.new(transparent.outputs[0],mix.inputs[1]);links.new(emission.outputs[0],mix.inputs[2]);output=nodes.new('ShaderNodeOutputMaterial');links.new(mix.outputs[0],output.inputs['Surface'])
        if self.plasma_color=='blue':emission.inputs['Color'].default_value=(.05,.35,1,1)
        self.tip_mesh=bpy.data.meshes.new('Plasma contact points');self.tip_obj=bpy.data.objects.new('Plasma contact points',self.tip_mesh);scene.collection.objects.link(self.tip_obj);self.tip_mesh.materials.append(tip)

    def update(self,direction,row,rows):
        if self.mode=='grow_hold':return self.update_grow_hold(direction,row,rows)
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
                side.normalize();fade=max(0.,math.sin(math.pi*j/(len(points)-1)))**.3
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

    def build_paths(self,direction):
        if self.path_style=='halo':return self.build_halo_paths(direction)
        if self.path_style=='plasma':return self.build_plasma_paths(direction)
        rng=np.random.default_rng(self.seed)
        hands=[(self.rig.matrix_world@self.rig.pose.bones['hand.'+s].head).copy() for s in ('L','R')]
        result=[]
        for k in range(6):
            start=.04+self.activation_spread*float(rng.random());angle=k*math.tau/6;points=[]
            for j in range(25):
                t=j/24;a=angle+t*2.6;r=.36+.17*math.sin(math.pi*t)
                p=self.cast_start_matrix@Vector((r*math.cos(a),r*math.sin(a),1.25*(1-t)+.08))
                if t<.22:p=p.lerp(hands[k%2],1-t/.22)
                p+=Vector((rng.uniform(-.04,.04),rng.uniform(-.04,.04),rng.uniform(-.035,.035)))*math.sin(math.pi*t)
                points.append(p)
            pivot=points[12];end=pivot+Vector((.17*math.cos(angle+1),.17*math.sin(angle+1),-.2))
            branch=[pivot.lerp(end,j/7)+Vector((rng.uniform(-.025,.025),0,rng.uniform(-.02,.02)))*math.sin(math.pi*j/7) for j in range(8)]
            distances=[0.]
            for a,b in zip(points,points[1:]):distances.append(distances[-1]+(b-a).length)
            result.append({'start':start,'points':points,'branch':branch,'lengths':distances,'fork_index':12,'power':.65+.35*float(rng.random()),'width':.025 if k%2 else .035})
        self.paths[direction]=result

    def build_plasma_paths(self,direction):
        rng=np.random.default_rng(self.seed);result=[];center=self.cast_start_matrix@Vector((0,0,.95));count=self.filament_count
        if self.body_contacts:self.select_body_contacts(count,rng)
        for k in range(count):
            start=.035+self.activation_spread*float(rng.random());nz=.92-1.72*k/(count-1);a=k*math.pi*(3-math.sqrt(5));rad=math.sqrt(1-nz*nz);end=center+Vector((.86*rad*math.cos(a),.78*rad*math.sin(a),1.04*nz));origin=center+Vector((rng.uniform(-.05,.05),rng.uniform(-.05,.05),rng.uniform(-.04,.04)));bend=Vector((rng.uniform(-.18,.18),rng.uniform(-.18,.18),rng.uniform(-.14,.14)));phase=float(rng.uniform(0,math.tau));points=[]
            for j in range(29):
                t=j/28;wiggle=Vector((math.sin(t*11+phase),math.sin(t*9+phase*1.7),math.sin(t*13+phase*.7)))*(.022*math.sin(math.pi*t));points.append(origin.lerp(end,t)+bend*math.sin(math.pi*t)+wiggle)
            pivot=points[19];fork_end=end+Vector((rng.uniform(-.13,.13),rng.uniform(-.13,.13),rng.uniform(-.10,.10)));branch=[]
            for j in range(12):
                t=j/11;branch.append(pivot.lerp(fork_end,t)+Vector((.035*math.sin(t*8+phase),.025*math.sin(t*9+phase),.03*math.sin(t*7+phase)))*math.sin(math.pi*t))
            distances=[0.]
            for x,y in zip(points,points[1:]):distances.append(distances[-1]+(y-x).length)
            result.append({'start':start,'points':points,'branch':branch,'lengths':distances,'fork_index':19,'power':.7+.3*float(rng.random()),'width':float(rng.uniform(.055,.085)),'plasma':{'contact_index':k,'center':center.copy(),'angle':a,'nz':nz,'phase':phase,'bend':bend.copy()}})
        self.paths[direction]=result

    def sword_climb_path(self,index,phase):
        swords=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.get('d1r_equipment') and 'sword' in str(o.get('d1r_asset','')).lower()]
        if not swords:raise RuntimeError('Sword climbers requested without a held sword')
        hand=self.rig.matrix_world@self.rig.pose.bones['hand.R'].head
        vertices=[o.matrix_world@v.co for o in swords for v in o.data.vertices]
        tip=max(vertices,key=lambda v:(v-hand).length)
        axis=(tip-hand).normalized();length=(tip-hand).length
        # Each strand has one moving blade contact, not a separate hilt-to-tip leg.
        side=axis.cross(Vector((0,-1,0))).normalized();offset=(index-1)*.018
        # Equally spaced moving contacts; wrap individually at the tip.
        progress=((phase-.07)/.85+index/3)%1
        hilt=hand+axis*.08
        contact=hilt.lerp(tip,progress)+side*offset
        chest=self.rig.matrix_world@self.rig.pose.bones['chest'].head
        chest+=Vector(((index-1)*.10,-.13,.07*index))
        time=phase*math.tau*2;points=[]
        for j in range(29):
            t=j/28;p=contact.lerp(chest,t)
            p+=Vector((-.12,.03,.20))*math.sin(math.pi*t)
            p+=side*(.025*math.sin(t*17-time*3+index))*math.sin(math.pi*t)
            points.append(p)
        return points

    def select_body_contacts(self,count,rng):
        # Select animated surface vertices by region, optionally including held equipment and boots.
        bones=['chest','pelvis','upperArm.L','forearm.L','upperArm.R','forearm.R','thigh.L','shin.L','thigh.R','shin.R']
        regions={name:[] for name in bones}
        self.contact_vertices=[];self.sword_contact_indices=set()
        for obj in bpy.context.scene.objects:
            if obj.type!='MESH':continue
            if obj.get('d1r_equipment'):
                if self.equipment_contacts:
                    region='equipment:'+str(obj.get('d1r_asset',obj.name))
                    regions.setdefault(region,[]).extend((obj,v.index) for v in obj.data.vertices)
                continue
            if not any(m.type=='ARMATURE' and m.object==self.rig for m in obj.modifiers):continue
            if not any(any(token in slot.material.name.lower() for token in ('trs','glv','leg','bts','armor_skin')) for slot in obj.material_slots if slot.material):continue
            groups={g.index:g.name for g in obj.vertex_groups}
            for vertex in obj.data.vertices:
                for group in vertex.groups:
                    name=groups[group.group]
                    if self.equipment_contacts and any(slot.material and 'bts' in slot.material.name.lower() for slot in obj.material_slots):
                        if group.weight>.35 and name in ('shin.L','shin.R','foot.L','foot.R','toe.L','toe.R'):
                            regions.setdefault('boot.'+name[-1],[]).append((obj,vertex.index))
                    if name in regions and group.weight>.35:regions[name].append((obj,vertex.index))
        available=[name for name in regions if regions[name]]
        if not available:raise RuntimeError('No weighted body surfaces found for plasma contacts')
        used=set()
        sword=next((name for name in available if name.startswith('equipment:') and 'sword' in name.lower()),None)
        schedule=[available[k%len(available)] for k in range(count)]
        if self.blade_contacts and sword:
            for k in (0,5,10):
                if k<count:schedule[k]=sword
        for k in range(count):
            region=schedule[k];candidates=regions[region]
            if self.blade_contacts and region==sword:
                hand=self.rig.matrix_world@self.rig.pose.bones['hand.R'].head
                ranked=sorted(candidates,key=lambda item:((item[0].matrix_world@item[0].data.vertices[item[1]].co)-hand).length)
                # Exclude grip/guard and use the exposed middle-to-tip of the blade.
                candidates=ranked[int(len(ranked)*.65):int(len(ranked)*.97)]
                self.sword_contact_indices.add(k)
            order=rng.permutation(len(candidates))
            chosen=next((candidates[int(i)] for i in order if (candidates[int(i)][0].name,candidates[int(i)][1]) not in used),None)
            if chosen is None:raise RuntimeError('Insufficient distinct body contact vertices')
            used.add((chosen[0].name,chosen[1]));self.contact_vertices.append(chosen)
        print('PLASMA_BODY_CONTACTS',count,'regions',available,flush=True)

    def evaluate_body_contacts(self):
        depsgraph=bpy.context.evaluated_depsgraph_get();positions={}
        for obj,index in self.contact_vertices:
            if obj.name in positions:continue
            evaluated=obj.evaluated_get(depsgraph);mesh=evaluated.to_mesh()
            try:
                normal_matrix=evaluated.matrix_world.to_3x3().inverted().transposed()
                positions[obj.name]=[(evaluated.matrix_world@v.co)+(normal_matrix@v.normal).normalized()*.005 for v in mesh.vertices]
            finally:evaluated.to_mesh_clear()
        self.contact_positions=[positions[obj.name][index] for obj,index in self.contact_vertices]

    def moving_plasma_path(self,path,phase):
        if self.plasma_motion<=0:return path
        s=path['plasma'];center=s['center'];seed=s['phase'];time=phase*math.tau*self.plasma_speed
        angle=s['angle']+self.plasma_motion*(.42*math.sin(time*1.6+seed)+.15*math.sin(time*3.2+seed*2))
        nz=max(-.84,min(.96,s['nz']+self.plasma_motion*.16*math.sin(time*1.8+seed)));rad=math.sqrt(1-nz*nz);end=center+Vector((.86*rad*math.cos(angle),.78*rad*math.sin(angle),1.04*nz))
        origin=center+Vector((.045*math.sin(time*1.3+seed),.045*math.cos(time*1.7+seed),.035*math.sin(time*2+seed)))
        if self.body_contacts:
            origin=end.copy()
            end=self.orbit_matrix.inverted()@self.contact_positions[s['contact_index']]
            if self.blade_contacts and s['contact_index'] in self.sword_contact_indices:
                # Approach from outside the sword side rather than crossing the torso.
                target=self.contact_positions[s['contact_index']]
                outward=Vector((target.x-center.x,target.y-center.y,0))
                if outward.length<.01:outward=Vector((-1,0,0))
                outward.normalize()
                origin=self.orbit_matrix.inverted()@(target+outward*.5+Vector((0,0,.18*math.sin(time+seed))))
        bend=s['bend']+Vector((.13*math.sin(time*1.7+seed),.13*math.sin(time*2.2+seed*.7),.10*math.cos(time*1.9+seed*1.4)))*self.plasma_motion;points=[]
        for j in range(29):
            t=j/28;envelope=math.sin(math.pi*t);ripple=Vector((math.sin(t*12-time*3.2+seed),math.sin(t*10-time*2.5+seed*1.7),math.sin(t*15-time*4+seed*.7)))*(.045*envelope*self.plasma_motion)
            points.append(origin.lerp(end,t)+bend*envelope+ripple)
        fork_angle=angle+.18*math.sin(time*2.5+seed);fork_nz=max(-.84,min(.96,nz+.1*math.sin(time*1.3+seed)));fork_r=math.sqrt(1-fork_nz*fork_nz);fork_end=center+Vector((.86*fork_r*math.cos(fork_angle),.78*fork_r*math.sin(fork_angle),1.04*fork_nz));pivot=points[19];branch=[]
        if self.body_contacts:fork_end=end.copy()
        for j in range(12):
            t=j/11;branch.append(pivot.lerp(fork_end,t)+Vector((.04*math.sin(t*9-time*4+seed),.03*math.sin(t*11-time*3+seed),.035*math.sin(t*8-time*3.5+seed)))*math.sin(math.pi*t))
        lengths=[0.]
        for x,y in zip(points,points[1:]):lengths.append(lengths[-1]+(y-x).length)
        return {**path,'points':points,'branch':branch,'lengths':lengths,'power':path['power']*(.82+.18*math.sin(time*4+seed))}

    def build_halo_paths(self,direction):
        rng=np.random.default_rng(self.seed);result=[]
        ground=self.halo_profile=='ground';count=8 if ground else 10
        for k in range(count):
            start=.04+self.activation_spread*float(rng.random());angle=k*math.tau/count+float(rng.uniform(-.14,.14));height=((.18,.40,.65) if ground else (.27,.83,1.40))[k%3]+float(rng.uniform(-.10,.10));radius=.52+float(rng.uniform(-.025,.07));sweep=float(rng.uniform(.9,1.6))*(-1 if k%2 else 1);end_height=max(.08,min(.9 if ground else 1.75,height+float(rng.uniform(-.3,.3))));points=[]
            for j in range(13):
                t=j/12;a=angle+t*sweep;r=radius+.035*math.sin(math.pi*t)
                p=Vector((r*math.cos(a),r*.78*math.sin(a),height+(end_height-height)*t))
                p+=Vector((rng.uniform(-.035,.035),rng.uniform(-.035,.035),rng.uniform(-.045,.045)))*math.sin(math.pi*t)**.35
                points.append(self.cast_start_matrix@p)
            pivot=points[6];end=pivot+Vector((.12*math.cos(angle+.5),.12*math.sin(angle+.5),rng.uniform(-.16,.16)))
            branch=[pivot.lerp(end,j/6)+Vector((rng.uniform(-.014,.014),0,rng.uniform(-.014,.014)))*math.sin(math.pi*j/6) for j in range(7)];distances=[0.]
            for a,b in zip(points,points[1:]):distances.append(distances[-1]+(b-a).length)
            result.append({'start':start,'points':points,'branch':branch,'lengths':distances,'fork_index':6,'power':.72+.28*float(rng.random()),'width':float(rng.uniform(.010,.016))})
        self.paths[direction]=result

    @staticmethod
    def partial(points,distance):
        if distance<=0:return []
        result=[points[0].copy()];travelled=0.
        for a,b in zip(points,points[1:]):
            length=(b-a).length
            if travelled+length>distance:
                result.append(a.lerp(b,(distance-travelled)/max(length,1e-9)));return result
            result.append(b.copy());travelled+=length
        return result

    def update_grow_hold(self,direction,row,rows):
        if direction not in self.paths:self.build_paths(direction)
        phase=min(row,19)/19;idle=rows>20 and row>=20
        verts=[];faces=[];uv=[];strength=[];camera=Vector((0,-.866,.5));active=0
        center=self.cast_start_matrix.translation
        self.orbit_matrix=Matrix.Translation(center)@Matrix.Rotation(phase*self.spin_rate,4,'Z')@Matrix.Translation(-center)
        self.visible_paths=[];tips=[]
        if self.body_contacts:self.evaluate_body_contacts()
        def bolt(points,width,power):
            if len(points)<2:return
            points=[self.orbit_matrix@p for p in points];self.visible_paths.append(points)
            start=len(verts)
            for j,p in enumerate(points):
                tangent=points[min(j+1,len(points)-1)]-points[max(0,j-1)];side=tangent.cross(camera)
                if side.length<1e-6:side=Vector((1,0,0))
                side.normalize();fade=max(0.,math.sin(math.pi*j/(len(points)-1)))**.3
                for u in (0,1):verts.append(tuple(p+side*((u-.5)*width)));uv.append((u,j/(len(points)-1)));strength.append(power*fade)
            for j in range(len(points)-1):faces.append((start+2*j,start+2*j+1,start+2*j+3,start+2*j+2))
        for path in self.paths[direction]:
            if self.path_style=='plasma':path=self.moving_plasma_path(path,phase)
            progress=max(0,min(1,(phase-path['start'])/self.bolt_travel)) if not idle else 0
            if progress<=0:continue
            active+=1;distance=progress*path['lengths'][-1]
            main=self.partial(path['points'],distance);bolt(main,path['width'],path['power'])
            if self.tip_mesh is not None and main:tips.append(self.orbit_matrix@main[-1])
            fork_distance=max(0,distance-path['lengths'][path['fork_index']])
            bolt(self.partial(path['branch'],fork_distance),path['width']*.55,path['power']*.65)
        if self.sword_climbers and not idle:
            for index in range(self.sword_climbers):
                points=self.sword_climb_path(index,phase)
                progress=1 if phase>=.07+index*.045 else 0
                distances=sum((b-a).length for a,b in zip(points,points[1:]))
                visible=self.partial(points,distances*progress)
                bolt([self.orbit_matrix.inverted()@p for p in visible],.045,.95)
                if self.tip_mesh is not None and visible:tips.append(visible[0])
        self.light.data.energy=24*active/len(self.paths[direction]);self.light.location=self.cast_start_matrix@Vector((0,-.2,.85))
        self.mesh.clear_geometry();self.mesh.from_pydata(verts,[],faces);self.mesh.update()
        layer=self.mesh.uv_layers.get('UVMap') or self.mesh.uv_layers.new(name='UVMap');layer.data.foreach_set('uv',np.asarray([uv[x.vertex_index] for x in self.mesh.loops],dtype=np.float32).ravel())
        attribute=self.mesh.attributes.get('fire_strength') or self.mesh.attributes.new('fire_strength','FLOAT','POINT');attribute.data.foreach_set('value',np.asarray(strength,dtype=np.float32));self.obj.hide_render=not verts
        if self.tip_mesh is not None:
            v=[];f=[];tex=[];right=Vector((1,0,0));up=Vector((0,.5,.866))
            for tip in tips:
                start=len(v)
                for x,y in ((0,0),(1,0),(1,1),(0,1)):v.append(tuple(tip+right*((x-.5)*.075)+up*((y-.5)*.075)));tex.append((x,y))
                f.append((start,start+1,start+2,start+3))
            self.tip_mesh.clear_geometry();self.tip_mesh.from_pydata(v,[],f);self.tip_mesh.update();layer=self.tip_mesh.uv_layers.get('UVMap') or self.tip_mesh.uv_layers.new(name='UVMap');layer.data.foreach_set('uv',np.asarray([tex[x.vertex_index] for x in self.tip_mesh.loops],dtype=np.float32).ravel());self.tip_obj.hide_render=not tips
        folder=self.output/f'{direction}-{row}';folder.mkdir(parents=True,exist_ok=True);self.file.directory=str(folder.resolve());self.file.file_name='mask'
