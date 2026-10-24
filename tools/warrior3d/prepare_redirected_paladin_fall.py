"""Choose the smallest foot-anchored fall redirection fitting each original cell.

Blender --python SCRIPT -- MODEL.glb REFERENCE.json OUTPUT.json CALIBRATION.json
Uses the existing 30-degree camera and southeast sun. Checks all twenty source
poses, eight views, full opaque geometry and projected shadows. Requires 18 NN8
pixels of geometric clearance and less than 0.01 mm of stance midpoint error. No
horizontal actor offsets, image offsets, model scaling, or artwork are stored.
"""
import bpy,sys,json,math,numpy as np
from pathlib import Path
source,reference,destination,calibration=map(Path,sys.argv[sys.argv.index('--')+1:]);sys.path.insert(0,str(Path(__file__).resolve().parent));scale=json.loads(calibration.read_text())['global_pixel_scale']
from redirect_paladin_fall import RedirectFall
bpy.context.scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=str(source.resolve()))
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');rig.rotation_mode='XYZ'
parts=[o for o in bpy.data.objects if o.type=='MESH' and o.data.materials and any(t in o.data.materials[0].name for t in ['base16_TRS','armor_skin','P00_HED','base01_GLV','base01_LEG','base05_BTS'])]
def points():
 result=[]
 for o in parts:
  ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();v=np.empty(len(me.vertices)*3,dtype=np.float32);me.vertices.foreach_get('co',v);m=np.array(ev.matrix_world);result.append(v.reshape(-1,3)@m[:3,:3].T+m[:3,3]);ev.to_mesh_clear()
 return np.concatenate(result)
ref=json.loads(reference.read_text());assert ref['cell']==1024 and ref['cell_height']==768 and ref['rows']==20;times=ref['source_frames'];redirect=RedirectFall(rig,times[0]);floor=float(points()[:,2].min());scores=[];offsets=[];errors=[]
for a in range(16):
 angle=a*math.pi/8;poses=[];zoffsets=[];anchor_errors=[]
 for frame in times:
  rig.location=(0,0,0);rig.rotation_euler=(0,0,0);err=redirect.apply(frame,angle);p=points();z=floor-float(p[:,2].min());p[:,2]+=z;poses.append(p);zoffsets.append([0,0,z]);anchor_errors.append(err)
 margins=[]
 for d in range(8):
  theta=-d*math.pi/4;c,s=math.cos(theta),math.sin(theta);rot=np.array([[c,-s,0],[s,c,0],[0,0,1]]);margin=1e9
  for p in poses:
   q=p@rot.T
   for kind in ['body','shadow']:
    v=q.copy()
    if kind=='shadow':h=np.maximum(v[:,2],0);v[:,0]-=.5*h;v[:,1]+=4/6*h;v[:,2]=.002
    x=512+v[:,0]*(768/2.75)*scale;y=640-(.5*v[:,1]+math.cos(math.pi/6)*v[:,2])*(768/2.75)*scale
    margin=min(margin,float(x.min()),float(y.min()),1024-float(x.max()),768-float(y.max()))
  margins.append(margin)
 scores.append(margins);offsets.append(zoffsets);errors.append(max(anchor_errors));print('ANGLE',a,'MARGINS',margins,'ANCHOR ERROR',max(anchor_errors),flush=True)
best=[]
for d in range(8):
 candidates=[a for a in range(16) if scores[a][d]>18 and errors[a]<1e-5]
 assert candidates,('No anchored solution',d)
 best.append(min(candidates,key=lambda a:(min(a,16-a),-scores[a][d])))
ref['redirect_fall']={'angles':[a*math.pi/8 for a in best],'first_frame':times[0]};ref['direction_pose_offsets']=[offsets[a] for a in best];ref['pose_offsets']=[];ref['pose_image_offsets']=[]
ref['shadow_overscan']=512;destination.parent.mkdir(parents=True,exist_ok=True);destination.write_text(json.dumps(ref,indent=2));destination.with_suffix('.audit.json').write_text(json.dumps({'angles_indices':best,'all_margins':scores,'minimum_margin':[scores[a][d] for d,a in enumerate(best)],'maximum_stance_midpoint_error':[errors[a] for a in best],'root_motion_anchors_stance_midpoint':True,'no_image_translation':True,'native_joint_angles_preserved':True},indent=2));print('BEST',best,flush=True)
