"""Audit an entire private town candidate, not only selected beauty renders.

Arguments: authoring registrations references renders atlas-contract output
Outputs contain private artwork/coordinates and must stay outside Git.
This does not encode or install game assets.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


def compare(reference, rendered):
    a,b=np.asarray(reference.convert('RGBA')),np.asarray(rendered.convert('RGBA'))
    if a.shape!=b.shape:raise ValueError('Comparison canvases differ')
    wanted,actual=a[:,:,3]>=128,b[:,:,3]>=128
    intersection=wanted&actual
    return dict(reference_pixels=int(wanted.sum()),rendered_pixels=int(actual.sum()),
                missing_pixels=int((wanted&~actual).sum()),
                extra_pixels=int((actual&~wanted).sum()),
                coverage_iou=float(intersection.sum()/max(1,(wanted|actual).sum())),
                colour_mae_overlap=float(np.abs(a[:,:,:3].astype(float)-b[:,:,:3])[intersection].mean())
                if intersection.any() else None)


def fragment_contexts(contract, pieces):
    """Retain every native MIN use; never select a last writer for shared art."""
    uses=[]
    for frame in contract['frames']:
        occurrences=[]
        for use in frame['uses']:
            for x,z in pieces.get(use['piece'],[]):
                occurrences.append(dict(x=x,z=z,piece=use['piece'],half=use['half'],
                                        vertical_pair=use['vertical_pair'],type=use['type'],
                                        world_rect=[32*(x-z)-32+use['half']*32,
                                                    16*(x+z)-use['vertical_pair']*32-31,32,32]))
        uses.append(dict(source_frame=frame['source_frame'],atlas_column=frame['column'],
                         atlas_row=frame['row'],min_uses=frame['uses'],world_uses=occurrences,
                         requires_shared_bake_comparison=len(occurrences)>1))
    return uses


def audit(args):
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
    scene=json.loads((args.authoring/'scene.json').read_text())
    archive=np.load(args.authoring/'meshes.npz')
    groups=json.loads(args.registrations.read_text())['groups']
    objects=json.loads((args.authoring/'native-object-map.json').read_text())
    cells={}
    for obj in objects:
        for x,z,piece,_ in obj['source_cells']:
            if (x,z) in cells and cells[x,z]!=piece:raise ValueError('Conflicting native source cell')
            cells[x,z]=piece
    pieces=defaultdict(list)
    for (x,z),piece in sorted(cells.items()):pieces[piece].append((x,z))
    contract=json.loads(args.atlas_contract.read_text())
    contexts=fragment_contexts(contract,pieces)
    records=[]
    sheet=Image.new('RGB',(1200,300*len(groups)),(22,22,22));draw=ImageDraw.Draw(sheet)
    for row,group in enumerate(groups):
        identity=group['ids'][0]
        ref=Image.open(args.references/(identity+'-vanilla.png')).convert('RGBA')
        render=Image.open(args.renders/(identity+'-new.png')).convert('RGBA')
        metrics=compare(ref,render)
        entries=[m for m in scene['meshes'] if m.get('building') in group['ids']]
        metrics.update(ids=group['ids'],triangles=sum(len(archive[m['key']])//3 for m in entries),
                       canvas=list(ref.size),native_origin=group['comparison_origin'])
        records.append(metrics)
        for col,(im,label) in enumerate([(ref,'Vanilla reference'),(render,'3D candidate')]):
            im=im.copy();im.thumbnail((580,265))
            sheet.paste(im,(col*600+(600-im.width)//2,row*300+28),im)
            draw.text((col*600+12,row*300+8),identity+' - '+label,fill='white')
    sheet.save(output/'all-buildings.png')
    present={m.get('building') for m in scene['meshes'] if m.get('building')}
    expected={b['id'] for b in scene['buildings']}
    assert present==expected and len(expected)==14
    report=dict(building_count=len(present),comparison_groups=records,native_grid=scene['grid'],
                static_object_count=len(objects),native_source_cells=len(cells),
                triangles=sum(len(archive[k])//3 for k in archive.files),
                atlas_referenced_frames=contract['referenced_source_frames'],
                atlas_frames_with_multiple_world_uses=sum(c['requires_shared_bake_comparison'] for c in contexts),
                atlas_world_uses=sum(len(c['world_uses']) for c in contexts),
                production_ready=False,
                outstanding=['Geometry still differs from reference silhouettes; see per-building missing/extra pixels.',
                             'Native facade references include scenery fringe, not architecture-only segmentation.',
                             'Ground/scenery retains native relief geometry; not fully modelled all-angle scenery.',
                             'Every repeated fragment needs separate visibility-aware bake comparison before encoding.',
                             'No candidate atlas has passed runtime lighting, occlusion and traversal tests.'])
    (output/'completion-report.json').write_text(json.dumps(report,indent=2))
    (output/'fragment-bake-plan.json').write_text(json.dumps(dict(resource=contract['resource'],
         density=contract['density'],records=contexts,
         rule='Reject differing instance pixels for a shared frame; never overwrite another occurrence.'),separators=(',',':')))
    print(json.dumps({k:report[k] for k in ('building_count','static_object_count','native_source_cells',
        'triangles','atlas_frames_with_multiple_world_uses','atlas_world_uses','production_ready')}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('authoring','registrations','references','renders','atlas_contract','output'):
        p.add_argument(name,type=Path)
    audit(p.parse_args())
