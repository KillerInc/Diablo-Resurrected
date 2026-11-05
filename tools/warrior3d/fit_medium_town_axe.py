import bpy,json,sys,copy
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent));from paladin_equipment import attach_equipment
planfile=Path(sys.argv[sys.argv.index('--')+1]).resolve();plan=json.loads(planfile.read_text());root=Path(plan['work']);job=next(j for j in plan['jobs'] if j['sheet']=='wmawl');ref=json.loads(Path(job['reference']).read_text());
if ref.get('medium_helmet_clearance'):
 print('Already fitted; audit the existing offset instead of accumulating another shift');raise SystemExit(0)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=job['model']);rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');gear=attach_equipment(rig,ref['equipment']);head=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.data.materials and any(t in o.data.materials[0].name for t in ('P00_HED','Helmet dark gray metal'))];original=[o.matrix_basis.copy() for o in gear]
def tree(o):
 ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();t=BVHTree.FromPolygons([ev.matrix_world@v.co for v in m.vertices],[tuple(p.vertices) for p in m.polygons]);ev.to_mesh_clear();return t
candidates=[]
for mm in range(2,102,2):
 for axis,sign in [(0,1),(0,-1),(2,-1),(2,1),(1,-1),(1,1)]:
  delta=Vector((0,0,0));delta[axis]=sign*mm/1000
  for o,matrix in zip(gear,original):o.matrix_basis=matrix.copy();o.matrix_basis.translation+=delta
  hits=0
  for row,frame in enumerate(ref['source_frames']):
   bpy.context.scene.frame_set(int(frame));bpy.context.view_layer.update();heads=[tree(o) for o in head]
   for o in gear:
    other=tree(o);hits+=sum(len(t.overlap(other)) for t in heads)
   if hits:break
  candidates.append({'delta_local_metres':list(delta),'clear':hits==0})
 if any(x['clear'] for x in candidates):break
assert any(x['clear'] for x in candidates),'No safe stowed-axe offset found; inspect rather than change a pose'
clear=next(x for x in candidates if x['clear']);delta=Vector(clear['delta_local_metres']);delta*=1+.002/delta.length
for name in ['wmast','wmawl']:
 p=root/'jobs'/name/'reference.json';r=json.loads(p.read_text());before=copy.deepcopy(r['equipment'][0]['local_transform'])
 for axis in range(3):r['equipment'][0]['local_transform'][axis][3]+=delta[axis]
 r['medium_helmet_clearance']={'chest_local_delta_metres':list(delta),'original_transform':before,'body_animation_changed':False};p.write_text(json.dumps(r,indent=2))
(root/'town-axe-helmet-fit.json').write_text(json.dumps({'candidates':candidates,'selected_delta_metres':list(delta),'safety_margin_metres':.002,'sheets':['wmast','wmawl'],'body_pose_and_weapon_rotation_preserved':True},indent=2));print('TOWN_AXE_CLEARANCE',list(delta))
