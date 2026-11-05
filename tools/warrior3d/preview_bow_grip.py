"""Blender --python SCRIPT -- CLOSED_GRIP_PLAN.json
Render front, inside and overhead hand close-ups for both idle poses.
"""
import bpy,sys,json,math
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent));from paladin_equipment import attach_equipment
file=Path(sys.argv[sys.argv.index('--')+1]);w=file.resolve().parent;p=json.loads(file.read_text());assert p['bow_grip_revision'];out=w/'closeups';out.mkdir(exist_ok=True)
for j in p['jobs']:
 bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=j['model']);rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');ref=json.loads(Path(j['reference']).read_text());attach_equipment(rig,ref['equipment']);scene.frame_set(0);bpy.context.view_layer.update();grip=rig.matrix_world@rig.pose.bones['hand.L'].matrix@Vector((-.04,.065,0));scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=700;scene.render.resolution_y=700;scene.render.resolution_percentage=100;scene.world=bpy.data.worlds.new('World');scene.world.color=(.08,.08,.08)
 for pos,power,size in [((3,-4,6),400,4),((-3,-1,3),140,3),((0,3,4),110,3)]:
  bpy.ops.object.light_add(type='AREA',location=pos);l=bpy.context.object;l.data.energy=power;l.data.size=size;l.rotation_euler=(Vector((0,0,.9))-l.location).to_track_quat('-Z','Y').to_euler()
 bpy.ops.object.camera_add();cam=bpy.context.object;cam.data.type='ORTHO';cam.data.clip_start=.001;scene.camera=cam
 for i,off in enumerate([(0.5,-.5,.35),(-.5,.4,.3),(0,-.1,.7)]):
  cam.data.ortho_scale=.34;cam.location=grip+Vector(off);cam.rotation_euler=(grip-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(out/(j['sheet']+'-grip-'+str(i)+'.png'));bpy.ops.render.render(write_still=True)
 cam.data.ortho_scale=2.5;target=Vector((0,0,.9));cam.location=(0,-6,.9+6*math.tan(math.radians(30)));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(out/(j['sheet']+'-body.png'));bpy.ops.render.render(write_still=True)
