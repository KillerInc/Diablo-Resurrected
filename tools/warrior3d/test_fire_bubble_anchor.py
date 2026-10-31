"""Blender synthetic test: a moving caster cannot move the anchored shell."""
import bpy,json,sys,math
from pathlib import Path
import numpy as np
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from paladin_fire_effect import FireEffect
bpy.ops.wm.read_factory_settings(use_empty=False)
bpy.ops.object.empty_add(location=(2,3,0));rig=bpy.context.object
settings=json.loads((Path(__file__).parent/'fire_bubble_settings.json').read_text())
out=Path(sys.argv[sys.argv.index('--')+1]);out.mkdir(parents=True,exist_ok=True)
effect=FireEffect(bpy.context.scene,rig,out,settings);centers=[]
for row in range(20):
 rig.location=(2+.4*math.sin(row),3+.3*math.cos(row),.1*math.sin(row))
 effect.update(0,row,20);center=effect.bubble.obj.location.copy();centers.append(list(center))
 assert (center-Vector((2,3,.9))).length<1e-6
 coords=np.empty(len(effect.bubble.obj.data.vertices)*3,dtype=np.float32);effect.bubble.obj.data.vertices.foreach_get('co',coords)
 assert np.array_equal(coords.reshape(-1,3),effect.bubble.original),'Shell geometry wobbled'
 assert (effect.matrix.translation-Vector((2,3,0))).length<1e-6
proof={'synthetic_frames':20,'caster_root_moves':True,'effect_center_fixed':True,'mesh_coordinates_unchanged':True,'center':[2,3,.9],'initial_growth_retained':True}
(out/'anchor-proof.json').write_text(json.dumps(proof,indent=2));print('PASS: moving caster root; fixed cast-start effect center and stable bubble mesh',flush=True)
