"""Blender: rebuild shadows only from a private JSON recipe, keeping body cells.

Usage: blender -b --python render_npc_shadows.py -- recipe.json output
The recipe supplies source scene, exact native-frame samples and camera fit.
No game artwork is included. World sun (3,-4,6) is expressed relative to the
sprite camera, as in the player's fixed-camera renderer, never the NPC's yaw.
"""
import json
import math
import sys
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

recipe, output = map(Path, sys.argv[sys.argv.index('--') + 1:])
spec = json.loads(recipe.read_text())
output.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=spec['source'])
scene = bpy.context.scene
camera = scene.camera
w, h = spec['cell']
scene.render.resolution_x = w
scene.render.resolution_y = h
scene.render.resolution_percentage = 100
scene.render.film_transparent = True
scene.render.image_settings.color_mode = 'RGBA'
actors = [o for o in scene.objects if o.type == 'MESH' and not o.hide_render
          and not o.name.startswith('Icosphere')]

def set_frame(time):
    scene.frame_set(math.floor(time), subframe=time-math.floor(time))
    bpy.context.view_layer.update()

def bounds(times):
    points = []
    for time in times:
        set_frame(time)
        deps = bpy.context.evaluated_depsgraph_get()
        for obj in actors:
            ev = obj.evaluated_get(deps)
            points.extend(world_to_camera_view(scene, camera, obj.matrix_world @ v.co)
                          for v in ev.data.vertices)
    return (min(p.x*w for p in points), min(p.y*h for p in points),
            max(p.x*w for p in points), max(p.y*h for p in points))

if spec['fit'] in ('standing', 'griswold'):
    angle = math.radians(spec.get('camera_yaw', 0))
    center = Vector((0, 0, .89))
    camera.location = center + Vector((math.sin(angle)*6, -math.cos(angle)*6, 3.464))*1.82
    camera.rotation_euler = (center-camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.ortho_scale = 2.5
    if spec['fit'] == 'griswold':
        camera.data.ortho_scale = 1.82*1.22*384/560*spec['reference_height']/260
    else:
        x0, y0, x1, y1 = bounds([1])
        camera.data.ortho_scale *= (y1-y0)/spec['target']
    bpy.context.view_layer.update()
    p = world_to_camera_view(scene, camera, Vector((0, 0, 0)))
    right = camera.rotation_euler.to_matrix() @ Vector((1, 0, 0))
    up = camera.rotation_euler.to_matrix() @ Vector((0, 1, 0))
    camera.location += right*((p.x*w-192)/w*camera.data.ortho_scale) + up*((340-(1-p.y)*h)/h*camera.data.ortho_scale)
else:
    x0, y0, x1, y1 = bounds(spec['times'])
    camera.data.ortho_scale *= ((y1-y0) if spec['fit']=='height' else (x1-x0))/spec['target']
    bpy.context.view_layer.update()
    x0, y0, x1, y1 = bounds(spec['times'])
    right = camera.rotation_euler.to_matrix() @ Vector((1, 0, 0))
    up = camera.rotation_euler.to_matrix() @ Vector((0, 1, 0))
    camera.location += right*((x0+x1)/2-spec['cx'])/w*camera.data.ortho_scale*(w/h) + up*(y0-(h-spec['bottom']))/h*camera.data.ortho_scale

# Rotate the player's canonical ground ray with the camera's horizontal basis.
# Rotating an NPC/camera pair must not rotate the on-screen sunlight.
right = camera.rotation_euler.to_matrix() @ Vector((1, 0, 0))
right.z = 0
right.normalize()
forward = Vector((-right.y, right.x, 0))
ray = right*(-3/6) + forward*(4/6)
material = bpy.data.materials.new('Player-rule projected ground shadow')
material.use_nodes = True
nodes = material.node_tree.nodes
nodes.clear()
emission = nodes.new('ShaderNodeEmission')
emission.inputs[0].default_value = (0, 0, 0, 1)
surface = nodes.new('ShaderNodeOutputMaterial')
material.node_tree.links.new(emission.outputs[0], surface.inputs[0])
mesh = bpy.data.meshes.new('Ground silhouette')
shadow = bpy.data.objects.new('Ground silhouette', mesh)
scene.collection.objects.link(shadow)
mesh.materials.append(material)
excluded = set()
for row, time in enumerate(spec['times']):
    set_frame(time)
    deps = bpy.context.evaluated_depsgraph_get()
    vertices, faces = [], []
    for obj in actors:
        if obj.name.lower().startswith(('blood', 'rune', 'particle')):
            excluded.add(obj.name)
            continue
        ev = obj.evaluated_get(deps)
        evaluated = ev.to_mesh()
        offset = len(vertices)
        for v in evaluated.vertices:
            p = ev.matrix_world @ v.co
            vertices.append((p.x+ray.x*max(0, p.z), p.y+ray.y*max(0, p.z), .002))
        for poly in evaluated.polygons:
            mat = evaluated.materials[poly.material_index] if evaluated.materials else None
            name = mat.name.lower() if mat else ''
            # Match player casters: no alpha hair cards, face overlays or effects.
            if any(t in name for t in ('_har', 'eyelash', 'eyeshadow', '_eye', 'rune', 'particle')):
                excluded.add(name)
                continue
            faces.append(tuple(offset+i for i in poly.vertices))
        ev.to_mesh_clear()
    mesh.clear_geometry()
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    for obj in scene.objects:
        if obj.type in ('MESH', 'CURVE'):
            obj.hide_render = obj != shadow
    scene.render.filepath = str(output/f'shadow-{row:02}.png')
    bpy.ops.render.render(write_still=True)
    print('SHADOW', spec['name'], row, flush=True)
(output/'audit.json').write_text(json.dumps({'recipe': spec, 'ray_world': list(ray),
    'camera_right': list(right), 'sun_camera_relative': [3,-4,6],
    'excluded_materials': sorted(excluded), 'ground_z': .002,
    'opacity': .7, 'blur_pixels_at_4x': 1, 'body_rerendered': False}, indent=2))
