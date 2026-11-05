"""Blender: overlap a separate pants mesh beneath its torso without moving legs.

Arguments: source.blend output.blend material-token transition-bottom lift
Only upper pants vertices change in rest space; retain UVs, weights, animation,
feet, materials and all other geometry. Source artwork stays private.
"""
import json
import sys
from pathlib import Path
import bpy

source, output, token, bottom, lift = sys.argv[sys.argv.index('--')+1:]
bottom, lift = float(bottom), float(lift)
bpy.ops.wm.open_mainfile(filepath=str(Path(source).resolve()))
matches = [o for o in bpy.context.scene.objects if o.type == 'MESH'
           and not o.hide_render and any(token in m.name for m in o.data.materials if m)]
assert len(matches) == 1, [o.name for o in matches]
obj = matches[0]
top = max((obj.matrix_world @ v.co).z for v in obj.data.vertices)
assert top > bottom and 0 < lift < .2
inverse = obj.matrix_world.inverted()
changed = 0
for vertex in obj.data.vertices:
    point = obj.matrix_world @ vertex.co
    if point.z <= bottom:
        continue
    t = min(1, (point.z-bottom)/(top-bottom))
    point.z += lift*t*t*(3-2*t)
    vertex.co = inverse @ point
    changed += 1
obj.data.update()
destination = Path(output).resolve()
destination.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(destination), compress=True)
destination.with_suffix('.waist.json').write_text(json.dumps({
    'source':str(Path(source).resolve()),'mesh':obj.name,'material':token,
    'transition_bottom':bottom,'original_top':top,'lift':lift,
    'changed_vertices':changed,'total_vertices':len(obj.data.vertices),
    'weights_uvs_animation_unchanged':True}, indent=2))
