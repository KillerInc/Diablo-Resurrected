"""Fit rendered town-animation alpha, retain vanilla shadows, assemble PNG.

Optional fourth argument reuses a prior validation JSON's scale/registrations
to keep the same character size and anchor across idle and walk.
"""
import sys,json,hashlib
from pathlib import Path
from PIL import Image,ImageDraw,ImageFilter
import numpy as np

frames,reference,out=map(Path,sys.argv[1:4]);out.mkdir(parents=True,exist_ok=True)
ref=json.loads((reference/'reference.json').read_text());boxes=ref['bounds']
rows=ref['rows'];filename=ref.get('sheet','wlnwl.png')
images=[[Image.open(frames/f'body-{d}-{r}.png').convert('RGBA') for d in range(8)] for r in range(rows)]
def bounds(im):return im.getchannel('A').point(lambda x:255 if x>=127 else 0).getbbox()
original_bounds=[[bounds(im) for im in row] for row in images]
target_height=np.mean([(b[3]-b[1])*8 for row in boxes for b in row]);actual_height=np.mean([b[3]-b[1] for row in original_bounds for b in row]);scale=float(target_height/actual_height)
registrations=[]
for d in range(8):
 center=np.mean([(row[d][0]+row[d][2])*.5 for row in original_bounds]);bottom=np.mean([row[d][3] for row in original_bounds])
 target_center=np.mean([(row[d][0]+row[d][2])*4 for row in boxes]);target_bottom=np.mean([row[d][3]*8 for row in boxes])
 registrations.append((float(target_center-scale*center),float(target_bottom-scale*bottom)))
if len(sys.argv)>4:
 calibration=json.loads(Path(sys.argv[4]).read_text());scale=calibration['global_pixel_scale'];registrations=calibration['fixed_direction_offsets']
shadow_root=Path(sys.argv[5]) if len(sys.argv)>5 else None
sheet=Image.new('RGBA',(6144,rows*768));cells=[];report={'global_pixel_scale':scale,'fixed_direction_offsets':registrations,'cells':[],'shadow_source':'animated model projection' if shadow_root else 'vanilla','body_rgb_gain':.62 if shadow_root else 1,'body_saturation':.86 if shadow_root else 1}
for r in range(rows):
 row=[]
 for d in range(8):
  dx,dy=registrations[d]
  # One uniform scale for all 64 cells; one constant anchor per direction.
  body=images[r][d].transform((768,768),Image.Transform.AFFINE,(1/scale,0,-dx/scale,0,1/scale,-dy/scale),resample=Image.Resampling.BICUBIC)
  if shadow_root:
   rgba=np.array(body);rgb=rgba[:,:,:3].astype(np.float32);luminance=rgb@np.array([.2126,.7152,.0722],dtype=np.float32)
   rgb=(luminance[:,:,None]+.86*(rgb-luminance[:,:,None]))*.62;rgba[:,:,:3]=np.clip(rgb,0,255).astype(np.uint8);body=Image.fromarray(rgba)
  box=body.getbbox();assert box and min(box[:2])>0 and max(box[2:])<768,('cropped sprite',d,r,box)
  if shadow_root:
   raw_shadow=Image.open(shadow_root/f'shadow-{d}-{r}.png').convert('RGBA')
   alpha=raw_shadow.getchannel('A').transform((768,768),Image.Transform.AFFINE,(1/scale,0,-dx/scale,0,1/scale,-dy/scale),resample=Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(2.0)).point(lambda v:round(v*.70))
   shadow=Image.new('RGBA',(768,768));shadow.putalpha(alpha)
  else:shadow=Image.open(reference/f'shadow-{d}-{r}.png').convert('RGBA')
  cell=Image.alpha_composite(shadow,body);sheet.paste(cell,(d*768,r*768));row.append(cell)
  report['cells'].append({'direction':d,'row':r,'body_bounds':bounds(body),'shadow_alpha_pixels':sum(x>0 for x in shadow.getchannel('A').getdata())})
 cells.append(row)
dest=out/filename;sheet.save(dest,compress_level=6)
with Image.open(dest) as check:assert check.size==(6144,rows*768) and check.mode=='RGBA'
report['sheet_sha256']=hashlib.sha256(dest.read_bytes()).hexdigest();report['size']=[6144,rows*768];report['rows']=rows;report['directions']=ref['columns'];report['timing']='Existing vanilla animation timing; source frames recorded in render.json.'
(out/'validation.json').write_text(json.dumps(report,indent=2))
preview=[]
for r in range(rows):
 canvas=Image.new('RGBA',(1200,625),(42,42,42,255));draw=ImageDraw.Draw(canvas)
 for j,(d,label) in enumerate([(0,'South'),(2,'West'),(4,'North')]):
  canvas.alpha_composite(cells[r][d].crop((180,110,580,710)),(j*400,25));draw.text((j*400+10,7),label,fill='white')
 preview.append(canvas.convert('RGB'))
preview_name='town-idle-preview.gif' if 'st' in filename else 'town-walk-preview.gif'
preview[0].save(out/preview_name,save_all=True,append_images=preview[1:],duration=130 if rows==20 else [170,160,170,170,160,170,170,160],loop=0,optimize=False)
contact=Image.new('RGBA',(768*4,768*2),(42,42,42,255))
for d in range(8):contact.alpha_composite(cells[0][d],((d%4)*768,(d//4)*768))
contact.resize((1536,768),Image.Resampling.LANCZOS).convert('RGB').save(out/'eight-directions.png')
print('Validated',rows*8,'uncropped cells; output',dest,'scale',scale)
