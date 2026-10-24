"""Create a local diagnostic overlay; never upload this reference-derived image."""
import argparse
import json
from pathlib import Path
from PIL import Image,ImageDraw

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--model',type=Path,required=True)
parser.add_argument('--reference',type=Path,required=True)
args=parser.parse_args()
reference=json.loads((args.reference/'idle-masks.json').read_text())
contact=Image.new('RGB',(4*384,2*384),(20,20,25))
for direction in range(8):
    frame=Image.open(args.model/f'frames/idle/{direction}_00.png').getchannel('A').resize((96,96),Image.Resampling.BOX)
    actual=[v>=128 for v in frame.tobytes()]
    expected=[v>=128 for v in reference[direction]]
    cell=Image.new('RGB',(96,96))
    cell.putdata([(235,235,235) if a and b else (30,180,220) if a else (240,70,60) if b else (20,20,25)
                   for a,b in zip(actual,expected)])
    cell=cell.resize((384,384),Image.Resampling.NEAREST)
    ImageDraw.Draw(cell).text((12,12),str(direction),fill='white')
    contact.paste(cell,((direction%4)*384,(direction//4)*384))
contact.save(args.model/'silhouette-comparison.png')
print('White: overlap. Red: reference only. Cyan: model only.')
