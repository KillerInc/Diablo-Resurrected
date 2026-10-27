"""Blender --python SCRIPT -- ORIGINAL_PREVIEW_WORK STAFF_PLAN NEW_WORK
Preview the user's hand-clearance and staff-slide adjustment to the originally
selected Sorcerer attack. Keeps the original frames, body, scale and staff roll.
Only the two arm chains move. Does not install game sheets.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from author_equipped_motion import author
from bake_staff_equipment import bake

def prepare(original,staff_plan,work):
 original=Path(original).resolve();old=json.loads(Path(staff_plan).read_text());work=Path(work).resolve();assert not work.exists();work.mkdir(parents=True)
 recipe=json.loads((original/'sorcerer-recipe.json').read_text());assert recipe['frames']==[i*3 for i in range(16)] and not recipe.get('arms')
 recipe.update(name='Original Sorcerer staff, forward hand clearance and shorter projection',hand_offsets={side:[[0,0,.15] for _ in range(16)] for side in ['R','L']});recipe_file=work/'recipe.json';recipe_file.write_text(json.dumps(recipe,indent=2));model=work/'sorcerer.glb';author(recipe_file,model);staff=work/'staff.glb';bake(model,Path(old['assets'])/'twoHandStaff_base01.glb',staff,16,grip_slide=-.1875)
 ref=json.loads((original/'sorcerer/reference.json').read_text());ref.update(preview_prefix='sorcerer-grip',preview_caption='Original Sorcerer | forward hand clearance / 15cm shorter projection');ref['equipment'][0]['path']=str(staff);out=work/'preview';out.mkdir();reference=out/'reference.json';reference.write_text(json.dumps(ref,indent=2));plan={'preview_only':True,'work':str(work),'calibration':old['calibration'],'jobs':[{'name':'Sorcerer grip refinement','sheet':'wltat','action':'at','model':str(model),'root':str(out),'reference':str(reference)}]};(work/'plan.json').write_text(json.dumps(plan,indent=2));print('Prepared original Sorcerer timing and motion with requested hand/staff placement',flush=True)
if __name__=='__main__':prepare(*sys.argv[sys.argv.index('--')+1:])

