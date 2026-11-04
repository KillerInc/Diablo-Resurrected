"""Replace canonical ground materials, preserving native masks and tile reuse.

Unlike the earlier detail-transfer candidate, this allows new RGB at tile edges.
Materials repeat in world X/Z; each shared frame must have one compatible UV
phase across every occurrence. No per-location override or runtime change.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

from pack_ground_art import ground_only_frames


def phase(world):
    x,y=world
    return ((2*x+4*y)%128,(4*y-2*x)%128)


def periodic_material(image,target_mean):
    # Reflection joins have identical opposing edge pixels, independent of
    # whether a generated source is perfectly seamless at its outer border.
    image=image.convert('RGB')
    # The source covers several metres; one repeating native tile needs a
    # close material sample, otherwise all stones collapse into fine noise.
    side=min(256,image.width,image.height)
    left=(image.width-side)//2;top=(image.height-side)//2
    quarter=np.asarray(image.crop((left,top,left+side,top+side)).resize((64,64),Image.Resampling.LANCZOS)).astype(np.float32)
    top=np.concatenate((quarter,quarter[:,::-1]),axis=1)
    result=np.concatenate((top,top[::-1]),axis=0)
    result*=np.asarray(target_mean)/np.maximum(result.mean(axis=(0,1)),1)
    return np.clip(result,0,255)


def sample(material,uv_phase,cell=128):
    y,x=np.mgrid[:cell,:cell]
    # Inverse native projection: world X = screenX/256 + screenY/128
    # at density four; texture UV scale is 128 texels per native grid cell.
    u=(uv_phase[0]+x*.5+y)%128;v=(uv_phase[1]-x*.5+y)%128
    ux=np.floor(u).astype(int);vy=np.floor(v).astype(int)
    f=(u-ux)[:,:,None];g=(v-vy)[:,:,None]
    top=material[vy,ux]*(1-f)+material[vy,(ux+1)%128]*f
    bottom=material[(vy+1)%128,ux]*(1-f)+material[(vy+1)%128,(ux+1)%128]*f
    return top*(1-g)+bottom*g


def source_field(image,radius=6):
    pixels=np.asarray(image.convert('RGBA'));alpha=pixels[:,:,3]
    masked=pixels[:,:,:3].copy();masked[alpha==0]=0
    rgb=np.asarray(Image.fromarray(masked).filter(ImageFilter.GaussianBlur(radius))).astype(np.float32)
    a=np.asarray(Image.fromarray(alpha).filter(ImageFilter.GaussianBlur(radius))).astype(np.float32)
    return rgb*255/np.maximum(a[:,:,None],1)


def replace(original,dirt,grass,uv_phase):
    src=np.asarray(original.convert('RGBA'));field=source_field(original)
    # Native bare dirt is redder than grass. Retain its spatial transition,
    # not its RGB texture or nearest-neighbour pixel blocks.
    soil=np.clip((field[:,:,0]-field[:,:,1]+1)/11,0,1)
    soil=soil*soil*(3-2*soil)
    rgb=sample(grass,uv_phase)*(1-soil[:,:,None])+sample(dirt,uv_phase)*soil[:,:,None]
    result=src.copy();visible=src[:,:,3]>0
    result[visible,:3]=np.rint(np.clip(rgb,0,255)).astype(np.uint8)[visible]
    assert np.array_equal(src[:,:,3],result[:,:,3])
    assert np.array_equal(src[~visible],result[~visible])
    return Image.fromarray(result)


def build(args):
    if args.output.exists():raise ValueError('Use a new output directory')
    project=args.project.resolve();meta=json.loads((project/'project.json').read_text())
    if (meta.get('columns'),meta.get('rows'))!=(28,128):
        raise ValueError('This material mapping requires the native 28 by 128 town atlas')
    plan=json.loads(args.plan.read_text());frames=set(plan['frames'])
    micros=np.frombuffer(args.minimum.read_bytes(),dtype='<u2').reshape(-1,16)
    allowed=ground_only_frames(micros,args.sol.read_bytes())
    if not frames<=allowed:raise ValueError('Non-ground frame selected')
    phases=defaultdict(set);uses=defaultdict(int)
    for layer in meta['layers']:
        if layer['frame'] in frames:
            phases[layer['frame']].add(phase(layer['world']));uses[layer['frame']]+=1
    if set(phases)!=frames or any(len(v)!=1 for v in phases.values()):
        raise ValueError('A shared frame requires conflicting material phases')
    dirt=periodic_material(Image.open(args.dirt),(52,43,32))
    grass=periodic_material(Image.open(args.grass),(28,35,23))
    atlas=Image.open(project/'base-atlas.png').convert('RGBA');before=np.asarray(atlas).copy()
    if atlas.size!=(3584,16384):raise ValueError('Expected native-density-four town atlas')
    args.output.mkdir(parents=True);(args.output/'frames').mkdir()
    for f in sorted(frames):
        original=Image.open(project/f'frames/{f:04}.png').convert('RGBA')
        tile=replace(original,dirt,grass,next(iter(phases[f])))
        tile.save(args.output/f'frames/{f:04}.png');col,row=divmod(f-1,meta['rows'])
        atlas.paste(tile,(col*128,row*128))
    after=np.asarray(atlas);assert np.array_equal(before[:,:,3],after[:,:,3])
    for f in range(1,meta['columns']*meta['rows']+1):
        if f in frames:continue
        c,r=divmod(f-1,meta['rows']);assert np.array_equal(before[r*128:(r+1)*128,c*128:(c+1)*128],after[r*128:(r+1)*128,c*128:(c+1)*128])
    atlas.save(args.output/'town.png')
    report=dict(replaced_frames=sorted(frames),world_occurrences=sum(uses.values()),
                alpha_exact=True,unselected_rgba_exact=True,shared_frame_phases_validated=True,
                edge_policy='New RGB allowed; repeated material phase and native alpha preserved',
                material_mapping='Inverse native isometric projection, periodic world X/Z',
                per_instance_overrides=0,installed=False)
    (args.output/'validation.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='replaced_frames'}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('project','plan','minimum','sol','dirt','grass','output'):p.add_argument(name,type=Path)
    args=p.parse_args();build(args)
