"""Use the approved idle ground shadow throughout an attack preview.

python SCRIPT IDLE_SHADOW_DIRECTORY ATTACK_REFERENCE.json OUTPUT_DIRECTORY
This deliberately holds the shadow stable; it does not project the kicking leg.
The larger raw canvas is padded equally before the normal bottom registration.
"""
import json,sys
from pathlib import Path
from PIL import Image
source,reference,out=map(Path,sys.argv[1:4]);ref=json.loads(reference.read_text())
cell=ref['cell'];out.mkdir(parents=True,exist_ok=True)
for d in range(8):
    idle=Image.open(source/f'shadow-{d}-0.png').convert('RGBA')
    assert idle.width==idle.height and cell>=idle.width and (cell-idle.width)%2==0
    pad=(cell-idle.width)//2
    canvas=Image.new('RGBA',(cell,cell));canvas.alpha_composite(idle,(pad,pad))
    for row in range(ref['rows']):canvas.save(out/f'shadow-{d}-{row}.png')
(out/'shadow.json').write_text(json.dumps({
    'method':'approved idle ground shadow held across attack',
    'source_frame':0,'directions':8,'frames':ref['rows'],
    'raised_leg_projection':False,'shadow_geometry_rescaled':False,
},indent=2))
