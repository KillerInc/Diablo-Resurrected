"""Refine N/NW death steering while preserving all other facing metadata.

Blender --python SCRIPT -- MODEL.glb CURRENT_REFERENCE.json OUTPUT.json CALIBRATION.json
Uses the head-to-stance body axis to preserve a lying endpoint and native joint
poses. Candidate selection checks full opaque body and southeast shadows.
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

ref=json.loads(reference.read_text());assert ref['sheet']=='wlndt.png' and ref['cell']==1024 and ref['cell_height']==768 and ref['rows']==20;assert len(parts)==6;times=ref['source_frames'];redirect=RedirectFall(rig,times[0]);floor=float(points()[:,2].min());scores=[];offsets=[];heights=[];errors=[]
for a in range(16):
 poses=[];zs=[];anchor=[]
 for frame in times:
  rig.location=(0,0,0);rig.rotation_euler=(0,0,0);anchor.append(redirect.apply(frame,a*math.pi/8,'body_axis'));p=points();z=floor-float(p[:,2].min());p[:,2]+=z;poses.append(p);zs.append([0,0,z])
 height=float(poses[-1][:,2].max()-poses[-1][:,2].min());margins=[]
 for d in [3,4]:
  theta=-d*math.pi/4;c,s=math.cos(theta),math.sin(theta);rot=np.array([[c,-s,0],[s,c,0],[0,0,1]]);margin=1e9
  for p in poses:
   q=p@rot.T
   for kind in ['body','shadow']:
    v=q.copy()
    if kind=='shadow':h=np.maximum(v[:,2],0);v[:,0]-=.5*h;v[:,1]+=4/6*h;v[:,2]=.002
    x=512+v[:,0]*(768/2.75)*scale;y=640-(.5*v[:,1]+math.cos(math.pi/6)*v[:,2])*(768/2.75)*scale
    margin=min(margin,float(x.min()),float(y.min()),1024-float(x.max()),768-float(y.max()))
  margins.append(margin)
 scores.append(margins);offsets.append(zs);heights.append(height);errors.append(max(anchor));print('CANDIDATE',a,margins,'rest height',height,flush=True)
selected=[]
ref['redirect_fall']['modes']=ref['redirect_fall'].get('modes',['pelvis']*8)
for col,d in enumerate([3,4]):
 candidates=[a for a in range(16) if scores[a][col]>18 and heights[a]<.60 and errors[a]<1e-5]
 assert candidates,('No lying solution',d)
 a=min(candidates,key=lambda a:(min(a,16-a),-scores[a][col]));selected.append(a)
 ref['redirect_fall']['angles'][d]=a*math.pi/8;ref['redirect_fall']['modes'][d]='body_axis';ref['direction_pose_offsets'][d]=offsets[a]
ref['render_directions']=[3,4];destination.parent.mkdir(parents=True,exist_ok=True);destination.write_text(json.dumps(ref,indent=2));destination.with_suffix('.audit.json').write_text(json.dumps({'refined_directions':[3,4],'selected_angle_indices':selected,'all_margins':scores,'final_heights':heights,'anchor_errors':errors,'other_facing_metadata_preserved':True},indent=2));print('SELECTED',selected,flush=True)
