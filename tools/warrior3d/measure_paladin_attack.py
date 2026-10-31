"""Blender --python SCRIPT -- INPUT.glb OUTPUT.json

Evaluate every integer animation sample's boot ground contact and foot positions.
The JSON is input to sample_paladin_kick.py's optional support-foot correction.
"""
import bpy,json,sys
from pathlib import Path
src,out=sys.argv[sys.argv.index('--')+1:]
bpy.context.scene.render.fps=30
bpy.ops.import_scene.gltf(filepath=src)
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
boots=next(o for o in bpy.data.objects if o.type=='MESH' and o.data.materials and 'base05_BTS' in o.data.materials[0].name)
first,last=rig.animation_data.action.frame_range
report=[]
for frame in range(round(first),round(last)+1):
    bpy.context.scene.frame_set(frame);bpy.context.view_layer.update()
    ev=boots.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh()
    z=min((ev.matrix_world@v.co).z for v in mesh.vertices);ev.to_mesh_clear()
    report.append({'frame':frame,'boot_min_z':z,'bones':{
        n:list(rig.matrix_world@rig.pose.bones[n].head)
        for n in ['root','pelvis','shin.R','ankle.R','foot.L','foot.R']}})
Path(out).write_text(json.dumps(report,indent=2))
print('Measured',len(report),'poses; boot Z range:',min(r['boot_min_z'] for r in report),max(r['boot_min_z'] for r in report))
