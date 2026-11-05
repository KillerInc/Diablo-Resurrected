"""Audit canonical art coverage through native painter-order visibility.

Track source addresses rather than counting a partly painted frame as finished.
The stripe owner canvas is bounded; no full-town RGBA allocation is required.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS=None


def source_owner_stripes(layers,frames,width,height,cell,stripe=128):
    buckets=defaultdict(list)
    for l in layers:
        for band in range(l['y']//stripe,(l['y']+cell-1)//stripe+1):buckets[band].append(l)
    yy,xx=np.mgrid[:cell,:cell]
    for top in range(0,height,stripe):
        owner=np.zeros((min(stripe,height-top),width),dtype=np.uint32)
        for l in buckets[top//stripe]:
            x,y=l['x'],l['y']-top
            x0,y0=max(0,x),max(0,y);x1,y1=min(width,x+cell),min(owner.shape[0],y+cell)
            if x1<=x0 or y1<=y0:continue
            sx,sy=x0-x,y0-y
            a=np.asarray(frames[l['frame']])[sy:sy+y1-y0,sx:sx+x1-x0,3]
            addresses=1+l['frame']*cell*cell+yy[sy:sy+y1-y0,sx:sx+x1-x0]*cell+xx[sy:sy+y1-y0,sx:sx+x1-x0]
            dest=owner[y0:y1,x0:x1];dest[a>0]=0;dest[a==255]=addresses[a==255]
        yield top,owner


def visible_sources(layers,frames,width,height,cell,frame_count,stripe=128):
    visible=np.zeros((frame_count+1)*cell*cell,dtype=bool)
    for _,owner in source_owner_stripes(layers,frames,width,height,cell,stripe):
        ids=owner[owner>0].astype(np.int64)-1;visible[ids]=True
    return visible


def build(args):
    if args.output.exists():raise ValueError('Use a new audit directory')
    meta=json.loads((args.project/'project.json').read_text());cell=meta['cell'];count=meta['columns']*meta['rows']
    atlas=Image.open(args.project/'base-atlas.png').convert('RGBA');frames={}
    for f in {l['frame'] for l in meta['layers']}:
        c,r=divmod(f-1,meta['rows']);frames[f]=atlas.crop((c*cell,r*cell,(c+1)*cell,(r+1)*cell))
    target=visible_sources(meta['layers'],frames,*meta['canvas'],cell,count)
    authored=np.load(args.coverage)['authored'].copy()
    if target.shape!=authored.shape:raise ValueError('Coverage geometry changed')
    retained_black=[]
    for f,tile in frames.items():
        data=np.asarray(tile);opaque=data[:,:,3]==255
        if opaque.any() and not data[opaque,:3].any():
            retained_black.append(f);authored[f*cell*cell:(f+1)*cell*cell]|=opaque.ravel()
    if args.ground_plan:
        for f in json.loads(args.ground_plan.read_text())['frames']:
            c,r=divmod(f-1,meta['rows']);tile=np.asarray(atlas.crop((c*cell,r*cell,(c+1)*cell,(r+1)*cell)))
            authored[f*cell*cell:(f+1)*cell*cell]|=tile[:,:,3].ravel()==255
    missing=target&~authored
    pending=missing.reshape(count+1,cell*cell).sum(axis=1)
    report=dict(visible_source_pixels=int(target.sum()),authored_visible_source_pixels=int((target&authored).sum()),
                pending_visible_source_pixels=int(missing.sum()),
                pending_frames={str(f):int(pending[f]) for f in np.flatnonzero(pending)},
                retained_constant_black_frames=retained_black,
                complete=not missing.any(),scope='base town map; audit alternate states separately')
    args.output.mkdir(parents=True);np.savez_compressed(args.output/'visibility.npz',target=target,missing=missing)
    (args.output/'audit.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='pending_frames'}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('project','coverage','output'):p.add_argument(name,type=Path)
    p.add_argument('--ground-plan',type=Path)
    build(p.parse_args())
