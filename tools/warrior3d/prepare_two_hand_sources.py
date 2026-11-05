"""Prepare existing native Paladin two-handed clips without copying art to Git.

python SCRIPT LOCAL_ASSET_DIRECTORY PRIVATE_SOURCE_DIRECTORY
"""
import json,subprocess,sys
from pathlib import Path
from merge_paladin_walk import merge,read
assets,out=map(Path,sys.argv[1:]);out.mkdir(exist_ok=True,parents=True);tools=Path(__file__).parent;base,base_binary=read(assets/'Paladin-D1-Candidate-1-edited.glb')
for tag,name in [('idle','palM_2HM_nav_idle'),('attack','palM_2HM_attk_basic'),('walk','palM_2HM_nav_walk'),('hit','palM_2HM_reac_flinch_B')]:
 native=out/(tag+'-native.glb');body=out/(tag+'.glb')
 if not native.exists():subprocess.run([sys.executable,str(tools/'select_paladin_animation.py'),str(assets/'palm_all_anims.glb'),name,str(native)],check=True)
 g,_=read(native);assert [a['name'] for a in g['animations']]==[name]
 if not body.exists():merge(assets/'Paladin-D1-Candidate-1-edited.glb',native,body)
 g,binary=read(body);assert [a['name'] for a in g['animations']]==[name]
 for field in ['nodes','skins','meshes','images','materials']:assert g.get(field)==base.get(field),('Cached body differs',field)
 assert binary.startswith(base_binary),'Cached body image/mesh buffer differs'
subprocess.run([sys.executable,str(tools/'shorten_paladin_stride.py'),str(out/'walk.glb'),str(out/'walk-short.glb')],check=True)
subprocess.run([sys.executable,str(tools/'fit_two_hand_axe.py'),str(assets/'twoHandAxe_base01.glb'),str(out/'equipment/twoHandAxe_base01.glb')],check=True)
print('Prepared native two-handed idle, attack, short-stride walk and hit reaction')
