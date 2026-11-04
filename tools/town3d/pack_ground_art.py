"""Reassemble private AI-painted ground pages into canonical native frames.

This is a compatibility packing pass: retain native alpha and an exact border
rim, retain source-local material colour, and never create per-instance art.
Inputs: source project, page-plan JSON, town.min, town.sol, output NEW directory.
Painted pages must be named painted-page-NN.png beside the page-plan JSON.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter


def inset_distance(alpha):
    mask=Image.fromarray(np.where(alpha>0,255,0).astype(np.uint8))
    padded=Image.new('L',(mask.width+2,mask.height+2));padded.paste(mask,(1,1))
    result=np.zeros(alpha.shape,dtype=np.float32)
    for _ in range(min(alpha.shape)//2+1):
        active=np.asarray(padded)[1:-1,1:-1]>0
        if not active.any():break
        result+=active
        padded=padded.filter(ImageFilter.MinFilter(3))
    return result


def compatible_frame(original,painted,border=8,feather=8):
    if original.size!=painted.size:raise ValueError('Frame sizes differ')
    source=np.asarray(original.convert('RGBA'));candidate=np.asarray(painted.convert('RGBA'))
    distance=inset_distance(source[:,:,3])
    weight=np.clip((distance-border)/max(1,feather),0,1)
    weight[candidate[:,:,3]<240]=0
    valid=weight>0
    if not valid.any():raise ValueError('Paint does not cover the protected tile interior')
    # Preserve native material transitions locally, not just the tile average.
    # A per-tile average can still leave a bright island inside a dark locked
    # rim. Transfer authored microdetail around the original low-frequency
    # colour field so reusable edges do not become a network of dark borders.
    a=source[:,:,:3].astype(np.float32);b=candidate[:,:,:3].astype(np.float32)
    low=np.asarray(painted.convert('RGB').filter(ImageFilter.GaussianBlur(4))).astype(np.float32)
    detail=(b-low)@np.array([.2126,.7152,.0722],dtype=np.float32)
    base=np.asarray(original.convert('RGB').filter(ImageFilter.GaussianBlur(1.15))).astype(np.float32)
    detail=np.clip(detail,-12,12)
    b=np.clip(base+detail[:,:,None]*.85,0,255)
    result=source.copy();mixed=np.rint(a*(1-weight[:,:,None])+b*weight[:,:,None]).astype(np.uint8)
    result[:,:,:3]=mixed
    protected=(distance<=border)|(source[:,:,3]==0)
    result[protected]=source[protected]
    assert np.array_equal(result[:,:,3],source[:,:,3])
    assert np.array_equal(result[protected],source[protected])
    return Image.fromarray(result),dict(changed_pixels=int(np.any(result!=source,axis=2).sum()),
                                      protected_pixels=int(protected.sum()),
                                      painted_interior_fraction=float(valid.sum()/max(1,(distance>border).sum())))


def ground_only_frames(micros,sol):
    uses=defaultdict(list)
    for piece,values in enumerate(micros):
        for block in range(16):
            frame=int(values[14+(block&1)-(block&14)])&4095
            if frame:uses[frame].append(block<2 and not(sol[piece]&5))
    return {frame for frame,flags in uses.items() if all(flags)}


def pack(args):
    if args.output.exists():raise ValueError('Use a new output directory')
    project=args.project.resolve();plan=json.loads(args.plan.read_text());meta=json.loads((project/'project.json').read_text())
    micros=np.frombuffer(args.minimum.read_bytes(),dtype='<u2').reshape(-1,16);sol=args.sol.read_bytes()
    allowed=ground_only_frames(micros,sol);selected=plan['frames']
    if len(selected)!=len(set(selected)) or not set(selected)<=allowed:raise ValueError('Selection includes duplicate or non-ground frames')
    atlas=Image.open(project/'base-atlas.png').convert('RGBA');cell=meta['cell'];columns=plan['columns'];rows=meta['rows']
    updates={};reports={}
    for number,page in enumerate(plan['pages'],1):
        with Image.open(args.plan.parent/f'painted-page-{number:02}.png') as image:
            if image.width!=image.height:raise ValueError('Painted atlas page is not square')
            image=image.convert('RGBA').resize((plan['page_size'],plan['page_size']),Image.Resampling.LANCZOS)
        for slot,frame in enumerate(page['frames']):
            if frame in updates:raise ValueError('Frame assigned twice')
            x=(slot%columns)*cell;y=(slot//columns)*cell
            painted=image.crop((x,y,x+cell,y+cell))
            original=Image.open(project/f'frames/{frame:04}.png').convert('RGBA')
            updates[frame],reports[str(frame)]=compatible_frame(original,painted,plan['protected_border_pixels'],
                                                               plan.get('feather_pixels',8))
    if set(updates)!=set(selected):raise ValueError('Painted pages do not match frame selection')
    args.output.mkdir(parents=True);(args.output/'frames').mkdir()
    for frame,image in updates.items():
        col,row=divmod(frame-1,rows);atlas.paste(image,(col*cell,row*cell))
        image.save(args.output/f'frames/{frame:04}.png')
    # Check every atlas slot: unselected art and all original alpha stay exact.
    source=Image.open(project/'base-atlas.png').convert('RGBA')
    for frame in range(1,meta['columns']*rows+1):
        col,row=divmod(frame-1,rows);box=(col*cell,row*cell,(col+1)*cell,(row+1)*cell)
        a=np.asarray(source.crop(box));b=np.asarray(atlas.crop(box))
        assert np.array_equal(a[:,:,3],b[:,:,3])
        if frame not in updates:assert np.array_equal(a,b)
    atlas.save(args.output/'town.png')
    report=dict(edited_frames=selected,world_occurrences=sum(l['frame'] in updates for l in meta['layers']),
                alpha_exact=True,unselected_frames_exact=True,original_edge_rim_exact=True,
                frame_ids_and_map_unchanged=True,per_instance_overrides=0,frames=reports,
                minimum_sha256=hashlib.sha256(args.minimum.read_bytes()).hexdigest(),installed=False)
    (args.output/'validation.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k not in ('frames','edited_frames')}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('project','plan','minimum','sol','output'):p.add_argument(name,type=Path)
    args=p.parse_args();pack(args)
