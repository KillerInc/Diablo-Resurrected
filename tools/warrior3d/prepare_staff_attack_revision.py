"""Blender --python SCRIPT -- EXISTING_STAFF_PLAN.json NEW_WORK
Prepare the selected Sorcerer staff melee as an attack-only revision.
Copyrighted input and generated assets stay outside Git.
"""
import copy,json,sys
from pathlib import Path
from mathutils import Matrix
TOOLS=Path(__file__).resolve().parent
sys.path.insert(0,str(TOOLS))
from retarget_paladin_kick import main as retarget
from author_equipped_motion import author
from bake_staff_native_attack import bake

def prepare(old_file,work):
 old=json.loads(Path(old_file).read_text());work=Path(work).resolve();assert not work.exists();work.mkdir(parents=True)
 assets=Path(old['assets']);previous=Path(old['previous']);manifest=json.loads((previous/'paladin-vanilla-dimensions/install-manifest.json').read_text())
 # Run the exact-clip selector with Blender's current Python runtime.

 source=work/'sorcerer-source.glb'
 import runpy
 argv=sys.argv[:]
 try:
  sys.argv=[str(TOOLS/'select_paladin_animation.py'),str(assets/'sorm_all_anims.glb'),'sorM_STF_attk_weaponAttack',str(source)]
  runpy.run_path(str(TOOLS/'select_paladin_animation.py'),run_name='__main__')
 finally:sys.argv=argv
 target=work/'sorcerer-paladin.glb';retarget(assets/'Paladin-D1-Candidate-1-edited.glb',source,target)
 frames=[0,.9,1.8,2.7,3.6,4.5,5.4,6.3,7.2,8.1,9,12,18,27,36,45]
 recipe=work/'wltat-recipe.json';recipe.write_text(json.dumps({'name':'Selected Sorcerer staff melee','native_source_clip':'sorM_STF_attk_weaponAttack','source':str(target),'frames':frames,'arms':[],'preserve_attack_motion':True},indent=2))
 model=work/'wltat.glb';author(recipe,model);staff=work/'staff-attack.glb';bake(model,assets/'twoHandStaff_base01.glb',staff,16)
 original=next(j for j in old['jobs'] if j['sheet']=='wltat');ref=json.loads(Path(original['reference']).read_text());ref.update(cell=2048,source_frames=list(range(16)),render_directions=list(range(8)),root_anchor_frame=0,preview_prefix='wltat',preview_contact_row=10,preview_caption='WLTAT | Sorcerer staff melee / impact frame 11')
 for key in ['pose_offsets','pose_xy_offsets','native_root_drive','motion_root_bone']:ref.pop(key,None)
 ref['equipment']=[{'path':str(staff),'bone':'hand.R','local_transform':[list(r) for r in Matrix.Identity(4)],'town_role':'held_staff','allow_hand_grip_contact':True}]
 job_root=work/'jobs/wltat';job_root.mkdir(parents=True);rp=job_root/'reference.json';rp.write_text(json.dumps(ref,indent=2));plan=copy.deepcopy(old);plan.update(work=str(work),attack_only=True,preview_only=False,starting_custom_manifest=manifest,jobs=[{'sheet':'wltat','code':'wlt','action':'at','model':str(model),'root':str(job_root),'reference':str(rp),'motion':'wltat'}],motions=[{'name':'wltat'}],inventory={'wlt':{'wltat':old['inventory']['wlt']['wltat']}},copies=[],selected_native_clip='sorM_STF_attk_weaponAttack',native_contact_frame=9,attack_action_frame=11)
 (work/'plan.json').write_text(json.dumps(plan,indent=2));print('Prepared selected staff attack only',flush=True)
if __name__=='__main__':prepare(*sys.argv[sys.argv.index('--')+1:])

