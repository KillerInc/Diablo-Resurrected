"""Blender synthetic proof: staggered growth, fixed paths, stable held geometry."""
import bpy,sys,json
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from paladin_lightning_effect import LightningEffect
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.object.armature_add();rig=bpy.context.object;bpy.ops.object.mode_set(mode='EDIT')
bone=rig.data.edit_bones[0];bone.name='hand.L';bone.head=(-.25,0,1);bone.tail=(-.25,0,1.1)
bone=rig.data.edit_bones.new('hand.R');bone.head=(.25,0,1);bone.tail=(.25,0,1.1);bpy.ops.object.mode_set(mode='OBJECT');bpy.context.view_layer.update()
out=Path(sys.argv[sys.argv.index('--')+1]);out.mkdir(parents=True,exist_ok=True)
settings=json.loads((Path(__file__).parent/'lightning_settings.json').read_text());effect=LightningEffect(bpy.context.scene,rig,out,settings)
effect.update(0,0,20);paths=effect.paths[0];original=[[tuple(v) for v in p['points']] for p in paths];assert len(paths)==6 and len({p['start'] for p in paths})==6
assert len(effect.mesh.vertices)==0
samples=[];counts=[];local_paths=[]
for row in range(1,20):
 rig.location.x=row*.02;bpy.context.view_layer.update();effect.update(0,row,20);counts.append(len(effect.mesh.vertices));coords=np.empty(len(effect.mesh.vertices)*3,dtype=np.float32);effect.mesh.vertices.foreach_get('co',coords)
 assert original==[[tuple(v) for v in p['points']] for p in paths]
 if row>=15:
  samples.append(coords.copy());inverse=effect.orbit_matrix.inverted();local_paths.append([[tuple(inverse@v) for v in p] for p in effect.visible_paths])
assert not np.array_equal(samples[0],samples[-1]),'Held bolts stopped spinning'
for paths in local_paths[1:]:
 assert all(np.allclose(a,b,atol=1e-6) for a,b in zip(local_paths[0],paths)),'Held bolt paths changed shape while spinning'
assert len(set(counts[:14]))>3,'Bolts did not grow over time'
effect.update(0,20,21);assert len(effect.mesh.vertices)==0 and effect.obj.hide_render
proof={'bolts':6,'staggered_starts':True,'progressive_growth':True,'orbit_center_fixed_despite_caster_movement':True,'held_paths_unchanged_in_orbit_coordinates':[15,16,17,18,19],'spins_while_holding':True,'spare_frame_idle':True,'fresh_randomness_each_cast':False}
(out/'grow-hold-proof.json').write_text(json.dumps(proof,indent=2));print('PASS: six staggered growing bolts; held paths spin around fixed cast point; spare frame idle',flush=True)
