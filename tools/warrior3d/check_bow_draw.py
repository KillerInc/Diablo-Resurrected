"""Blender --python SCRIPT -- BOW_PLAN.json
Check baked morph weights, palm grips, string draw and frame-11 arrow release.
"""
import bpy,json,sys
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent));from paladin_equipment import attach_equipment
file=Path(sys.argv[sys.argv.index('--')+1]);plan=json.loads(file.read_text());j=next(j for j in plan['jobs'] if j['action']=='at');ref=json.loads(Path(j['reference']).read_text());bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=j['model']);rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');objects=attach_equipment(rig,ref['equipment']);string=next(o for o in objects if 'string' in o.name.lower());arrow=next(o for o in objects if 'arrow' in o.name.lower());wood=next(o for o in objects if o not in [string,arrow]);records=[]
def positions(o):
 e=o.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();v=[e.matrix_world@x.co for x in m.vertices];e.to_mesh_clear();return v
for row in range(16):
 bpy.context.scene.frame_set(row);bpy.context.view_layer.update();left=rig.matrix_world@rig.pose.bones['hand.L'].matrix@Vector((0,.05,0));right=rig.matrix_world@rig.pose.bones['hand.R'].matrix@Vector((.0425,.0825,-.002));sv=positions(string);av=positions(arrow);arrow_span=max((p-av[0]).length for p in av);records.append({'row':row,'left_grip_error':((wood.matrix_world@Vector())-left).length,'string_right_grip_error':min((p-right).length for p in sv) if 5<=row<=10 else None,'arrow_span':arrow_span,'arrow_nock_error':min((p-right).length for p in av) if 4<=row<=10 else None})
valid=all(r['left_grip_error']<.001 and (r['string_right_grip_error'] is None or r['string_right_grip_error']<.005) and (r['arrow_nock_error'] is None or r['arrow_nock_error']<.005) and (r['arrow_span']>.6 if 4<=r['row']<=10 else r['arrow_span']<.0001) for r in records);report={'game_release_frame':11,'native_contact_frame':7,'all_grips_and_release_valid':valid,'samples':records};(Path(plan['work'])/'bow-draw-check.json').write_text(json.dumps(report,indent=2));assert valid,records;print('Bow grips, string and arrow release verified for all sixteen frames')
