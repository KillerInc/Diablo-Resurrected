"""Compare supplied building geometry with private native town coverage.

Fit horizontal scale, height scale and ground-plane translation as a candidate.
The ground stays at zero; UVs/source files are untouched. This fits the native
coverage envelope, not unseen architecture or pixel-perfect colour fidelity.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from convert_scene import native_facade, read_model

GROUPS = [('tavern-main','tavern-wing'),('smithy-house','smithy-forge')]


def project(points):
    return np.stack((32*(points[:,0]-points[:,2]),
                     16*(points[:,0]+points[:,2])-32*points[:,1]),axis=1)


def apply_registration(points, record):
    result=points.copy()
    pivot=np.asarray(record['pivot'])
    result[:,[0,2]]=pivot[[0,2]]+(result[:,[0,2]]-pivot[[0,2]])*record['horizontal_scale']
    result[:,1]*=record['height_scale']
    result+=np.asarray(record['translation'])
    return result


def fit(points, target, pivot):
    before=project(points)
    horizontal=(target[2]-target[0])/(before[:,0].max()-before[:,0].min())
    assert .25<horizontal<4
    record=dict(pivot=list(pivot),horizontal_scale=float(horizontal),height_scale=1.,translation=[0.,0.,0.])
    wanted=target[3]-target[1]
    lo,hi=.05,4.
    for _ in range(48):
        record['height_scale']=(lo+hi)/2
        p=project(apply_registration(points,record))
        if np.ptp(p[:,1])<wanted:lo=record['height_scale']
        else:hi=record['height_scale']
    record['height_scale']=(lo+hi)/2
    p=project(apply_registration(points,record))
    delta_x=(target[0]+target[2]-p[:,0].min()-p[:,0].max())/2
    delta_y=target[3]-p[:,1].max()
    record['translation']=[float((delta_x/32+delta_y/16)/2),0.,float((delta_y/16-delta_x/32)/2)]
    return record


def envelope(points):
    p=project(points)
    return [float(p[:,0].min()),float(p[:,1].min()),float(p[:,0].max()),float(p[:,1].max())]


def mask(points, origin, size):
    image=Image.new('L',size)
    draw=ImageDraw.Draw(image)
    p=project(points)-np.asarray(origin)
    for triangle in p.reshape(-1,3,2):draw.polygon([tuple(v) for v in triangle],fill=255)
    return image


def coverage_iou(a,b):
    x,y=np.asarray(a)>0,np.asarray(b)>0
    union=np.count_nonzero(x|y)
    return float(np.count_nonzero(x&y)/union) if union else 1.


def register(args):
    args.output.mkdir(parents=True,exist_ok=True)
    scene=json.loads((args.converted/'scene.json').read_text())
    meshes=np.load(args.converted/'meshes.npz')
    native_objects=json.loads((args.converted/'native-object-map.json').read_text())
    pieces={(x,z):piece for o in native_objects for x,z,piece,special in o['source_cells']}
    micros=np.frombuffer((args.native/'levels/towndata/town.min').read_bytes(),dtype='<u2').reshape(-1,16)
    sol=(args.native/'levels/towndata/town.sol').read_bytes()
    atlas=Image.open(args.atlas).convert('RGBA')
    geometry=defaultdict(list)
    for entry in scene['meshes']:
        if entry.get('building'):geometry[entry['building']].append(meshes[entry['key']][:,:3])
    groups=list(GROUPS)+[(b['id'],) for b in scene['buildings'] if not any(b['id'] in g for g in GROUPS)]
    records=[]
    for group in groups:
        points=np.concatenate([p for identity in group for p in geometry[identity]])
        reference=None
        for identity in group:
            entry=next(b for b in scene['buildings'] if b['id']==identity)
            model=read_model(entry['source'])
            image,pixel_origin,tile=native_facade(model,pieces,micros,sol,atlas)
            world_origin=(32*(tile[0]-tile[1])-pixel_origin[0],16*(tile[0]+tile[1])-pixel_origin[1])
            if reference is None:
                reference=image;origin=world_origin
            else:
                assert origin==world_origin and reference.size==image.size
                reference=Image.alpha_composite(reference,image)
        box=reference.getbbox();assert box
        target=[box[0]+origin[0],box[1]+origin[1],box[2]+origin[0],box[3]+origin[1]]
        pivot=[float(points[:,0].mean()),0.,float(points[:,2].mean())]
        candidate=fit(points,target,pivot)
        repaired=apply_registration(points,candidate)
        # Use a common unclipped canvas for all three masks.
        old_box,new_box=envelope(points),envelope(repaired)
        left=int(min(origin[0],old_box[0],new_box[0]))-8
        top=int(min(origin[1],old_box[1],new_box[1]))-8
        right=int(max(origin[0]+reference.width,old_box[2],new_box[2]))+9
        bottom=int(max(origin[1]+reference.height,old_box[3],new_box[3]))+9
        size=(right-left,bottom-top)
        ref=Image.new('RGBA',size);ref.alpha_composite(reference,(origin[0]-left,origin[1]-top))
        before=mask(points,(left,top),size);after=mask(repaired,(left,top),size)
        old_iou=coverage_iou(before,ref.getchannel('A'));new_iou=coverage_iou(after,ref.getchannel('A'))
        accepted=new_iou>old_iou+.005 and .2<candidate['height_scale']<3
        record=dict(ids=list(group),**candidate,native_coverage_box=target,
                    before_box=old_box,after_box=new_box,
                    comparison_origin=[left,top],comparison_size=list(size),
                    before_coverage_iou=old_iou,after_coverage_iou=new_iou,
                    apply=accepted,status='registration candidate; shape and colour remain under review')
        records.append(record)
        identity=group[0]
        ref.save(args.output/(identity+'-vanilla.png'))
        for label,model_mask in [('before',before),('registered',after)]:
            overlay=Image.new('RGBA',size,(0,0,0,0));overlay.putalpha(model_mask.point(lambda a:round(a*.35)))
            overlay.paste((0,200,255,90),(0,0,size[0],size[1]),model_mask)
            Image.alpha_composite(ref,overlay).save(args.output/(identity+'-'+label+'-coverage.png'))
    (args.output/'registrations.json').write_text(json.dumps(dict(format='d1r.tristram-registration-v1',
        note='Native coverage includes fringe; envelope fit is not complete fidelity approval.',groups=records),indent=2))
    print(json.dumps([dict(ids=r['ids'],horizontal=round(r['horizontal_scale'],3),height=round(r['height_scale'],3),
                           before_iou=round(r['before_coverage_iou'],3),after_iou=round(r['after_coverage_iou'],3),apply=r['apply']) for r in records]))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for field in ('converted','native','atlas','output'):p.add_argument(field,type=Path)
    register(p.parse_args())
