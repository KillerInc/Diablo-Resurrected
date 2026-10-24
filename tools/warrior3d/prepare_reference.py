"""Measure local NN8 Warrior references without copying artwork into Git."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from PIL import Image


def body_mask(data,base,frame,width=96):
    start,end=struct.unpack_from('<II',data,base+4*(frame+1))
    payload=data[base+start:base+end]
    position=struct.unpack_from('<H',payload)[0]
    pixels=[]
    while position<len(payload):
        control=payload[position]; position+=1
        if control<128:
            pixels.extend([-1]*control)
        elif control<=190:
            pixels.extend([payload[position]]*(191-control)); position+=1
        else:
            length=256-control
            pixels.extend(payload[position:position+length]); position+=length
    if len(pixels)%width or len(pixels)//width>width:
        raise ValueError('Original CL2 frame does not fit the logical cell')
    height=len(pixels)//width
    result=Image.new('L',(width,width),0)
    rows=[pixels[i*width:(i+1)*width] for i in range(height)][::-1]
    # Palette index 0 is the original baked ground shadow. Excluding it from
    # anatomy/camera fitting prevents treating the shadow as a foot or limb.
    values=[255 if value>0 else 0 for row in rows for value in row]
    frame_image=Image.new('L',(width,height)); frame_image.putdata(values)
    result.paste(frame_image,(0,width-height))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--nn-root', type=Path, required=True)
    parser.add_argument('--original-root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = {'class': 'warrior', 'equipment': 'light armor, unarmed, no shield',
              'scale': 8, 'cell': [768, 768], 'directions': 8,
              'direction_names': ['South','SouthWest','West','NorthWest','North','NorthEast','East','SouthEast'],
              'animations': {}}
    for animation, filename in [('idle','wlnas'),('walk','wlnaw')]:
        relative = Path('plrgfx/warrior/wln') / filename
        png = args.nn_root / relative.with_suffix('.png')
        cl2 = args.original_root / relative.with_suffix('.cl2')
        data = cl2.read_bytes()
        offsets = struct.unpack_from('<8I',data)
        frames = [struct.unpack_from('<I',data,offset)[0] for offset in offsets]
        if len(set(frames)) != 1:
            raise ValueError('This first model export expects equal direction lengths')
        with Image.open(png) as source:
            expected = (768*8,768*frames[0])
            if source.size != expected:
                raise ValueError(f'{png}: expected {expected}, found {source.size}')
            alpha = source.getchannel('A').resize((96*8,96*frames[0]),Image.Resampling.BOX)
        boxes = []
        masks = []
        for frame in range(frames[0]):
            row=[]
            for direction in range(8):
                cell = alpha.crop((direction*96,frame*96,(direction+1)*96,(frame+1)*96))
                mask = body_mask(data,offsets[direction],frame)
                row.append(mask.getbbox())
                masks.append(list(mask.tobytes()))
            boxes.append(row)
        result['animations'][animation] = {'sheet':str(relative.with_suffix('.png')).replace('\\','/'),
            'frames':frames[0], 'source_size':expected, 'bounds_logical':boxes,
            'fitting_mask':'original CL2 body pixels excluding palette-index-0 ground shadow',
            'source_sha256':hashlib.sha256(png.read_bytes()).hexdigest()}
        args.out.mkdir(parents=True,exist_ok=True)
        # Numeric silhouettes are local comparison inputs; not packed in .blend or committed.
        (args.out/f'{animation}-masks.json').write_text(json.dumps(masks,separators=(',',':')))
    (args.out/'reference.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({name:{'frames':v['frames'],'bounds_first_frame':v['bounds_logical'][0]}
                      for name,v in result['animations'].items()},indent=2))


if __name__ == '__main__':
    main()
