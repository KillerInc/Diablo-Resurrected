"""Repair local Tripo Warrior segmentation weights. No source artwork is embedded in this script.
Run Blender --background --factory-startup --python this.py -- --input model.glb --out private-output
"""
import argparse,json,math,sys
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector,Matrix,Quaternion
p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(a.input.resolve()))
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
meshes=[o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith('tripo_part_')]
assert len(meshes)==39, 'This mapping requires the inspected 39-piece Warrior export'
for o in list(bpy.data.objects):
 if o.type=='MESH' and o not in meshes: bpy.data.objects.remove(o,do_unlink=True)
rig.animation_data_clear()
for b in rig.pose.bones:b.matrix_basis.identity()
rig.data.pose_position='POSE';bpy.context.view_layer.update()
sys.path.insert(0,str(Path(__file__).resolve().parent))
from pauldron_control import add_control,set_control,clear_body,NAME
add_control(rig)
from knee_control import add_knees,bend,plate_weights
add_knees(rig)
collision_results=[];repair_active=False
# Rigid equipment must not interpolate between unrelated bones.
rigid={0:'Spine02',3:'Waist',4:'Pelvis',5:'Head',7:'R_Calf',8:'L_Upperarm',9:'L_Foot',
10:'L_Calf',11:'R_Foot',12:NAME,13:'L_Calf',14:'R_Thigh',15:'R_Hand',16:'Spine02',
17:'L_Hand',19:'R_Thigh',20:'Pelvis',21:'Head',23:'Pelvis',27:'L_Foot',28:'R_Foot',
30:'R_Hand',31:'L_Thigh',32:'L_Hand',33:'R_Calf',34:'R_Hand',35:'Head',36:'L_Hand',37:'R_Upperarm',38:'Head'}
soft={1:['Pelvis','L_Thigh','R_Thigh'],2:['Waist','Spine01','Spine02'],
6:['R_Upperarm','R_Forearm'],18:['Spine02','NeckTwist01','NeckTwist02','Head'],
22:['R_Thigh','R_Calf'],24:['L_Calf','L_Foot'],25:['R_Calf','R_Foot'],
26:['L_Forearm','L_Hand'],29:['L_Thigh','L_Calf']}
assert set(rigid)|set(soft)==set(range(39))
report={'status':'candidate; visual review required','rig_strategy':'retain imported joint locations; restrict skin weights by inspected part; rigid equipment binding','parts':[], 'original_assets_in_git':False}
original={o.name:[[(o.vertex_groups[g.group].name,g.weight) for g in v.groups] for v in o.data.vertices] for o in meshes}
# Build controlled shoulder test using armature-space pivots; preserve imported rest geometry.
from pose_test import apply_test_pose
def pose(amount):
 apply_test_pose(rig,amount,repair_active,globals().get('bridges',()),collision_results)

def edge_positions():
 deps=bpy.context.evaluated_depsgraph_get();result={}
 for o in meshes:
  ev=o.evaluated_get(deps);me=ev.to_mesh();co=np.array([tuple(v.co) for v in me.vertices]);e=np.array([tuple(edge.vertices) for edge in me.edges]);result[o.name]=np.linalg.norm(co[e[:,0]]-co[e[:,1]],axis=1);ev.to_mesh_clear()
 return result
pose(0);baseline=edge_positions()
def distortion():
 now=edge_positions();ratios=np.concatenate([now[n]/np.maximum(baseline[n],1e-8) for n in now]);return {'p99_edge_stretch':float(np.percentile(ratios,99)),'maximum_edge_stretch':float(ratios.max()),'edges_stretched_over_3x':int((ratios>3).sum()),'maximum_by_part':{n:float((now[n]/np.maximum(baseline[n],1e-8)).max()) for n in now if (now[n]/np.maximum(baseline[n],1e-8)).max()>2}}
scene=bpy.context.scene;scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=768;scene.render.resolution_y=768;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.film_transparent=True;scene.world.color=(.12,.12,.12)
up=(rig.matrix_world.to_3x3()@Vector((0,0,1))).normalized();front=(rig.matrix_world.to_3x3()@Vector((0,-1,0))).normalized();center=rig.matrix_world@Vector((.015,-.02,.51))
bpy.ops.object.camera_add();cam=bpy.context.object;cam.data.type='ORTHO';cam.data.ortho_scale=1.28;scene.camera=cam;cam.location=center+front*3+up*.35
back=(cam.location-center).normalized();right=up.cross(back).normalized();vertical=back.cross(right);cam.rotation_euler=Matrix((right,vertical,back)).transposed().to_euler()
for pos,energy in [(( -2,-3,3),100),((2,0,2),65)]:
 bpy.ops.object.light_add(type='AREA',location=rig.matrix_world@Vector(pos));light=bpy.context.object;light.data.energy=energy;light.data.size=2;light.rotation_euler=(center-light.location).to_track_quat('-Z','Y').to_euler()
def render(name):scene.render.filepath=str(a.out/(name+'.png'));bpy.ops.render.render(write_still=True)
pose(1);report['original_shoulder_test']=distortion();render('before-arm-test');pose(0)
for o in meshes:
 index=int(o.name.rsplit('_',1)[1]);allowed=[rigid[index]] if index in rigid else soft[index]
 assert all(name in rig.data.bones for name in allowed)
 for g in list(o.vertex_groups):o.vertex_groups.remove(g)
 groups={n:o.vertex_groups.new(name=n) for n in allowed};removed=0
 for v,old in zip(o.data.vertices,original[o.name]):
  weights={n:w for n,w in old if n in allowed};removed+=sum(w for n,w in old if n not in allowed)>.001
  if index in rigid:weights={allowed[0]:1}
  total=sum(weights.values())
  if total<1e-6:
   point=rig.matrix_world.inverted()@o.matrix_world@v.co
   nearest=min(allowed,key=lambda n:(rig.data.bones[n].head_local-point).length)
   weights={nearest:1};total=1
  for n,w in weights.items():
   if w>0:groups[n].add([v.index],w/total,'REPLACE')
 o['repair_binding']='rigid' if index in rigid else 'restricted skin';o['repair_allowed_bones']=','.join(allowed)
 report['parts'].append({'part':index,'bones':allowed,'vertices_with_removed_influences':removed})
sys.path.insert(0,str(Path(__file__).resolve().parent))
from underarm_surface import connect_underarms,endpoint_error
plate_weights(rig)
bridges,report['underarm_bridges']=connect_underarms(rig)
from hidden_surfaces import fill_hidden_surfaces
hidden_surfaces=fill_hidden_surfaces(rig)
report['reconstructed_hidden_surfaces']=[o.name for o in hidden_surfaces]
repair_active=True
pose(1);report['repaired_shoulder_test']=distortion();render('after-arm-test')
pose(0);render('repaired-rest')
# Keep equipment in the file, with an explicit reversible unarmed collection.
gear=bpy.data.collections.new('Optional sword and back shield');scene.collection.children.link(gear)
for index in (0,4,30,34):
 o=bpy.data.objects[f'tripo_part_{index}'];gear.objects.link(o)
 for collection in list(o.users_collection):
  if collection!=gear:collection.objects.unlink(o)
 o.hide_render=True; o.hide_set(True)
report['unarmed_hidden_parts']=[0,4,30,34]
render('unarmed-rest')
# Save a neutral editable candidate before rendering diagnostic motion.
rig['repair_status']='Weight-repair candidate; imported joint positions retained; not production approved'
bpy.ops.wm.save_as_mainfile(filepath=str(a.out/'Warrior-weight-repair.blend'),compress=True)
bpy.ops.object.select_all(action='DESELECT')
for o in meshes+bridges+hidden_surfaces+[rig]:o.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.gltf(filepath=str(a.out/'Warrior-weight-repair.glb'),export_format='GLB',use_selection=True,export_animations=False)
for frame in range(16):
 pose(.5-.5*math.cos(2*math.pi*frame/16))
 error=endpoint_error(rig,bridges);assert error<1e-5,('Detached underarm',error)
 report['maximum_underarm_endpoint_error']=max(error,report.get('maximum_underarm_endpoint_error',0))
 render(f'arm-check-{frame:02}')
pose(0)
report['pauldron_clearance']=collision_results
(a.out/'repair-report.json').write_text(json.dumps(report,indent=2));print('REPAIR_REPORT',json.dumps({k:v for k,v in report.items() if k!='parts'}),flush=True)
