"""Author/check an attack-only revision without changing the installed pack.

Blender --python SCRIPT -- EXISTING_PLAN.json PRIVATE_WORK SWORD_CUT.glb SHIELD_SMASH.glb
The last two inputs are matching-rig merged native clips prepared locally.
Render the resulting plan with build_equipped_sets.py render, then review.
"""
import copy,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from author_equipped_motion import author
from preflight_equipped_sets import check
from equipped_attack_recipe import make_attack_recipe

def refine(plan_file,work,sword_cut,shield_smash,sword_canvas_profile=None):
 sword_cut,shield_smash=map(lambda p:str(Path(p).resolve()),[sword_cut,shield_smash])
 plan=json.loads(Path(plan_file).read_text());work=Path(work).resolve();assert not (work/'refinement-plan.json').exists(),'Use a new revision directory';work.mkdir(parents=True,exist_ok=True);previous=Path(plan['previous']);old_jobs={j['sheet']:j for j in plan['jobs']};jobs=[];motions=[];records=[]
 for code in ['wld','wls','wlu']:
  canvas=json.loads(Path(sword_canvas_profile).read_text()) if sword_canvas_profile and code!='wlu' else None
  sheet=code+'at';folder=work/sheet;folder.mkdir(exist_ok=True);old=old_jobs[sheet];idle=previous/'paladin-sword-shield/Paladin-armed-idle-body.glb' if code in ('wld','wlu') else Path(old_jobs[code+'as']['model']);recipe=make_attack_recipe(code,idle,shield_smash if code=='wlu' else sword_cut,previous/'paladin-town-idle/Paladin-D1-idle.glb');recipe_path=folder/'recipe.json';recipe_path.write_text(json.dumps(recipe,indent=2));model=folder/'authored.glb';author(recipe_path,model)
  ref=json.loads(Path(old['reference']).read_text());ref.update(render_directions=list(range(8)),source_frames=list(range(16)),preview_caption=recipe['name']+' | frame-9 impact');ref.pop('pose_offsets',None)
  if canvas:
   ref.update(canvas_logical=canvas['logical'],canvas_anchor=canvas['anchor']);plan['inventory'][code][sheet]['size']=[canvas['logical'][0]*8*8,canvas['logical'][1]*8*16]
  reference=folder/'reference.json';reference.write_text(json.dumps(ref,indent=2));result=check(model,reference);ref['pose_offsets']=result.pop('pose_offsets');reference.write_text(json.dumps(ref,indent=2));record=dict(result,motion=old['motion'],sheet=sheet);records.append(record);(folder/'preflight.json').write_text(json.dumps(record,indent=2));job=copy.deepcopy(old);job.update(root=str(folder),model=str(model),reference=str(reference));jobs.append(job);motions.append({'name':old['motion'],'recipe':str(recipe_path),'model':str(model)})
 plan.update(work=str(work),jobs=jobs,motions=motions,copies=[],attack_only=True,previous_plan=str(Path(plan_file).resolve()),starting_custom_manifest=json.loads((previous/'paladin-vanilla-dimensions/install-manifest.json').read_text()));(work/'refinement-plan.json').write_text(json.dumps(plan,indent=2));(work/'preflight-progress.json').write_text(json.dumps(records,indent=2));(work/'refinement-checks.json').write_text(json.dumps(records,indent=2));assert all(r['safe'] for r in records),'Review failed poses; do not damp attack rotations automatically';print('All three complete attack revisions pass geometry checks',flush=True)

if __name__=='__main__':refine(*sys.argv[sys.argv.index('--')+1:])
