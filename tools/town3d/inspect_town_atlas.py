"""Record the existing town atlas contract before any 3D-to-BC7 bake.

Usage: script game-HD extracted-town.min output.json
This only reads installed graphics. It does not create or install BC7 pages.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
from collections import defaultdict

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from gpu_index import read_index


def inspect(hd, minimum, output):
    hd,minimum,output=map(Path,(hd,minimum,output))
    key='levels/towndata/town.png'
    lines=read_index(hd/'sprites.gpus')[key]
    _,density,columns,rows,width,height,pages=lines[0].split()
    density,columns,rows,width,height,pages=map(int,(density,columns,rows,width,height,pages))
    references=defaultdict(list)
    raw=minimum.read_bytes()
    assert len(raw)%32==0
    for piece in range(len(raw)//32):
        values=struct.unpack_from('<16H',raw,piece*32)
        for block in range(16):
            value=values[14+(block&1)-(block&14)]
            frame=value&4095
            if frame:
                assert frame<=columns*rows
                references[frame].append(dict(piece=piece,half=block&1,
                                              vertical_pair=block//2,type=(value>>12)&7))
    records=[]
    for frame in range(1,columns*rows+1):
        col,row=divmod(frame-1,rows)
        records.append(dict(source_frame=frame,column=col,row=row,
                            gpu_frame=lines[pages+frame],uses=references.get(frame,[])))
    metadata=dict(status='contract recorded; replacement not baked or installed',
        resource=key,density=density,columns=columns,rows=rows,
        logical_cell=[width,height],render_cell=[width*density,height*density],
        native_piece_count=len(raw)//32,referenced_source_frames=len(references),
        shared_frames=sum(len(v)>1 for v in references.values()),
        pages=[dict(path=str(Path(key).parent/line.split()[0]),
                    dimensions=list(map(int,line.split()[1:])),
                    sha256=hashlib.sha256((hd/Path(key).parent/line.split()[0]).read_bytes()).hexdigest())
               for line in lines[1:pages+1]],
        original_index_sha256=hashlib.sha256((hd/'sprites.gpus').read_bytes()).hexdigest(),
        original_layouts_sha256=hashlib.sha256((hd/'layouts.csv').read_bytes()).hexdigest(),
        frames=records,
        bake_requirements=[
            'Use the calibrated native orthographic projection at density 4.',
            'Preserve native alpha, floor/foliage separation and source frame identities.',
            'Compare every repeated source frame across all world uses before assigning a new image.',
            'Report conflicting instance bakes; never silently overwrite a shared frame.',
            'Keep dungeon records, layout anchors, gameplay and scene traversal unchanged.',
            'Encode a private candidate pack and validate GPU loading and in-game occlusion before installation.'])
    output.write_text(json.dumps(metadata,indent=2))
    print(json.dumps({k:metadata[k] for k in ('resource','density','columns','rows','native_piece_count',
                                           'referenced_source_frames','shared_frames')}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for field in ('hd','minimum','output'):p.add_argument(field,type=Path)
    args=p.parse_args();inspect(args.hd,args.minimum,args.output)
