"""Blender --python SCRIPT -- QUIVER_FIT_PLAN.json
Render a side-profile before/after inspection of the closer quiver mount.
"""
import bpy,sys,json
from pathlib import Path
from mathutils import Vector,Matrix
sys.path.insert(0,str(Path(__file__).resolve().parent))
from paladin_equipment import attach_equipment
p=json.loads(Path(sys.argv[sys.argv.index('--')+1]).read_text());out=Path(p['work'])/'quiver-preview';out.mkdir(exist_ok=True);j=next(j for j in p['jobs'] if j['sheet']=='wlbst');r=json.loads(Path(j['reference']).read_text());bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=j['model']);rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');objects=attach_equipment(rig,r['equipment']);q=next(o for o in objects if o.get('d1r_asset')==Path(next(e for e in r['equipment'] if e.get('town_role')=='back_quiver')['path']).name);basis=q.matrix_basis.copy();scene.frame_set(0);bpy.context.view_layer.update();target=rig.matrix_world@rig.pose.bones['chest'].head;target+=Vector((0,.10,.05));scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=720;scene.render.resolution_y=900;scene.render.resolution_percentage=100;scene.world=bpy.data.worlds.new('World');scene.world.color=(.08,.08,.08)
for pos,power,size in [((3,-4,6),400,4),((-3,-1,3),140,3),((0,3,4),110,3)]:
 bpy.ops.object.light_add(type='AREA',location=pos);o=bpy.context.object;o.data.energy=power;o.data.size=size;o.rotation_euler=(target-o.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=target+Vector((3,0,.55)));cam=bpy.context.object;cam.data.type='ORTHO';cam.data.ortho_scale=1.08;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();scene.camera=cam
original_basis=basis.copy()
if p['quiver_fit'].get('contour'):
 prior=json.loads((Path(p['work'])/'translation-only-plan.json').read_text());before=json.loads((Path(p['work'])/'translation-only-references/wlbst.json').read_text());spec=next(e for e in before['equipment'] if e.get('town_role')=='back_quiver');M=Matrix(spec['local_transform']);original_basis=Matrix.Translation((0,-rig.data.bones['chest'].length,0))@M;original_basis.translation+=M.to_3x3()@Vector((0,prior['quiver_fit']['selected_inward_metres']/.8,0))
else:original_basis.translation+=basis.to_3x3()@Vector((0,p['quiver_fit']['selected_inward_metres']/.8,0))
for label,B in [('before',original_basis),('after',basis)]:
 q.matrix_basis=B.copy();bpy.context.view_layer.update();scene.render.filepath=str(out/(label+'.png'));bpy.ops.render.render(write_still=True)
