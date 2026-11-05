"""Reconcile painted material joins through canonical source-address constraints.

Only discontinuities at fragment boundaries whose ORIGINAL coarse colours agree
are eligible. Native alpha/map/layout are immutable. Bounded colour corrections
feather inside existing cells; this is packing reconciliation, not new artwork.
"""
import argparse
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image

from audit_town_art import source_owner_stripes
from replace_ground_materials import source_field

Image.MAX_IMAGE_PIXELS=None


def matching_edges(a,b,field,rgb,step,reference_tolerance=6,jump=18):
    a=a.ravel().astype(np.int64)-1;b=b.ravel().astype(np.int64)-1
    valid=(a>=0)&(b>=0)&(b!=a+step)
    a,b=a[valid],b[valid]
    if not len(a):return np.empty((0,2),dtype=np.int64)
    original=np.max(np.abs(field[a].astype(np.int16)-field[b].astype(np.int16)),axis=1)
    delta=np.max(np.abs(rgb[a].astype(np.int16)-rgb[b].astype(np.int16)),axis=1)
    keep=(original<=reference_tolerance)&(delta>=jump)&field[a].any(axis=1)&field[b].any(axis=1)
    return np.unique(np.sort(np.stack((a[keep],b[keep]),axis=1),axis=1),axis=0)


def balanced_targets(pairs,rgb,limit=24):
    nodes,inverse=np.unique(pairs,return_inverse=True);edge=inverse.reshape(-1,2)
    values=rgb[nodes].astype(np.float32)
    degree=np.bincount(edge.ravel(),minlength=len(nodes))+1
    for _ in range(12):
        sums=values.copy()
        for channel in range(3):
            sums[:,channel]+=np.bincount(edge[:,0],weights=values[edge[:,1],channel],minlength=len(nodes))
            sums[:,channel]+=np.bincount(edge[:,1],weights=values[edge[:,0],channel],minlength=len(nodes))
        values=sums/degree[:,None]
    original=rgb[nodes].astype(np.float32)
    return nodes,np.clip(values-original,-limit,limit)


def build(args):
    if args.output.exists():raise ValueError('Use a new output directory')
    if args.dependencies:sys.path.insert(0,str(args.dependencies.resolve()))
    import cv2
    meta=json.loads((args.project/'project.json').read_text());cell=meta['cell'];count=meta['columns']*meta['rows']
    original=Image.open(args.project/'base-atlas.png').convert('RGBA');candidate=Image.open(args.atlas).convert('RGBA')
    native=np.asarray(original);after=np.asarray(candidate).copy()
    if native.shape!=after.shape or not np.array_equal(native[:,:,3],after[:,:,3]):raise ValueError('Native coverage changed')
    field=np.zeros(((count+1)*cell*cell,3),dtype=np.uint8);rgb=np.zeros_like(field);frames={}
    for f in range(1,count+1):
        c,r=divmod(f-1,meta['rows']);box=(c*cell,r*cell,(c+1)*cell,(r+1)*cell)
        tile=original.crop(box);field[f*cell*cell:(f+1)*cell*cell]=np.clip(source_field(tile,3),0,255).astype(np.uint8).reshape(-1,3)
        rgb[f*cell*cell:(f+1)*cell*cell]=np.asarray(candidate.crop(box))[:,:,:3].reshape(-1,3)
        frames[f]=tile
    chunks=[];previous=None
    for top,owner in source_owner_stripes(meta['layers'],frames,*meta['canvas'],cell):
        chunks.append(matching_edges(owner[:,:-1],owner[:,1:],field,rgb,1))
        chunks.append(matching_edges(owner[:-1],owner[1:],field,rgb,cell))
        if previous is not None:chunks.append(matching_edges(previous,owner[:1],field,rgb,cell))
        previous=owner[-1:]
    pairs=np.unique(np.concatenate(chunks),axis=0)
    if not len(pairs):raise ValueError('No eligible painted seams found')
    nodes,deltas=balanced_targets(pairs,rgb);changed=0
    for f in np.unique(nodes//(cell*cell)):
        selected=nodes//(cell*cell)==f;pixel=nodes[selected]%(cell*cell)
        correction=np.zeros((cell,cell,3),np.float32);weight=np.zeros((cell,cell),np.float32)
        correction[pixel//cell,pixel%cell]=deltas[selected];weight[pixel//cell,pixel%cell]=1
        w=cv2.GaussianBlur(weight,(0,0),4)
        spread=cv2.GaussianBlur(correction,(0,0),4)/np.maximum(w[:,:,None],1e-8)
        spread*=np.minimum(w[:,:,None]*10,1)
        spread[pixel//cell,pixel%cell]=deltas[selected]
        c,r=divmod(int(f)-1,meta['rows']);tile=after[r*cell:(r+1)*cell,c*cell:(c+1)*cell]
        update=np.rint(np.clip(tile[:,:,:3].astype(np.float32)+spread,0,255)).astype(np.uint8)
        visible=tile[:,:,3]>0;changed+=int(np.any(tile[:,:,:3][visible]!=update[visible],axis=1).sum())
        tile[visible,:3]=update[visible]
    if not np.array_equal(native[:,:,3],after[:,:,3]):raise AssertionError('Alpha changed')
    # Native constant-black opaque cells are masks, not missing material art.
    for f in range(1,count+1):
        c,r=divmod(f-1,meta['rows']);src=native[r*cell:(r+1)*cell,c*cell:(c+1)*cell]
        opaque=src[:,:,3]==255
        if opaque.any() and not src[opaque,:3].any():
            target=after[r*cell:(r+1)*cell,c*cell:(c+1)*cell];target[opaque,:3]=0
    if not np.array_equal(native[native[:,:,3]==0],after[native[:,:,3]==0]):raise AssertionError('Hidden pixels changed')
    args.output.mkdir(parents=True);Image.fromarray(after).save(args.output/'town.png')
    report=dict(eligible_canonical_edge_pairs=len(pairs),edge_source_pixels=len(nodes),changed_source_pixels=changed,
                original_coarse_colour_tolerance=6,minimum_painted_jump=18,maximum_channel_correction=24,
                feather_sigma=4,alpha_exact=True,hidden_rgba_exact=True,installed=False)
    (args.output/'seam-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('project','atlas','output'):p.add_argument(name,type=Path)
    p.add_argument('--dependencies',type=Path);build(p.parse_args())
