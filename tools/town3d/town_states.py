"""Extract both native fountain and catacombs states for private art review.

The state rules mirror levels/town.cpp; no game logic, save or installed pack
is changed. Inputs: town.til sector2s.dun town.min native-object-map.json atlas
base-region-directory output-new-directory.
"""
import argparse
from pathlib import Path
import json
import numpy as np
from PIL import Image

from town_canvas import fragments, digest


def fill_tile(cells, megas, x, z, tile):
    if not 1<=tile<=len(megas):raise ValueError('Mega tile outside TIL')
    result=cells.copy()
    for (dx,dz),piece in zip(((0,0),(1,0),(0,1),(1,1)),megas[tile-1]):
        result[x+dx,z+dz]=int(piece)
    return result


def sector_tile(raw,x,z):
    values=np.frombuffer(raw,dtype='<u2')
    if len(values)<2:raise ValueError('Truncated DUN header')
    width,height=map(int,values[:2])
    if not 0<=x<width or not 0<=z<height or len(values)<2+width*height:
        raise ValueError('DUN cell outside tile layer')
    return int(values[2+z*width+x])


def tile_frames(micros,megas,tile):
    return sorted({int(v)&4095 for piece in megas[tile-1] for v in micros[int(piece)] if int(v)&4095})


def southern_warp_states(cells,megas,sector3,sector1):
    """Native cave/hell variants; closed Hell has four random floor choices.

    Restore open tiles from sector3's actual DUN layer, never from a guessed
    visual. These private maps do not change game logic or the user's saves.
    """
    result={};opened=cells.copy()
    for x,z in ((16,68),(16,70)):
        tile=sector_tile(sector3,x//2,(z-46)//2)
        opened=fill_tile(opened,megas,x,z,tile)
    result['caves-open']=opened
    closed=fill_tile(fill_tile(opened,megas,16,68,332),megas,16,70,331)
    result['caves-closed']=closed
    opened=cells.copy()
    for x in range(36,46):
        # FillSector writes a 2x2 mega at even coordinates. DrlgTPass3's
        # closed loop later overwrites overlapping 2x2 blocks at EVERY x.
        even=x-x%2
        tile=sector_tile(sector3,even//2,(78-46)//2)
        opened=fill_tile(opened,megas,even,78,tile)
    # The closed loop at x=45 also writes x=46, beyond the even anchor 44.
    tile=sector_tile(sector1,0,(78-46)//2)
    opened=fill_tile(opened,megas,46,78,tile)
    result['hell-open']=opened
    for floor in (1,2,3,4):
        closed=opened.copy()
        for x in range(36,46):closed=fill_tile(closed,megas,x,78,floor)
        result[f'hell-closed-floor-{floor}']=closed
    return result


def render(layers,atlas,rect,density=4):
    left,top,width,height=rect;cell=32*density
    result=Image.new('RGBA',(width*density,height*density));cache={}
    for layer in layers:
        x=(layer['world'][0]-left)*density;y=(layer['world'][1]-top)*density
        if x>=result.width or y>=result.height or x+cell<=0 or y+cell<=0:continue
        frame=layer['frame']
        if frame not in cache:
            col,row=divmod(frame-1,128)
            cache[frame]=atlas.crop((col*cell,row*cell,(col+1)*cell,(row+1)*cell))
        result.alpha_composite(cache[frame],(x,y))
    return result


def build(args):
    if args.output.exists():raise ValueError('Use a new output directory')
    megas=np.frombuffer(args.til.read_bytes(),dtype='<u2').reshape(-1,4)
    micros=np.frombuffer(args.minimum.read_bytes(),dtype='<u2').reshape(-1,16)
    objects=json.loads(args.objects.read_text());cells={}
    for obj in objects:
        for x,z,piece,_ in obj['source_cells']:
            if (x,z) in cells and cells[x,z]!=piece:raise ValueError('Conflicting source cell')
            cells[x,z]=piece
    # town.cpp FillSector sector2s starts at (46,0), each DUN tile is 2x2 cells.
    open_tile=sector_tile(args.sector.read_bytes(),(48-46)//2,20//2)
    definitions=[('well-poisoned','well',60,70,342),('well-clean','well',60,70,71),
                 ('catacombs-closed','catacombs-entrance',48,20,320),
                 ('catacombs-open','catacombs-entrance',48,20,open_tile)]
    atlas=Image.open(args.atlas).convert('RGBA');args.output.mkdir(parents=True)
    records=[]
    for name,identity,x,z,tile in definitions:
        updated=fill_tile(cells,megas,x,z,tile)
        rect=json.loads((args.regions/identity/'region.json').read_text())['rect']
        image=render(fragments(micros,updated),atlas,rect)
        image.save(args.output/(name+'-native.png'))
        object_path=args.output/(name+'-native-object-map.json')
        object_path.write_text(json.dumps([dict(id=name,source_cells=[
            [cx,cz,piece,0] for (cx,cz),piece in sorted(updated.items())])],separators=(',',':')))
        records.append(dict(name=name,structure=identity,anchor=[x,z],mega_tile=tile,
                            pieces=[int(v) for v in megas[tile-1]],
                            canvas_objects=object_path.name,
                            affected_frames=tile_frames(micros,megas,tile),rect=rect,
                            native_pixel_sha256=digest(image)))
        # The supplied base town has poisoned water and the closed entrance.
        if name in ('well-poisoned','catacombs-closed'):
            reference=Image.open(args.regions/identity/'reference.png')
            if digest(image)!=digest(reference):raise ValueError('State reference does not match base town: '+name)
    pairs=[]
    for first,second in ((records[0],records[1]),(records[2],records[3])):
        a,b=set(first['affected_frames']),set(second['affected_frames'])
        pairs.append(dict(states=[first['name'],second['name']],shared_frames=sorted(a&b),
                          first_only_frames=sorted(a-b),second_only_frames=sorted(b-a)))
    manifest=dict(source_rules=['Source/levels/town.cpp DrlgTPass3 and CleanTownFountain',
                               'Source/levels/trigs.cpp IsWarpOpen'],states=records,pairs=pairs,
                  policy='Author both variants. Keep shared material pixels consistent; preserve water state and entrance obstruction.',
                  installed=False)
    (args.output/'states.json').write_text(json.dumps(manifest,indent=2))
    print(json.dumps(dict(states=[dict(name=r['name'],tile=r['mega_tile'],pieces=r['pieces']) for r in records],
                          frame_differences=pairs)))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('til','sector','minimum','objects','atlas','regions','output'):p.add_argument(name,type=Path)
    args=p.parse_args();build(args)
