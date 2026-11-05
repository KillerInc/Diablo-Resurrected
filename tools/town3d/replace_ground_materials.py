"""Replace canonical ground materials, preserving native masks and tile reuse.

Unlike the earlier detail-transfer candidate, this allows new RGB at tile edges.
Materials repeat in world X/Z; each shared frame must have one compatible UV
phase across every occurrence. No per-location override or runtime change.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

from pack_ground_art import ground_only_frames


def phase(world):
    x,y=world
    return ((2*x+4*y)%128,(4*y-2*x)%128)


def periodic_material(image,target_mean):
    # Keep the original stochastic arrangement instead of reflecting a small
    # sample into four quadrants, which creates conspicuous curls/rosettes.
    # A generated high-resolution material is not automatically a detailed
    # runtime tile: shrinking a 512px sample to 128px discards its fine grit.
    # Retain one source texel per material texel. Small synthetic inputs may
    # still be enlarged for offline tests; production materials are >=128px.
    image=image.convert('RGB');side=min(128,image.width,image.height)
    left=(image.width-side)//2;top=(image.height-side)//2
    patch=image.crop((left,top,left+side,top+side))
    if patch.size!=(128,128):patch=patch.resize((128,128),Image.Resampling.LANCZOS)
    result=np.asarray(patch).astype(np.float32).copy()
    for axis in (0,1):
        view=np.swapaxes(result,0,axis)
        edge=(view[0]+view[-1])*.5
        # Match only the boundary sample. Wide feather strips reduce local
        # variance and read as a regular crosshatch under isometric projection.
        view[0]=edge;view[-1]=edge
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
    # Preserve baked cast shadows and coloured window/cathedral spill, while
    # replacing the underlying material. Native high-frequency dithering is
    # not transferred. Expected values describe unlit native grass and dirt.
    expected=np.array([31,31,31])*(1-soil[:,:,None])+np.array([55,42,48])*soil[:,:,None]
    illumination=np.clip(field/expected,.08,2.4)
    rgb*=illumination
    result=src.copy();visible=src[:,:,3]>0
    result[visible,:3]=np.rint(np.clip(rgb,0,255)).astype(np.uint8)[visible]
    assert np.array_equal(src[:,:,3],result[:,:,3])
    assert np.array_equal(src[~visible],result[~visible])
    return Image.fromarray(result)


def preserve_authored_pixels(before,after,protected):
    """Ground-eligible native cells can contain subsequently painted objects."""
    if before.shape!=after.shape or protected.shape!=before.shape[:2]:
        raise ValueError('Authored protection geometry changed')
    result=after.copy();result[protected]=before[protected]
    return result


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
    # Include tiles absent from this town state (for example an opened warp).
    # Integer world-cell translations do not change this material period.
    for piece in micros:
        for block in range(16):
            f=int(piece[14+(block&1)-(block&14)])&4095
            if f in frames:
                phases[f].add(phase((-32+(block&1)*32,-(block//2)*32-31)))
    for layer in meta['layers']:
        if layer['frame'] in frames:
            phases[layer['frame']].add(phase(layer['world']));uses[layer['frame']]+=1
    if set(phases)!=frames or any(len(v)!=1 for v in phases.values()):
        raise ValueError('A shared frame requires conflicting material phases')
    dirt=periodic_material(Image.open(args.dirt),(52,43,32))
    grass=periodic_material(Image.open(args.grass),(33,32,26))
    atlas=Image.open(getattr(args,'initial_atlas',None) or project/'base-atlas.png').convert('RGBA');before=np.asarray(atlas).copy()
    native=Image.open(project/'base-atlas.png').convert('RGBA')
    if atlas.size!=native.size or not np.array_equal(np.asarray(native)[:,:,3],before[:,:,3]):
        raise ValueError('Initial atlas changed native geometry or alpha')
    if atlas.size!=(3584,16384):raise ValueError('Expected native-density-four town atlas')
    args.output.mkdir(parents=True);(args.output/'frames').mkdir()
    for f in sorted(frames):
        original=Image.open(project/f'frames/{f:04}.png').convert('RGBA')
        tile=replace(original,dirt,grass,next(iter(phases[f])))
        tile.save(args.output/f'frames/{f:04}.png');col,row=divmod(f-1,meta['rows'])
        atlas.paste(tile,(col*128,row*128))
    after=np.asarray(atlas)
    protected_count=0
    if getattr(args,'protected_pixels',None):
        with np.load(args.protected_pixels,allow_pickle=False) as protection:
            initial=Path(getattr(args,'initial_atlas',None) or project/'base-atlas.png')
            if str(protection['source_sha256'])!=hashlib.sha256(initial.read_bytes()).hexdigest():
                raise ValueError('Authored protection belongs to a different initial atlas')
            protected=protection['protected'].astype(bool)
        after=preserve_authored_pixels(before,after,protected)
        protected_count=int((protected&(before[:,:,3]>0)).sum())
        atlas=Image.fromarray(after)
        # Exported cells must describe the protected final atlas too.
        for f in frames:
            c,r=divmod(f-1,meta['rows'])
            atlas.crop((c*128,r*128,(c+1)*128,(r+1)*128)).save(args.output/f'frames/{f:04}.png')
    assert np.array_equal(before[:,:,3],after[:,:,3])
    for f in range(1,meta['columns']*meta['rows']+1):
        if f in frames:continue
        c,r=divmod(f-1,meta['rows']);assert np.array_equal(before[r*128:(r+1)*128,c*128:(c+1)*128],after[r*128:(r+1)*128,c*128:(c+1)*128])
    atlas.save(args.output/'town.png')
    report=dict(replaced_frames=sorted(frames),world_occurrences=sum(uses.values()),
                alpha_exact=True,unselected_rgba_exact=True,shared_frame_phases_validated=True,
                edge_policy='New RGB allowed; repeated material phase and native alpha preserved',
                material_mapping='Inverse native isometric projection, periodic world X/Z',
                per_instance_overrides=0,protected_authored_pixels=protected_count,installed=False)
    (args.output/'validation.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='replaced_frames'}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('project','plan','minimum','sol','dirt','grass','output'):p.add_argument(name,type=Path)
    p.add_argument('--initial-atlas',type=Path,help='Preserve already approved buildings/scenery while replacing selected ground')
    p.add_argument('--protected-pixels',type=Path,help='Hash-bound native source-pixel mask for painted object bases/repairs')
    args=p.parse_args();build(args)
