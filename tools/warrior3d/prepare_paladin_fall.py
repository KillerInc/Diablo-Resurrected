"""Prepare floor contact and a smooth fixed-endpoint settling path for a fall.

Blender --python SCRIPT -- MODEL.glb REFERENCE.json OUTPUT_REFERENCE.json
No geometry or bone animation is changed. The body/shadow render share the same
pose offsets. Final footprint center is fixed, not recomputed for each view.
"""
import bpy,json,sys
from pathlib import Path
import numpy as np

source,reference,destination=map(Path,sys.argv[sys.argv.index('--')+1:])
bpy.context.scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=str(source.resolve()))
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');ref=json.loads(reference.read_text())
parts=[o for o in bpy.data.objects if o.type=='MESH' and o.data.materials and any(
    t in o.data.materials[0].name for t in ['base16_TRS','armor_skin','P00_HED','base01_GLV','base01_LEG','base05_BTS'])]
assert len(parts)==6
poses=[]
for frame in ref['source_frames']:
    bpy.context.scene.frame_set(frame);bpy.context.view_layer.update();points=[]
    for o in parts:
        ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh()
        vertices=np.empty(len(mesh.vertices)*3,dtype=np.float32);mesh.vertices.foreach_get('co',vertices);vertices=vertices.reshape(-1,3)
        transform=np.array(ev.matrix_world);points.append(vertices@transform[:3,:3].T+transform[:3,3]);ev.to_mesh_clear()
    points=np.concatenate(points);poses.append((points,np.array(rig.matrix_world@rig.pose.bones['pelvis'].head)))
floor=float(poses[0][0][:,2].min());center=((poses[-1][0].min(0)+poses[-1][0].max(0))/2)[:2]
offsets=[];image_offsets=[]
for points,hip in poses:
    drop=(poses[0][1][2]-hip[2])/(poses[0][1][2]-poses[-1][1][2])
    blend=float(np.clip((drop-.25)/.75,0,1));blend=blend*blend*(3-2*blend)
    offsets.append([-float(center[0])*blend,-float(center[1])*blend,floor-float(points[:,2].min())])
    # Two logical pixels of gradual upward settling leave blur room in the
    # original 128x96 cell. Identical placement in every facing; no scaling.
    image_offsets.append([0,-16*blend])
ref.update(pose_offsets=offsets,pose_image_offsets=image_offsets)
destination.write_text(json.dumps(ref,indent=2))
destination.with_suffix('.grounding.json').write_text(json.dumps({
    'floor_z':floor,'final_footprint_center':center.tolist(),'pose_offsets':offsets,
    'pose_image_offsets':image_offsets,'mesh_and_joint_animation_unchanged':True,
    'constant_corpse_endpoint_for_all_directions':True,
},indent=2))
print('Prepared floor contact, fixed corpse endpoint and two-pixel settling clearance')
