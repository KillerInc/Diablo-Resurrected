"""Blender --python SCRIPT -- BOW_IDLE_PLAN.json
Check every idle pose: unchanged palm socket and bow clearance from body.
Intentional glove/grip contact is permitted; all other body intersections fail.
"""
import bpy,json,sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from paladin_equipment import attach_equipment
from preflight_equipped_sets import opaque
import hashlib
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()
file=Path(sys.argv[sys.argv.index('--')+1]);p=json.loads(file.read_text());reports=[]
def geometry(o):
 e=o.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();m.calc_loop_triangles();v=[e.matrix_world@a.co for a in m.vertices];t=[tuple(a.vertices) for a in m.loop_triangles];e.to_mesh_clear();return v,t
for j in p['jobs']:
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=j['model']);r=json.loads(Path(j['reference']).read_text());rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');equipment=attach_equipment(rig,[r['equipment'][0]]);parts=[o for o in bpy.data.objects if opaque(o) and o not in equipment and 'base01_GLV' not in o.data.materials[0].name];hits=[];errors=[]
 for row,time in enumerate(r['source_frames']):
  bpy.context.scene.frame_set(time);bpy.context.view_layer.update();grip=rig.matrix_world@rig.pose.bones['hand.L'].matrix@Vector((0,.05,0))
  errors.extend(((o.matrix_world@Vector())-grip).length for o in equipment)
  for o in equipment:
   v,t=geometry(o);tree=BVHTree.FromPolygons(v,t,all_triangles=True)
   for part in parts:
    bv,bt=geometry(part);contacts=tree.overlap(BVHTree.FromPolygons(bv,bt,all_triangles=True))
    if contacts:hits.append({'row':row,'bow':o.name,'body':part.name,'contacts':len(contacts)})
 reports.append({'sheet':j['sheet'],'rows':r['rows'],'bow_sha256':sha(r['equipment'][0]['path']),'body_sha256':sha(j['model']),'max_grip_error_metres':max(errors),'body_contacts':hits});(Path(p['work'])/'idle-hold-audit.json').write_text(json.dumps(reports,indent=2));print(j['sheet'],max(errors),hits,flush=True)
assert len(reports)==2 and all(r['max_grip_error_metres']<1e-5 and not r['body_contacts'] for r in reports)

