"""Fit a private shield revision across source poses using surface intersections.
No mesh or animation data is embedded. Run the equipment audit before and after.
"""
import bpy,json,sys,math,argparse
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from paladin_equipment import attach_equipment
parser=argparse.ArgumentParser(description='Fit shield-only helmet clearance; preserve character animation and approved idle fit.');parser.add_argument('plan',type=Path);args=parser.parse_args(sys.argv[sys.argv.index('--')+1:]);root=args.plan.resolve().parent;plan=json.loads(args.plan.read_text());audit=json.loads((root/'all-equipment-head-audit.json').read_text());bad={r['sheet'] for r in audit if r['head_contacts']};results=json.loads((root/'shield-pose-clearance.json').read_text()) if (root/'shield-pose-clearance.json').exists() else []
for job in plan['jobs']:
 if job['sheet'] not in bad:continue
 if any(e.get('pose_clearance') for e in json.loads(Path(job['reference']).read_text()).get('equipment',[])):continue
 ref=json.loads(Path(job['reference']).read_text());bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=job['model']);rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');gear=attach_equipment(rig,ref['equipment']);shield=next(o for o in gear if o.get('d1r_asset')=='shield_Medium.glb');item=next(e for e in ref['equipment'] if 'shield_Medium' in e['path']);bone=item['bone'];base=Matrix(item['local_transform']);vertices=[v.co.copy() for v in shield.data.vertices];faces=[tuple(p.vertices) for p in shield.data.polygons];heads=[o for o in bpy.context.scene.objects if o.type=='MESH' and any(s.material and any(t in s.material.name for t in ['P00_HED','Helmet dark gray metal']) for s in o.material_slots)];cache=[]
 for frame in ref['source_frames']:
  bpy.context.scene.frame_set(frame);bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get();trees=[]
  for o in heads:
   ev=o.evaluated_get(deps);mesh=ev.to_mesh();trees.append(BVHTree.FromPolygons([ev.matrix_world@v.co for v in mesh.vertices],[tuple(p.vertices) for p in mesh.polygons]));ev.to_mesh_clear()
  cache.append((rig.matrix_world@rig.pose.bones[bone].matrix,trees))
 bpy.context.scene.frame_set(ref['source_frames'][0]);bpy.context.view_layer.update();pivot=rig.pose.bones[bone].matrix.inverted()@rig.pose.bones['hand.L'].head;normal=base.to_3x3().col[2].normalized();chosen=None
 for distance in (0,.03,.06,.10,.15,.20,.25):
  for axis,degrees in [('Y',v) for v in (0,-15,-30,-45,-60,15,30,45,60)]+[(axis,v) for axis in ('X','Z') for v in (-15,15,-30,30,-45,45,-60,60)]:
   transform=Matrix.Translation(normal*distance)@Matrix.Translation(pivot)@Matrix.Rotation(math.radians(degrees),4,axis)@Matrix.Translation(-pivot)@base
   okay=True
   for boneworld,trees in cache:
    world=boneworld@transform;tree=BVHTree.FromPolygons([world@v for v in vertices],faces)
    if any(tree.overlap(head) for head in trees):okay=False;break
   if okay:chosen=(degrees,distance,transform,axis);break
  if chosen:break
 if not chosen:raise RuntimeError('Cannot clear helmet '+job['sheet'])
 degrees,distance,transform,axis=chosen;item['local_transform']=[list(row) for row in transform];item['pose_clearance']={'rotation_degrees':degrees,'rotation_axis':axis,'normal_offset_m':distance,'arm_motion_unchanged':True,'all_source_frames_checked':len(cache)};Path(job['reference']).write_text(json.dumps(ref,indent=2))
 folder=Path(job['root']);previous=folder/'before-pose-clearance';previous.mkdir(exist_ok=True)
 for name in ('frames','shadows','output'):
  if (folder/name).exists():(folder/name).rename(previous/name)
 results.append({'sheet':job['sheet'],**item['pose_clearance']});(root/'shield-pose-clearance.json').write_text(json.dumps(results,indent=2));print('SHIELD_CLEARED',job['sheet'],degrees,distance,flush=True)
