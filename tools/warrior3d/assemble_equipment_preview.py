"""Composite selected equipment views at a common world scale; never emit a sheet.

python SCRIPT BODY_FRAMES SHADOWS RENDER.json CALIBRATION.json OUTPUT
Unlike the full-pack assembler this accepts an explicitly partial direction set.
"""
import json,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
body_root,shadow_root,metadata,calibration,out=map(Path,sys.argv[1:6]);out.mkdir(exist_ok=True,parents=True)
info=json.loads(metadata.read_text());scale=json.loads(calibration.read_text())['global_pixel_scale'];origin=info['ground_origin_pixel'];directions=info['render_directions'];rows=info['output_rows'];assert directions==[0,2,3]
# A common preview rectangle keeps idle and attack at the same apparent scale.
logical=info.get('canvas_logical',192);logical=[logical,logical] if isinstance(logical,int) else logical;size=(max(1536,logical[0]*8),max(1408,logical[1]*8));ground=(size[0]//2,size[1]-256);view_width=size[0]//4;view_height=size[1]//4;dx=ground[0]-scale*origin[0];dy=ground[1]-scale*origin[1];previews=[];checks=[]
for row in range(rows):
 canvas=Image.new('RGB',(view_width*3,view_height+56),(38,38,38));draw=ImageDraw.Draw(canvas)
 for col,direction in enumerate(directions):
  body=Image.open(body_root/f'body-{direction}-{row}.png').convert('RGBA').transform(size,Image.Transform.AFFINE,(1/scale,0,-dx/scale,0,1/scale,-dy/scale),resample=Image.Resampling.BICUBIC);rgba=np.array(body);rgb=rgba[:,:,:3].astype(np.float32);lum=rgb@np.array([.2126,.7152,.0722]);rgba[:,:,:3]=np.clip((lum[:,:,None]+.86*(rgb-lum[:,:,None]))*.62,0,255).astype(np.uint8);body=Image.fromarray(rgba)
  alpha=Image.open(shadow_root/f'shadow-{direction}-{row}.png').getchannel('A').transform(size,Image.Transform.AFFINE,(1/scale,0,-dx/scale+256,0,1/scale,-dy/scale+256),resample=Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(2)).point(lambda x:round(x*.7))
  for kind,box in [('body',body.getbbox()),('shadow',alpha.getbbox())]:
   assert box and min(box[:2])>0 and box[2]<size[0] and box[3]<size[1],('Preview capture clips',kind,row,direction,box)
   checks.append({'row':row,'direction':direction,'kind':kind,'bounds':box})
  shadow=Image.new('RGBA',size);shadow.putalpha(alpha);view=Image.new('RGBA',size,(46,46,46,255));view=Image.alpha_composite(view,Image.alpha_composite(shadow,body));view=view.resize((view_width,view_height),Image.Resampling.LANCZOS);canvas.paste(view.convert('RGB'),(col*view_width,24));draw.text((col*view_width+10,7),['South','West','Northwest'][col],fill='white')
 draw.text((10,view_height+35),info['preview_caption']+' | frame '+str(row+1),fill='white');previews.append(canvas)
 if row==info.get('preview_contact_row',8):canvas.save(out/(info['preview_prefix']+'-contact.png'))
previews[0].save(out/(info['preview_prefix']+'-preview.gif'),save_all=True,append_images=previews[1:],duration=200 if info['preview_prefix'].endswith('idle') else 50,loop=0,optimize=False)
report={'preview_only':True,'direction_count':len(directions),'directions':directions,'frame_count':rows,'cells':checks,'world_scale_preserved':True,'game_sheets_written':False};(out/'validation.json').write_text(json.dumps(report,indent=2));print('Validated selected-direction preview; no game sheet emitted')
