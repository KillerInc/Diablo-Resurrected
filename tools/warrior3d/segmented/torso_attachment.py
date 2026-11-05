"""Separate torso-side skin patches that were grouped into arm meshes."""
import bpy,numpy as np

def skin_face(obj,face,uvs,image_pixels):
    if image_pixels is None:return True
    uv=sum((uvs[i] for i in face.loop_indices),uvs[face.loop_start]*0)/len(face.loop_indices)
    pixels=image_pixels;h,w=pixels.shape[:2];r,g,b=pixels[min(h-1,max(0,int(uv.y*h))),min(w-1,max(0,int(uv.x*w))),:3]
    return r-g>.025 and g-b>.02 and r-b>.07 and r>.23

def anchor_torso_skin(rig):
    inv=rig.matrix_world.inverted();report=[]
    for index,side in ((6,'R'),(8,'L')):
        obj=bpy.data.objects[f'tripo_part_{index}'];old=obj.data
        uvs=[v.uv.copy() for v in old.uv_layers.active.data]
        image=next((node.image for mat in old.materials if mat and mat.use_nodes for node in mat.node_tree.nodes if node.type=='TEX_IMAGE' and node.image and 'basecolor' in node.image.name.lower()),None)
        pixels=np.array(image.pixels[:]).reshape(image.size[1],image.size[0],4) if image else None
        selected=[];keep=[]
        for face in old.polygons:
            point=sum((inv@obj.matrix_world@old.vertices[i].co for i in face.vertices),old.vertices[0].co*0)/len(face.vertices)
            medial=(point.x>-.109 if side=='R' else point.x<.151)
            region=medial and (.65<point.z<.746 if side=='R' else .625<point.z<.742)
            if region and (side=='R' or skin_face(obj,face,uvs,pixels)):selected.append(face.index)
            else:keep.append(face.index)
        assert selected,(side,'No torso skin selected')
        ids=sorted({i for f in selected for i in old.polygons[f].vertices});lookup={v:i for i,v in enumerate(ids)}
        patch=bpy.data.meshes.new(f'{side} torso-side skin patch')
        patch.from_pydata([old.vertices[i].co[:] for i in ids],[],[tuple(lookup[i] for i in old.polygons[f].vertices) for f in selected]);patch.update()
        new=bpy.data.objects.new('Torso-attached skin '+side,patch);bpy.context.scene.collection.objects.link(new);new.matrix_world=obj.matrix_world.copy()
        for mat in old.materials:patch.materials.append(mat)
        layer=patch.uv_layers.new(name='UVMap')
        for face,original_id in zip(patch.polygons,selected):
            original=old.polygons[original_id];face.use_smooth=True;face.material_index=original.material_index
            for loop,new_loop in zip(original.loop_indices,face.loop_indices):layer.data[new_loop].uv=uvs[loop]
        chest=new.vertex_groups.new(name='Spine02');chest.add(list(range(len(ids))),1,'REPLACE')
        mod=new.modifiers.new('Torso-only skin attachment','ARMATURE');mod.object=rig
        new['attachment']='Spine02 only; removed from upper-arm mesh'
        # Preserve source vertex/edge indices and skin groups, removing faces only.
        mesh=bpy.data.meshes.new(old.name+' arm without torso skin')
        mesh.from_pydata([v.co[:] for v in old.vertices],[tuple(e.vertices) for e in old.edges],[tuple(old.polygons[f].vertices) for f in keep]);mesh.update()
        for mat in old.materials:mesh.materials.append(mat)
        layer=mesh.uv_layers.new(name='UVMap')
        for face,original_id in zip(mesh.polygons,keep):
            original=old.polygons[original_id];face.use_smooth=original.use_smooth;face.material_index=original.material_index
            for loop,new_loop in zip(original.loop_indices,face.loop_indices):layer.data[new_loop].uv=uvs[loop]
        # Mesh replacement needs explicit weight copy; vertex groups live on object.
        group_names=[g.name for g in obj.vertex_groups]
        assignments=[[(g.group,g.weight) for g in v.groups] for v in old.vertices]
        obj.data=mesh
        for group in list(obj.vertex_groups):obj.vertex_groups.remove(group)
        for name in group_names:obj.vertex_groups.new(name=name)
        for i,groups in enumerate(assignments):
            for group,w in groups:obj.vertex_groups[group].add([i],w,'REPLACE')
        # Close the cut arm-side opening, without returning the torso patch to
        # the arm. Match source rim weights so the new cap cannot detach.
        labels={}
        selected_set=set(selected)
        for face in old.polygons:
            for a,b in face.edge_keys:
                key=tuple(sorted((tuple(round(c,5) for c in old.vertices[a].co),tuple(round(c,5) for c in old.vertices[b].co))))
                labels.setdefault(key,[]).append((face.index in selected_set,a,b))
        rim=[]
        for entries in labels.values():
            if any(x[0] for x in entries) and any(not x[0] for x in entries):
                _,a,b=next(x for x in entries if not x[0]);rim.append((a,b))
        if rim:
            rim_ids=sorted({i for edge in rim for i in edge});mapping={v:i for i,v in enumerate(rim_ids)}
            center=sum((old.vertices[i].co for i in rim_ids),old.vertices[0].co*0)/len(rim_ids)
            vertices=[old.vertices[i].co[:] for i in rim_ids]+[center[:]]
            cap=bpy.data.meshes.new('Arm opening closure '+side);cap.from_pydata(vertices,[],[(mapping[a],mapping[b],len(rim_ids)) for a,b in rim]);cap.update()
            closure=bpy.data.objects.new(cap.name,cap);bpy.context.scene.collection.objects.link(closure);closure.matrix_world=obj.matrix_world.copy()
            mat=bpy.data.materials.new('Inner upper arm skin '+side);mat.use_nodes=True;shader=mat.node_tree.nodes['Principled BSDF'];shader.inputs['Base Color'].default_value=(.18,.145,.12,1);shader.inputs['Roughness'].default_value=.85;cap.materials.append(mat)
            for face in cap.polygons:face.use_smooth=True
            cap_groups={name:closure.vertex_groups.new(name=name) for name in group_names};average={}
            for i,source_id in enumerate(rim_ids):
                for group,w in assignments[source_id]:
                    cap_groups[group_names[group]].add([i],w,'REPLACE');average[group]=average.get(group,0)+w/len(rim_ids)
            for group,w in average.items():cap_groups[group_names[group]].add([len(rim_ids)],w,'REPLACE')
            mod=closure.modifiers.new('Matched arm-rim skin weights','ARMATURE');mod.object=rig;mod.use_deform_preserve_volume=True
        report.append({'side':side,'torso_attached_faces':len(selected),'fully_chest_pinned_vertices':len(ids),'separate_surface':new.name})
    return report

def pinned_skin_error(rig):
    deps=bpy.context.evaluated_depsgraph_get();transform=rig.matrix_world@rig.pose.bones['Spine02'].matrix@rig.data.bones['Spine02'].matrix_local.inverted();maximum=0;inv=rig.matrix_world.inverted()
    for obj in bpy.data.objects:
        if obj.type!='MESH' or not obj.name.startswith('Torso-attached skin '):continue
        ev=obj.evaluated_get(deps);mesh=ev.to_mesh()
        for vertex in obj.data.vertices:
            expected=transform@(inv@obj.matrix_world@vertex.co)
            maximum=max(maximum,(ev.matrix_world@mesh.vertices[vertex.index].co-expected).length)
        ev.to_mesh_clear()
    return maximum
