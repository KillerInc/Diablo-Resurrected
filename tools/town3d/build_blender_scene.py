"""Blender --python SCRIPT -- converted-directory output-directory.

Build an isolated editable town scene and three orthographic review cameras.
Materials reference separate replaceable PNGs. Never install a game atlas here.
"""
import json
import math
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector

source, output = (Path(p).resolve() for p in sys.argv[sys.argv.index('--')+1:])
output.mkdir(parents=True,exist_ok=True)
spec=json.loads((source/'scene.json').read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
# Emission-only preview keeps the source palette ungraded and inexpensive.
scene.render.engine='CYCLES'
scene.cycles.samples=16
scene.cycles.use_denoising=False
scene.cycles.max_bounces=1
scene.cycles.transparent_max_bounces=64
scene.render.film_transparent=False
scene.render.image_settings.file_format='PNG'
scene.render.image_settings.color_mode='RGBA'
scene.view_settings.view_transform='Standard'
scene.view_settings.look='None'
scene.view_settings.exposure=0
scene.view_settings.gamma=1
world=bpy.data.worlds.new('Town review background')
world.use_nodes=True
world.node_tree.nodes.get('Background').inputs[0].default_value=(.018,.018,.022,1)
world.node_tree.nodes.get('Background').inputs[1].default_value=1
scene.world=world
collections={}
for name in ['Native terrain and scenery','Tristram buildings','Review cameras']:
    collection=bpy.data.collections.new(name)
    scene.collection.children.link(collection)
    collections[name]=collection

materials=[]
for i,entry in enumerate(spec['materials']):
    material=bpy.data.materials.new(entry['name'])
    material.use_nodes=True
    material['source_texture_id']=i
    material['replaceable_base_color']=entry['image']
    image=bpy.data.images.load(str(source/entry['image']),check_existing=True)
    nodes=material.node_tree.nodes
    nodes.clear()
    texture=nodes.new('ShaderNodeTexImage');texture.image=image
    texture.interpolation='Closest'
    texture.extension='REPEAT' if entry['repeat'] else 'CLIP'
    texture.label='Replace this image for higher-resolution artwork'
    emission=nodes.new('ShaderNodeEmission')
    material.node_tree.links.new(texture.outputs['Color'],emission.inputs[0])
    destination=nodes.new('ShaderNodeOutputMaterial')
    if entry.get('architecture'):
        # Projected-front coverage must not cut holes through solid unseen walls.
        mix=nodes.new('ShaderNodeMixRGB')
        mix.inputs[1].default_value=(.012,.009,.0065,1)
        material.node_tree.links.new(texture.outputs['Alpha'],mix.inputs[0])
        material.node_tree.links.new(texture.outputs['Color'],mix.inputs[2])
        material.node_tree.links.new(mix.outputs[0],emission.inputs[0])
        material.node_tree.links.new(emission.outputs[0],destination.inputs[0])
    else:
        transparent=nodes.new('ShaderNodeBsdfTransparent')
        mix=nodes.new('ShaderNodeMixShader')
        material.node_tree.links.new(texture.outputs['Alpha'],mix.inputs[0])
        material.node_tree.links.new(transparent.outputs[0],mix.inputs[1])
        material.node_tree.links.new(emission.outputs[0],mix.inputs[2])
        material.node_tree.links.new(mix.outputs[0],destination.inputs[0])
    materials.append(material)

meshes=np.load(source/'meshes.npz')
building_roots={}
triangles=0
for i,entry in enumerate(spec['meshes']):
    data=meshes[entry['key']]
    count=len(data)
    assert count % 3 == 0 and np.isfinite(data).all()
    coordinates=np.stack((data[:,0],-data[:,2],data[:,1]*spec['blender_height_scale']),axis=1).astype(np.float32)
    mesh=bpy.data.meshes.new(entry['name'])
    mesh.vertices.add(count)
    mesh.vertices.foreach_set('co',coordinates.ravel())
    mesh.loops.add(count)
    mesh.loops.foreach_set('vertex_index',np.arange(count,dtype=np.int32))
    mesh.polygons.add(count//3)
    mesh.polygons.foreach_set('loop_start',np.arange(0,count,3,dtype=np.int32))
    mesh.polygons.foreach_set('loop_total',np.full(count//3,3,dtype=np.int32))
    uv=mesh.uv_layers.new(name='Source UV - retain for texture replacement')
    coords=data[:,3:5].copy();coords[:,1]=1-coords[:,1]
    uv.data.foreach_set('uv',coords.ravel())
    mesh.materials.append(materials[entry['material']])
    mesh.update()
    obj=bpy.data.objects.new(entry['name'],mesh)
    collections[entry['collection']].objects.link(obj)
    obj['source_mesh_key']=entry['key']
    if entry.get('building'):
        identity=entry['building']
        if identity not in building_roots:
            parent=bpy.data.objects.new(identity,None)
            collections['Tristram buildings'].objects.link(parent)
            record=next(b for b in spec['buildings'] if b['id']==identity)
            parent['native_min']=record['native_min'];parent['native_max']=record['native_max']
            parent['source_sha256']=record['sha256']
            building_roots[identity]=parent
        obj.parent=building_roots[identity]
        obj['surface_material']=entry['surface']
    triangles+=count//3
    if i % 200 == 0:print('IMPORTED',i,len(spec['meshes']),flush=True)

# The game's void is black. A black backing below the grid also gives alpha
# edges their correct background, rather than the grey review-world colour.
backing_mesh=bpy.data.meshes.new('Native grid black backing')
backing_mesh.from_pydata([(-1,1,-.05),(112,1,-.05),(112,-112,-.05),(-1,-112,-.05)],[],[(0,1,2,3)])
backing=bpy.data.objects.new('Native grid black backing',backing_mesh)
collections['Native terrain and scenery'].objects.link(backing)
black=bpy.data.materials.new('Original void black');black.use_nodes=True
nodes=black.node_tree.nodes;nodes.clear();em=nodes.new('ShaderNodeEmission');em.inputs[0].default_value=(0,0,0,1)
dest=nodes.new('ShaderNodeOutputMaterial');black.node_tree.links.new(em.outputs[0],dest.inputs[0]);backing_mesh.materials.append(black)
center=Vector((55,-55,0))
def camera(name, elevation, scale, resolution):
    data=bpy.data.cameras.new(name);data.type='ORTHO';data.ortho_scale=scale
    obj=bpy.data.objects.new(name,data)
    collections['Review cameras'].objects.link(obj)
    a=math.radians(elevation)
    direction=Vector((math.cos(a)/math.sqrt(2),-math.cos(a)/math.sqrt(2),math.sin(a)))
    obj.location=center+direction*200
    obj.rotation_euler=(center-obj.location).to_track_quat('-Z','Y').to_euler()
    obj['render_resolution']=list(resolution)
    obj['elevation_degrees']=elevation
    return obj

views=[camera('Birds eye - 55 degrees',55,163,(2560,2048)),
       camera('Overhead - orthographic',90,163,(2560,2560)),
       camera('Diablo native - 2 to 1 tile diamonds',30,163,(3072,2048))]
scene['native_grid']=[112,112]
scene['native_units']='one grid cell; original (x,height,z) maps to (x,-z,height*sqrt(2/3))'
scene['preview_status']='Layout candidate; not a verified one-to-one replacement or production atlas'
scene['source_manifest']=str(source/'scene.json')
scene['lighting_mode']='Unlit palette reference; original alpha retained'
scene.camera=views[0]
scene.render.resolution_x,scene.render.resolution_y=views[0]['render_resolution']
scene.render.resolution_percentage=100
scene.view_settings.exposure=1
for area in bpy.context.screen.areas if bpy.context.screen else []:
    if area.type=='VIEW_3D':
        area.spaces.active.region_3d.view_distance=150
        area.spaces.active.region_3d.view_location=center
        area.spaces.active.clip_end=1000
# Relative external images stay editable; a packed scene is also self contained.
for image in bpy.data.images:
    if image.source=='FILE':image.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(output/'Tristram-authoring.blend'),compress=True)
names=['Tristram-birds-eye.png','Tristram-overhead.png','Tristram-native-camera.png']
for view,name in zip(views,names):
    scene.camera=view
    scene.render.resolution_x,scene.render.resolution_y=view['render_resolution']
    scene.view_settings.exposure=1 if view!=views[2] else 0
    scene.render.filepath=str(output/name)
    bpy.ops.render.render(write_still=True)
    print('RENDERED',name,flush=True)
(output/'blender-audit.json').write_text(json.dumps({'mesh_objects':len(spec['meshes']),
    'building_groups':len(building_roots),'triangles':triangles,'materials':len(materials),
    'native_grid':[112,112],'height_scale':spec['blender_height_scale'],
    'renders':names,'limitations':spec['limitations']},indent=2))
