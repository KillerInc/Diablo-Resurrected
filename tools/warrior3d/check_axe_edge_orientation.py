"""Blender --background --python SCRIPT -- AXE_EDGE_REVISION_PLAN.json
Measure broad-face alignment with perpendicular-to-haft head velocity.
"""
import bpy,json,sys,math
from pathlib import Path
from mathutils import Vector
file=Path(sys.argv[sys.argv.index('--')+1]);root=file.parent;sys.path.insert(0,str(Path(__file__).parent));from paladin_equipment import attach_equipment
plan=json.loads(file.read_text());job=next(j for j in plan['jobs'] if j['action']=='at');ref=json.loads(Path(job['reference']).read_text());bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=job['model']);rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');new=attach_equipment(rig,ref['equipment'])[0];item=dict(ref['equipment'][0]);item.pop('local_basis');old=attach_equipment(rig,[item])[0]
def frame(t):bpy.context.scene.frame_set(int(t),subframe=t%1);bpy.context.view_layer.update()
def head(obj,t):
 frame(t);p=obj.matrix_world@Vector((0,-1.15,0));pelvis=rig.matrix_world@rig.pose.bones['pelvis'].head;p.x-=pelvis.x;p.y-=pelvis.y;return p
records=[]
for row in [6,6.5,7,7.5,8,8.5,9]:
 velocity=(head(new,row+.01)-head(new,row-.01))/.02;frame(row);shaft=(new.matrix_world.to_3x3()@Vector((0,1,0))).normalized();velocity-=shaft*velocity.dot(shaft)
 if velocity.length<1e-5:continue
 velocity.normalize();before=(old.matrix_world.to_3x3()@Vector((0,0,1))).normalized();after=(new.matrix_world.to_3x3()@Vector((0,0,1))).normalized();records.append({'row':row,'old_broad_face_alignment':abs(before.dot(velocity)),'new_broad_face_alignment':abs(after.dot(velocity))})
assert len(records)==7 and sum(r['new_broad_face_alignment'] for r in records)<sum(r['old_broad_face_alignment'] for r in records)/2 and max(r['new_broad_face_alignment'] for r in records)<.6,'Blade remains broadside to the cut'
(root/'edge-orientation-check.json').write_text(json.dumps({'metric':'0=edge-first, 1=broadside-first; perpendicular-to-haft head velocity','samples':records},indent=2));print(records,flush=True)
