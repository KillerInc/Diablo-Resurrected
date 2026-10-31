"""Blender --python SCRIPT -- QUIVER_PLAN.json APPROVED_QUIVER.glb
Map each consolidated triangle to its original private mesh component.
"""
import bpy,json,sys
from pathlib import Path
plan_file,source=map(Path,sys.argv[sys.argv.index('--')+1:]);w=plan_file.resolve().parent;bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(source.resolve()));bpy.context.view_layer.update();lookup={}
def key(v):return tuple(round(x,5) for x in v)
for o in bpy.data.objects:
 if o.type!='MESH':continue
 o.data.calc_loop_triangles()
 for t in o.data.loop_triangles:
  c=sum((o.matrix_world@o.data.vertices[i].co for i in t.vertices),__import__('mathutils').Vector())/3;lookup[key(c)]=o.name
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(w/'quiver-six-arrows.glb'));o=next(o for o in bpy.data.objects if o.type=='MESH');o.data.calc_loop_triangles();names=[]
for t in o.data.loop_triangles:
 c=sum((o.data.vertices[i].co for i in t.vertices),__import__('mathutils').Vector())/3;names.append(lookup.get(key(c),'unknown'))
(w/'triangle-parts.json').write_text(json.dumps(names));assert "unknown" not in names, "Consolidated triangle provenance mismatch"
