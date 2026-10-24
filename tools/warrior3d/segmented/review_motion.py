"""Load repair .blend and render front/side/back exercise; bake a review action."""
import bpy,math,sys,json
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
sys.path.insert(0,str(Path(__file__).resolve().parent))
from pose_test import apply_test_pose
from underarm_surface import endpoint_error
out=Path(sys.argv[sys.argv.index('--')+1]).resolve();out.mkdir(parents=True,exist_ok=True)
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');bridges=[o for o in bpy.data.objects if o.name.endswith('rounded underarm')]
scene=bpy.context.scene;camera=scene.camera;scene.render.resolution_x=512;scene.render.resolution_y=512
up=(rig.matrix_world.to_3x3()@Vector((0,0,1))).normalized();front=(rig.matrix_world.to_3x3()@Vector((0,-1,0))).normalized();center=rig.matrix_world@Vector((.015,-.02,.51))
bpy.ops.object.light_add(type='AREA',location=rig.matrix_world@Vector((0,2,2)))
fill=bpy.context.object;fill.data.energy=75;fill.data.size=3;fill.rotation_euler=(center-fill.location).to_track_quat('-Z','Y').to_euler()
results=[];rig.animation_data_create();action=bpy.data.actions.new('Refinement_joint_range_review');rig.animation_data.action=action
for bone in rig.pose.bones:bone.rotation_mode='QUATERNION'
for frame in range(17):
    scene.frame_set(frame+1);amount=.5-.5*math.cos(2*math.pi*frame/16)
    checks=[];apply_test_pose(rig,amount,True,bridges,checks);error=endpoint_error(rig,bridges);assert error<1e-5
    for bone in rig.pose.bones:
        for path in ('location','rotation_quaternion','scale'):bone.keyframe_insert(data_path=path,frame=frame+1,group=bone.name)
    results.append({'frame':frame+1,'endpoint_error':error,'pauldron':checks[0]})
    if frame==16:continue
    for view,angle in [('front',0),('side',90),('back',180)]:
        direction=Quaternion(up,math.radians(angle))@front;camera.location=center+direction*3+up*.35
        back=(camera.location-center).normalized();right=up.cross(back).normalized();vertical=back.cross(right);camera.rotation_euler=Matrix((right,vertical,back)).transposed().to_euler()
        scene.render.filepath=str(out/f'{view}-{frame:02}.png');bpy.ops.render.render(write_still=True)
scene.frame_start=1;scene.frame_end=17;scene.render.fps=10;scene.frame_set(1)
# Check loop endpoint matrices after animation evaluation, not just pose input.
a=[]
for frame in (1,17):
    scene.frame_set(frame);a.append([v for b in rig.pose.bones for row in b.matrix for v in row])
loop=max(abs(x-y) for x,y in zip(*a));assert loop<1e-5
(out/'multi-view-validation.json').write_text(json.dumps({'poses':results,'loop_matrix_error':loop,'status':'range exercise; not a walking cycle'},indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(out/'Warrior-refinement-review.blend'),compress=True)
print('MULTIVIEW_DONE',len(results),loop,flush=True)
