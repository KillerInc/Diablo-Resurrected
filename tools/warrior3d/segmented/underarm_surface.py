"""Add deforming underarm surface bridges between segmented arm rims and torso.
Each endpoint copies the exact position and weights of its adjoining source mesh.
No original textures are copied into the repository; existing material/UVs are reused.
"""
import bpy
from mathutils.kdtree import KDTree

def connect_underarms(rig):
    chest=bpy.data.objects['tripo_part_2'];inv=rig.matrix_world.inverted()
    tree=KDTree(len(chest.data.vertices))
    for vertex in chest.data.vertices:tree.insert(inv@chest.matrix_world@vertex.co,vertex.index)
    tree.balance();bridges=[];report=[]
    def weights(obj,vertex):
        return {obj.vertex_groups[g.group].name:g.weight for g in vertex.groups if g.weight>0}
    for index,side in [(6,'R'),(8,'L')]:
        source=bpy.data.objects[f'tripo_part_{index}']
        # Collapse coincident UV-split vertex IDs for boundary detection only.
        keys={v.index:tuple(round(float(c),5) for c in v.co) for v in source.data.vertices}
        def edge_key(a,b):return tuple(sorted((keys[a],keys[b])))
        edge_counts={edge_key(*e.vertices):0 for e in source.data.edges}
        for face in source.data.polygons:
            for pair in face.edge_keys:edge_counts[edge_key(*pair)]+=1
        shoulder=rig.data.bones[side+'_Upperarm'].head_local
        edges=[]
        for edge in source.data.edges:
            if edge_counts[edge_key(*edge.vertices)]!=1:continue
            points=[inv@source.matrix_world@source.data.vertices[i].co for i in edge.vertices]
            center=sum(points,points[0]*0)/2
            if center.z>.70 and (center-shoulder).length<.115:
                edges.append(tuple(edge.vertices))
        assert edges, f'No shoulder rim found for {side}'
        ids=sorted(set(i for edge in edges for i in edge));lookup={v:i for i,v in enumerate(ids)}
        uv_by_vertex={}
        if source.data.uv_layers.active:
            for loop in source.data.loops:uv_by_vertex.setdefault(loop.vertex_index,source.data.uv_layers.active.data[loop.index].uv.copy())
        vertices=[];all_weights=[];uvs=[];spans=[];target_ids=[]
        for row in range(5):
            t=row/4
            for i in ids:
                vertex=source.data.vertices[i];start=inv@source.matrix_world@vertex.co
                end,j,distance=tree.find(start);spans.append(distance)
                if row==0:target_ids.append(j)
                vertices.append(tuple(start.lerp(end,t)))
                wa=weights(source,vertex);wb=weights(chest,chest.data.vertices[j])
                names=set(wa)|set(wb)
                all_weights.append({name:wa.get(name,0)*(1-t)+wb.get(name,0)*t for name in names})
                uvs.append(uv_by_vertex.get(i,(0,0)))
        faces=[];width=len(ids)
        for row in range(4):
            for a,b in edges:
                x=row*width+lookup[a];y=row*width+lookup[b]
                faces.append((x,y,y+width,x+width))
        mesh=bpy.data.meshes.new(f'{side} underarm connected surface');mesh.from_pydata(vertices,[],faces);mesh.update()
        obj=bpy.data.objects.new(mesh.name,mesh);bpy.context.scene.collection.objects.link(obj)
        obj.matrix_world=rig.matrix_world.copy()
        # Reconstructed surface has no matching source UV coverage.
        material=bpy.data.materials.new(f'{side} reconstructed underarm')
        material.use_nodes=True;shader=material.node_tree.nodes.get('Principled BSDF')
        shader.inputs['Base Color'].default_value=(.21,.145,.105,1) if side=='R' else (.065,.055,.045,1)
        shader.inputs['Roughness'].default_value=.85
        mesh.materials.append(material)
        layer=mesh.uv_layers.new(name='UVMap')
        for face in mesh.polygons:
            face.use_smooth=True
            for loop_index in face.loop_indices:layer.data[loop_index].uv=uvs[mesh.loops[loop_index].vertex_index]
        groups={n:obj.vertex_groups.new(name=n) for n in sorted({n for ws in all_weights for n in ws})}
        for i,ws in enumerate(all_weights):
            total=sum(ws.values())
            for n,w in ws.items():
                if w>0:groups[n].add([i],w/total,'REPLACE')
        modifier=obj.modifiers.new('Shared torso and arm deformation','ARMATURE');modifier.object=rig
        obj['arm_vertex_ids']=ids;obj['torso_vertex_ids']=target_ids;obj['arm_part']=source.name
        obj['join_method']='Exact endpoint position and weight match to source arm rim and torso vertex'
        bridges.append(obj);report.append({'side':side,'rim_edges':len(edges),'vertices':len(vertices),'maximum_rest_span':max(spans)})
    return bridges,report

def endpoint_error(rig,bridges):
    deps=bpy.context.evaluated_depsgraph_get();chest=bpy.data.objects['tripo_part_2'];maximum=0
    def points(obj):
        ev=obj.evaluated_get(deps);mesh=ev.to_mesh();result=[ev.matrix_world@v.co for v in mesh.vertices];ev.to_mesh_clear();return result
    torso=points(chest)
    for bridge in bridges:
        seam=points(bridge);arm=points(bpy.data.objects[bridge['arm_part']]);ids=list(bridge['arm_vertex_ids']);targets=list(bridge['torso_vertex_ids']);width=len(ids)
        for i,(a,b) in enumerate(zip(ids,targets)):
            maximum=max(maximum,(seam[i]-arm[a]).length,(seam[4*width+i]-torso[b]).length)
    return maximum
