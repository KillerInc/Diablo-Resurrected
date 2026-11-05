"""Blender --python SCRIPT -- STAFF_PLAN.json
Check every held staff grip, at the actual stored game frames.
"""
import bpy,json,sys,math,numpy as np
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
from preflight_equipped_sets import check
plan=json.loads(Path(sys.argv[sys.argv.index('--')+1]).read_text());records=[]
for j in plan['jobs']:
 if j['action'] in ['st','wl']:continue
 ref=json.loads(Path(j['reference']).read_text());check(j['model'],j['reference']);rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');staff=next(o for o in bpy.data.objects if o.get('d1r_equipment'));samples=[]
 for tick in range(ref['rows']):
  row=tick;bpy.context.scene.frame_set(int(row),subframe=row%1);bpy.context.view_layer.update();palm=rig.matrix_world@rig.pose.bones['hand.R'].matrix@Vector((.0425,.0825,-.002));left=rig.matrix_world@rig.pose.bones['hand.L'].matrix@Vector((0,.05,0));ev=staff.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh();points=np.array([list(ev.matrix_world@v.co) for v in mesh.vertices]);ev.to_mesh_clear();samples.append({'row':row,'right_grip_error':float(np.linalg.norm(points-np.array(palm),axis=1).min()),'left_shaft_distance':float(np.linalg.norm(points-np.array(left),axis=1).min())})
 records.append({'sheet':j['sheet'],'max_right_grip_error':max(r['right_grip_error'] for r in samples),'max_left_shaft_distance':max(r['left_shaft_distance'] for r in samples),'samples':samples})
result={'profiles':records,'measurement':'nearest mesh vertex to palm; includes shaft thickness','all_right_grips_valid':all(r['max_right_grip_error']<.08 for r in records)};(Path(plan['work'])/'staff-grip-check.json').write_text(json.dumps(result,indent=2));assert result['all_right_grips_valid'];print('All staff right-hand grips verified')
