"""Run with Blender after loading the generated .blend file."""
import json
import math
from pathlib import Path
import sys
import bpy

output=Path(sys.argv[sys.argv.index('--')+1]).resolve() if '--' in sys.argv else None
rig=bpy.data.objects.get('Warrior_Rig')
assert rig and rig.type=='ARMATURE'
assert len(rig.data.bones)==18
meshes=[obj for obj in bpy.data.objects if obj.type=='MESH']
assert len(meshes)>20
assert bpy.data.objects.get('Steel shoulder L')
assert not bpy.data.objects.get('Steel shoulder R')
assert not bpy.data.objects.get('Pauldron lower plate R')
assert all(any(mod.type=='ARMATURE' and mod.object==rig for mod in obj.modifiers) for obj in meshes)
assert not any(image.packed_file or (image.filepath and image.source in {'FILE','SEQUENCE','MOVIE'}) for image in bpy.data.images)
assert bpy.context.scene.camera.data.type=='ORTHO'
assert bpy.context.scene.render.film_transparent
assert bpy.context.scene.render.image_settings.color_mode=='RGBA'
results={}
for name,count in [('Warrior_idle',10),('Warrior_walk',8)]:
    action=bpy.data.actions.get(name)
    assert action and action['sprite_frame_count']==count
    rig.animation_data.action=action
    sampled=[]; wrists=[]; feet=[]
    for frame in range(1,count+2):
        bpy.context.scene.frame_set(frame)
        values=[value for bone in rig.pose.bones for row in bone.matrix for value in row]
        assert all(math.isfinite(value) for value in values)
        sampled.append(values)
        wrists.append(rig.pose.bones['hand.L'].head.copy())
        feet.append(rig.pose.bones['foot.L'].head.copy())
    loop_error=max(abs(a-b) for a,b in zip(sampled[0],sampled[-1]))
    motion=max(abs(a-b) for sample in sampled[1:-1] for a,b in zip(sampled[0],sample))
    assert loop_error<1e-4,(name,loop_error)
    assert motion>1e-5,(name,'static animation')
    fore_aft=max(v.y for v in wrists)-min(v.y for v in wrists)
    vertical=max(v.z for v in wrists)-min(v.z for v in wrists)
    if name=='Warrior_idle':
        assert max(v.z for v in wrists)<1.0, 'Idle hands should hang beside hips'
    else:
        assert fore_aft>3*vertical, 'Arm swing must travel mainly forward/back'
        assert sum((w.y-sum(v.y for v in wrists)/len(wrists))*(f.y-sum(v.y for v in feet)/len(feet)) for w,f in zip(wrists,feet))<0, 'Arm must oppose same-side leg'
    bpy.context.scene.frame_set(1)
    results[name]={'frames':count,'maximum_loop_matrix_error':loop_error,'motion_detected':True,
                   'first_left_wrist':list(rig.pose.bones['hand.L'].head)}
report={'passed':True,'mesh_objects':len(meshes),'bones':len(rig.data.bones),
        'vertices':sum(len(obj.data.vertices) for obj in meshes),'reference_art_embedded':False,
        'orthographic_camera':True,'transparent_rgba':True,'animations':results}
if output: output.write_text(json.dumps(report,indent=2))
if '--compress' in sys.argv:
    rig.animation_data.action=bpy.data.actions['Warrior_idle']
    bpy.context.scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath,compress=True)
print('WARRIOR_RIG_VALIDATION',json.dumps(report),flush=True)
