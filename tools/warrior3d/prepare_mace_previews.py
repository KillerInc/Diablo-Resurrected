"""Prepare both supplied mace models against existing approved body/shield poses.

python SCRIPT EQUIPPED_PLAN.json APPROVED_MOUNTS.json NEW_PRIVATE_OUTPUT
Output is explicitly a three-direction preview, never an installable pack.
"""
import json,copy,sys
from pathlib import Path
import numpy as np
plan_file,mounts_file,output=map(Path,sys.argv[1:]);plan=json.loads(plan_file.read_text());work=output.resolve();work.mkdir(exist_ok=False);jobs=[]
for label,filename in [('M1','mace_base03.glb'),('M2','mace_base07.glb')]:
 for action,sheet in [('idle','wldas'),('swing','wldat')]:
  donor=next(j for j in plan['jobs'] if j['sheet']==sheet);ref=json.loads(Path(donor['reference']).read_text());gear=next(e for e in ref['equipment'] if 'sword_base00' in e['path']);old=np.array(gear.get('local_transform')) if gear.get('local_transform') else None
  if old is None:
   mount=json.loads(mounts_file.read_text())[0];gear.update(local_transform=mount['local_transform']);old=np.array(gear['local_transform'])
  grip=np.array([0,.18,0]);point=old[:3,:3]@np.array(gear['grip'])+old[:3,3];old[:3,3]=point-old[:3,:3]@grip;gear.update(path=str(Path(plan['assets'])/filename),grip=grip.tolist(),local_transform=old.tolist())
  name=label.lower()+'-'+action;ref.update(sheet=name+'.png',render_directions=[0,2,3],preview_prefix=name,preview_caption=label+' '+filename+' | same native '+action+' / corrected shield',preview_contact_row=0 if action=='idle' else 8);jobroot=work/name;jobroot.mkdir(exist_ok=True);r=jobroot/'reference.json';r.write_text(json.dumps(ref,indent=2));jobs.append({'name':name,'model':donor['model'],'reference':str(r),'root':str(jobroot),'label':label,'action':action,'preview_only':True})
(work/'plan.json').write_text(json.dumps({'jobs':jobs,'calibration':plan['calibration'],'preview_only':True,'rendered_directions':['S','W','NW'],'grip':[0,.18,0],'weapon_scale':.75,'approved_body_and_shield_preserved':True},indent=2));print('Prepared both maces in the same idle and full native attack with approved shield mount')
