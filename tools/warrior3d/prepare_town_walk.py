"""Measure private town-animation body bounds and extract palette-zero shadows."""
import sys,json,struct
from pathlib import Path
from PIL import Image
from prepare_reference import body_mask

png,cl2,out=map(Path,sys.argv[1:4]);out.mkdir(parents=True,exist_ok=True)
im=Image.open(png).convert('RGBA');assert im.width%8==0
cell=im.width//8;logical=cell//8;assert cell%8==0 and im.height%cell==0
rows=im.height//cell
data=cl2.read_bytes();offsets=struct.unpack_from('<8I',data);bounds=[]
for frame in range(rows):
 row=[]
 for direction in range(8):
  assert struct.unpack_from('<I',data,offsets[direction])[0]==rows
  mask=body_mask(data,offsets[direction],frame,width=logical);row.append(mask.getbbox())
  body=mask.resize((cell,cell),Image.Resampling.NEAREST)
  image_cell=im.crop((direction*cell,frame*cell,(direction+1)*cell,(frame+1)*cell))
  from PIL import ImageChops
  shadow=Image.new('RGBA',(cell,cell),(0,0,0,0));shadow.putalpha(ImageChops.subtract(image_cell.getchannel('A'),body))
  shadow.save(out/f'shadow-{direction}-{frame}.png')
 bounds.append(row)
(out/'reference.json').write_text(json.dumps({'sheet':png.name,'bounds':bounds,'cell':cell,'logical':logical,'columns':['S','SW','W','NW','N','NE','E','SE'],'rows':rows},indent=2))
