"""Prepare existing native matching-rig clips locally; no artwork in Git.

python SCRIPT ASSETS_DIRECTORY PRIVATE_WORK_DIRECTORY
"""
import subprocess,sys
from pathlib import Path
from merge_paladin_walk import merge

def prepare(assets,work):
 assets=Path(assets);root=Path(work)/'sources';root.mkdir(parents=True,exist_ok=True);tools=Path(__file__).resolve().parent
 for tag,clip in [('walk','palM_1hsShd_nav_walk'),('attack','palM_1HSShd_attk_weaponAttack'),('sword-cut','palM_1hsShd_attk_swordAndBoard'),('shield-smash','palM_1hsShd_attk_shieldBash'),('shield-charge','palM_1hsShd_attk_shieldCharge_3units'),('hit','palM_1hsShd_reac_flinch_B'),('block','palM_1hsSH_attk_withstand')]:
  selected=root/(tag+'-native.glb');merged=root/(tag+'.glb');subprocess.run([sys.executable,str(tools/'select_paladin_animation.py'),str(assets/'palm_all_anims.glb'),clip,str(selected)],check=True);merge(assets/'Paladin-D1-Candidate-1-edited.glb',selected,merged)
 subprocess.run([sys.executable,str(tools/'shorten_paladin_stride.py'),str(root/'walk.glb'),str(root/'walk-short.glb')],check=True)

if __name__=='__main__':prepare(*sys.argv[1:])
