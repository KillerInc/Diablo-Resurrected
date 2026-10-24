"""Measure private town-animation body bounds and extract palette-zero shadows."""
import sys,json,struct
from pathlib import Path
from PIL import Image
from prepare_reference import body_mask

png,cl2,out=map(Path,sys.argv[1:4]);out.mkdir(parents=True,exist_ok=True)
im=Image.open(png).convert('RGBA');assert im.width==6144 and im.height%768==0
rows=im.height//768
data=cl2.read_bytes();offsets=struct.unpack_from('<8I',data);bounds=[]
for frame in range(rows):
 row=[]
 for direction in range(8):
  assert struct.unpack_from('<I',data,offsets[direction])[0]==rows
  mask=body_mask(data,offsets[direction],frame);row.append(mask.getbbox())
  body=mask.resize((768,768),Image.Resampling.NEAREST)
  cell=im.crop((direction*768,frame*768,(direction+1)*768,(frame+1)*768))
  from PIL import ImageChops
  shadow=Image.new('RGBA',(768,768),(0,0,0,0));shadow.putalpha(ImageChops.subtract(cell.getchannel('A'),body))
  shadow.save(out/f'shadow-{direction}-{frame}.png')
 bounds.append(row)
(out/'reference.json').write_text(json.dumps({'sheet':png.name,'bounds':bounds,'cell':768,'logical':96,'columns':['S','SW','W','NW','N','NE','E','SE'],'rows':rows},indent=2))
