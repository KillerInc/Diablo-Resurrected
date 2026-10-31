"""Pad a rendered sprite canvas without changing scale, animation or world anchor."""
import json,math
from pathlib import Path
from PIL import Image

def fit(frames,shadows,render_file,calibration,reference):
 frames,shadows,render_file,calibration,reference=map(Path,(frames,shadows,render_file,calibration,reference));info=json.loads(render_file.read_text());ref=json.loads(reference.read_text());scale=json.loads(calibration.read_text())['global_pixel_scale'];density=8;width,height=info['canvas_logical'];ax,ay=info['canvas_anchor'];ground=(ax*density,(ay-16)*density);origin=info['ground_origin_pixel'];bounds=[]
 for row in range(info['output_rows']):
  source=(info.get('source_render_rows') or list(range(info['output_rows'])))[row];offset=(info.get('pose_image_offsets') or [[0,0]]*info['output_rows'])[row]
  for direction in range(8):
   delta=info.get('direction_image_offsets',[[0,0]]*8)[direction];dx=ground[0]-scale*origin[0]+offset[0]+delta[0];dy=ground[1]-scale*origin[1]+offset[1]+delta[1]
   for folder,prefix,overscan in [(frames,'body',0),(shadows,'shadow',256)]:
    with Image.open(folder/f'{prefix}-{direction}-{source}.png') as im:box=im.getchannel('A').getbbox()
    assert box
    bounds.append([dx+scale*(box[0]-overscan),dy+scale*(box[1]-overscan),dx+scale*(box[2]-overscan),dy+scale*(box[3]-overscan)])
 left=max(0,math.ceil((16-min(b[0] for b in bounds))/density));top=max(0,math.ceil((16-min(b[1] for b in bounds))/density));right=max(0,math.ceil((max(b[2] for b in bounds)+16-width*density)/density));bottom=max(0,math.ceil((max(b[3] for b in bounds)+16-height*density)/density));assert left+top+right+bottom>0,'Assembly failed for a reason other than canvas size'
 change={'original_canvas':[width,height],'original_anchor':[ax,ay],'padding_logical':[left,top,right,bottom],'character_scale_changed':False,'world_anchor_changed':False}
 for record in (info,ref):record.update(canvas_logical=[width+left+right,height+top+bottom],canvas_anchor=[ax+left,ay+top],canvas_padding=change)
 render_file.write_text(json.dumps(info,indent=2));reference.write_text(json.dumps(ref,indent=2));print('PADDED_RENDERED_CANVAS',info['sheet'],change,flush=True);return change

if __name__=="__main__":
 import sys
 fit(*sys.argv[1:6])
