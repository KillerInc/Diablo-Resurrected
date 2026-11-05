"""Blender: render building groups at exact native pixel registration.

Arguments after --: scene.blend registrations.json output-directory
Use the same fixed 30-degree camera calibration; never fit each render by eye.
"""
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector

scene_file,registration_file,output=(Path(p).resolve() for p in sys.argv[sys.argv.index('--')+1:])
output.mkdir(parents=True,exist_ok=True)
registrations=json.loads(registration_file.read_text())
bpy.ops.wm.open_mainfile(filepath=str(scene_file))
scene=bpy.context.scene
scene.render.film_transparent=True
scene.view_settings.exposure=0
scene.cycles.samples=16
camera=bpy.data.objects['Diablo native - 2 to 1 tile diamonds']
camera.data.sensor_fit='HORIZONTAL'
scene.camera=camera
for entry in registrations['groups']:
    identity=entry['ids'][0]
    left,top=entry['comparison_origin'];width,height=entry['comparison_size']
    x,y=left+width/2,top+height/2
    gx=(x/32+y/16)/2;gz=(y/16-x/32)/2
    target=Vector((gx,-gz,0))
    direction=Vector((math.sqrt(3/8),-math.sqrt(3/8),.5))
    camera.location=target+200*direction
    camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.ortho_scale=width/(32*math.sqrt(2))
    for obj in scene.objects:
        if obj.type=='MESH':
            obj.hide_render=not (obj.parent and obj.parent.name in entry['ids'])
    scene.render.resolution_x=width;scene.render.resolution_y=height
    scene.render.resolution_percentage=100
    scene.render.filepath=str(output/(identity+'-new.png'))
    bpy.ops.render.render(write_still=True)
    print('NATIVE COMPARISON',identity,flush=True)
