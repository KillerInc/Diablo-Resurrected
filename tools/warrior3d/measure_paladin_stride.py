"""Measure all 40 source poses' boot contact and foot forward excursion.

Blender --python SCRIPT -- INPUT.glb OUTPUT.json
The result can supply the optional grounding input to shorten_paladin_stride.py.
"""
import bpy,sys,json
from pathlib import Path
bpy.context.scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=sys.argv[sys.argv.index('--')+1])
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');boots=next(o for o in bpy.data.objects if o.type=='MESH' and o.data.materials and 'base05_BTS' in o.data.materials[0].name)
mins=[];feet=[]
for frame in range(40):
 bpy.context.scene.frame_set(frame);bpy.context.view_layer.update();ev=boots.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();mins.append(min((ev.matrix_world@v.co).z for v in me.vertices));ev.to_mesh_clear();feet.append([list(rig.pose.bones[n].head) for n in ['foot.L','foot.R']])
Path(sys.argv[sys.argv.index('--')+2]).write_text(json.dumps({'boot_min_z':mins,'root_vertical_correction':[.003-z for z in mins],'forward_excursion':[max(p[s][1] for p in feet)-min(p[s][1] for p in feet) for s in range(2)]},indent=2))
