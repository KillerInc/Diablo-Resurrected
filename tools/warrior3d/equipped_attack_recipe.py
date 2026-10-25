"""Full native sword attacks and an authored forward shield-face smash.

Only timing and horizontal alignment change in the sword animation. Attack
contact is output row 8 (game frame 9). All artwork is supplied locally.
"""
from pathlib import Path


def make_attack_recipe(code,idle,native,empty_idle):
 assert code in ('wld','wls','wlu')
 idle,native=map(str,[idle,native])
 if code!='wlu':
  return {'name':code+' full native swordAndBoard','source':native,'frames':[0,1,2,3,4,5,6,7,8,10,40,43,46,50,55,59],'arms':[],'idle':idle,'finger_grip':[],'arm_gain':1,'motion_gain':1,'align_horizontal_root':True,'preserve_attack_motion':True}
 pulse=[0,-.04,-.07,-.09,-.09,-.04,.10,.26,.34,.29,.18,.08,.01,0,0,0];body=[0,0,.02,.03,.03,.05,.12,.22,.3,.24,.16,.08,.03,0,0,0]
 return {'name':'Forward shield-face smash, frame-9 impact','source':idle,'frames':[0]*16,'arms':[{'side':'R','source':str(empty_idle),'frames':[0]*16}],'idle':idle,'finger_grip':['L'],'arm_gain':1,'motion_gain':1,'preserve_attack_motion':True,'node_overlays':[{'nodes':['chest','pelvis','thigh.L','thigh.R','shin.L','shin.R','foot.L','foot.R'],'source':native,'frames':[0]*16,'weights':body}],'hand_offsets':{'L':[[-.22*q/.34,-.04*q/.34,.28*q/.34] for q in pulse]}}
