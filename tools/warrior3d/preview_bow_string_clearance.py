"""Blender --python SCRIPT -- NEAR_ARM_BOW_PLAN.json
Render both full idle cycles with a fixed camera close to the glove/string.
"""
import bpy,sys,json,math
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent));from paladin_equipment import attach_equipment
file=Path(sys.argv[sys.argv.index('--')+1]);p=json.loads(file.read_text());out=Path(p['work'])/'closeups/animated';out.mkdir(parents=True,exist_ok=True)
for j in p['jobs']:
 bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=j['model']);rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');r=json.loads(Path(j['reference']).read_text());attach_equipment(rig,r['equipment']);scene.frame_set(0);bpy.context.view_layer.update();P=rig.matrix_world@rig.pose.bones['hand.L'].matrix@Vector((-.04,.065,0));scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=512;scene.render.resolution_y=512;scene.render.resolution_percentage=100;scene.world=bpy.data.worlds.new('World');scene.world.color=(.08,.08,.08)
 for pos,power,size in [((3,-4,6),400,4),((-3,-1,3),140,3),((0,3,4),110,3)]:
  bpy.ops.object.light_add(type='AREA',location=pos);o=bpy.context.object;o.data.energy=power;o.data.size=size;o.rotation_euler=(Vector((0,0,.9))-o.location).to_track_quat('-Z','Y').to_euler()
 bpy.ops.object.camera_add(location=P+Vector((0,-.1,.7)));cam=bpy.context.object;cam.data.type='ORTHO';cam.data.ortho_scale=.34;cam.rotation_euler=(P-cam.location).to_track_quat('-Z','Y').to_euler();scene.camera=cam
 for row,f in enumerate(r['source_frames']):
  scene.frame_set(f);bpy.context.view_layer.update();scene.render.filepath=str(out/(j['sheet']+'-'+str(row)+'.png'));bpy.ops.render.render(write_still=True)
