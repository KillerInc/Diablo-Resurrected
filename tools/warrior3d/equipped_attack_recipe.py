"""Full native sword attacks and an authored forward shield-face smash.

Only timing and horizontal alignment change in the sword animation. Attack
contact is output row 8 (game frame 9). All artwork is supplied locally.
"""
from pathlib import Path
import copy,json


def make_attack_recipe(code,idle,native,empty_idle):
 assert code in ('wld','wls','wlu')
 idle,native=map(str,[idle,native])
 if code!='wlu':
  return {'name':code+' full native swordAndBoard','source':native,'frames':[0,1,2,3,4,5,6,7,8,10,40,43,46,50,55,59],'arms':[],'idle':idle,'finger_grip':[],'arm_gain':1,'motion_gain':1,'align_horizontal_root':True,'preserve_attack_motion':True}
 frames=[0,0,1,2,3,4,5,6,7,8,9,9,9,9,9,9];weights=[1,.75,.45,.15,0,0,0,0,0,0,.05,.2,.4,.65,.85,1]
 profile=json.loads((Path(__file__).parent/'shield_attack_equipment.json').read_text());constraint={k:profile[k] for k in ['bone','hand','up_local','normal_local','grip_local','hand_grip_local','scale','weighted_body_vertices']};constraint.update(follow_hand=True,preserve_mount_rotation=True,reference_row=0,forward=[0,0,1],weights=[0,.4,.8,1,1,1,1,1,1,1,1,1,.8,.5,.2,0])
 return {'name':'Native ShieldCharge_3units smooth upright bash','native_source_clip':'palM_1hsShd_attk_shieldCharge_3units','source':native,'frames':frames,'idle':idle,'idle_weights':weights,'arms':[],'finger_grip':[],'arm_gain':1,'motion_gain':1,'align_horizontal_root':False,'preserve_attack_motion':True,'temporal_smoothing_passes':2,'locked_rows':[0,8,15],'wrist_shield_vertical':[{k:constraint[k] for k in ['bone','hand','normal_local','weights']}],'attachment_constraints':[constraint]}


def shield_attack_equipment(equipment):
 profile=json.loads((Path(__file__).parent/'shield_attack_equipment.json').read_text());result=copy.deepcopy(equipment)
 for item in result:
  if Path(item['path']).name==profile['filename']:item.update(bone=profile['bone'],local_transform=profile['local_transform'],grip=profile['grip'],shield_grip_revision=profile['shield_grip_revision'])
 return result
