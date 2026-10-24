"""Fit rendered body alpha to vanilla WLNWL, retain its shadow, assemble PNG."""
import sys,json,hashlib
from pathlib import Path
from PIL import Image,ImageDraw
import numpy as np

frames,reference,out=map(Path,sys.argv[1:4]);out.mkdir(parents=True,exist_ok=True)
ref=json.loads((reference/'reference.json').read_text());boxes=ref['bounds']
images=[[Image.open(frames/f'body-{d}-{r}.png').convert('RGBA') for d in range(8)] for r in range(8)]
def bounds(im):return im.getchannel('A').point(lambda x:255 if x>=127 else 0).getbbox()
original_bounds=[[bounds(im) for im in row] for row in images]
target_height=np.mean([(b[3]-b[1])*8 for row in boxes for b in row]);actual_height=np.mean([b[3]-b[1] for row in original_bounds for b in row]);scale=float(target_height/actual_height)
registrations=[]
for d in range(8):
 center=np.mean([(row[d][0]+row[d][2])*.5 for row in original_bounds]);bottom=np.mean([row[d][3] for row in original_bounds])
 target_center=np.mean([(row[d][0]+row[d][2])*4 for row in boxes]);target_bottom=np.mean([row[d][3]*8 for row in boxes])
 registrations.append((float(target_center-scale*center),float(target_bottom-scale*bottom)))
sheet=Image.new('RGBA',(6144,6144));cells=[];report={'global_pixel_scale':scale,'fixed_direction_offsets':registrations,'cells':[]}
for r in range(8):
 row=[]
 for d in range(8):
  dx,dy=registrations[d]
  # One uniform scale for all 64 cells; one constant anchor per direction.
  body=images[r][d].transform((768,768),Image.Transform.AFFINE,(1/scale,0,-dx/scale,0,1/scale,-dy/scale),resample=Image.Resampling.BICUBIC)
  box=body.getbbox();assert box and min(box[:2])>0 and max(box[2:])<768,('cropped sprite',d,r,box)
  shadow=Image.open(reference/f'shadow-{d}-{r}.png').convert('RGBA');cell=Image.alpha_composite(shadow,body);sheet.paste(cell,(d*768,r*768));row.append(cell)
  report['cells'].append({'direction':d,'row':r,'body_bounds':bounds(body),'shadow_alpha_pixels':sum(x>0 for x in shadow.getchannel('A').getdata())})
 cells.append(row)
dest=out/'wlnwl.png';sheet.save(dest,compress_level=6)
with Image.open(dest) as check:assert check.size==(6144,6144) and check.mode=='RGBA'
report['sheet_sha256']=hashlib.sha256(dest.read_bytes()).hexdigest();report['size']=[6144,6144];report['rows']=8;report['directions']=ref['columns'];report['timing']='Existing vanilla animation timing; 40-frame source sampled at 1,6,11,16,21,26,31,36.'
(out/'validation.json').write_text(json.dumps(report,indent=2))
preview=[]
for r in range(8):
 canvas=Image.new('RGBA',(1200,625),(42,42,42,255));draw=ImageDraw.Draw(canvas)
 for j,(d,label) in enumerate([(0,'South'),(2,'West'),(4,'North')]):
  canvas.alpha_composite(cells[r][d].crop((180,110,580,710)),(j*400,25));draw.text((j*400+10,7),label,fill='white')
 preview.append(canvas.convert('RGB'))
preview[0].save(out/'town-walk-preview.gif',save_all=True,append_images=preview[1:],duration=[170,160,170,170,160,170,170,160],loop=0,optimize=False)
contact=Image.new('RGBA',(768*4,768*2),(42,42,42,255))
for d in range(8):contact.alpha_composite(cells[0][d],((d%4)*768,(d//4)*768))
contact.resize((1536,768),Image.Resampling.LANCZOS).convert('RGB').save(out/'eight-directions.png')
print('Validated 64 uncropped cells; output',dest,'scale',scale)
