"""Correct the H3 shield's hand grip without changing body animation or scale."""
import copy
import numpy as np

REVISION='small-handgrip-180-v1'
OLD_GRIP=np.array([-.2,0,-.1])
HAND_GRIP=np.array([.23,0,-.1])
# Measured shield-plane normal in the imported mesh's own coordinates.
NORMAL=np.array([.008661111816763878,.0014705377398058772,.9999614357948303])
NORMAL/=np.linalg.norm(NORMAL)
ROTATION=2*np.outer(NORMAL,NORMAL)-np.eye(3)

def correct(item):
 result=copy.deepcopy(item)
 if result.get('shield_grip_revision')==REVISION:return result
 if not str(result.get('path',result.get('filename',''))).endswith('Shield_S15_Warrior_Red.glb'):return result
 old=np.array(result.get('grip',OLD_GRIP),dtype=float)
 if result.get('local_transform'):
  matrix=np.array(result['local_transform'],dtype=float);point=matrix[:3,:3]@old+matrix[:3,3];matrix[:3,:3]=matrix[:3,:3]@ROTATION;matrix[:3,3]=point-matrix[:3,:3]@HAND_GRIP;result['local_transform']=matrix.tolist()
 if result.get('local_basis'):result['local_basis']=(np.array(result['local_basis'])@ROTATION).tolist()
 result.update(grip=HAND_GRIP.tolist(),shield_grip_revision=REVISION)
 return result
