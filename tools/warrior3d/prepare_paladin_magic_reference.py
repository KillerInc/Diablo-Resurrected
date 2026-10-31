"""Prepare original-size QM using the approved grounded twenty-pose cast.

python SCRIPT APPROVED_FM_REFERENCE.json VANILLA_QM.cl2 OUTPUT.json [PARTICLE_SCALE] [MOTION]
"""
import json,struct,sys
from pathlib import Path

source,cl2,destination=map(Path,sys.argv[1:4])
assert len(sys.argv) in (4,5,6)
particle_scale=float(sys.argv[4]) if len(sys.argv)>=5 else 1
motion=sys.argv[5] if len(sys.argv)==6 else 'spiral';assert motion in ('spiral','ground_emitter')
assert 0<particle_scale<=4
assert destination.resolve() not in [source.resolve(),cl2.resolve()]
ref=json.loads(source.read_text());data=cl2.read_bytes()
counts=[struct.unpack_from('<I',data,offset)[0] for offset in struct.unpack_from('<8I',data)]
assert counts==[20]*8,counts
assert ref['sheet']=='wlnfm.png' and ref['rows']==20 and ref['cell']==768
assert ref['source_frames']==list(range(20)) and len(ref['pose_offsets'])==20
ref.update(sheet='wlnqm.png',fire_effect={'style':'magic','seed':1447,'particle_scale':particle_scale,'motion':motion},
           preview_prefix='magic-cast',preview_contact_row=13,
           preview_caption='Native Gizmo Operate | blue magic spiral | release frame 14')
for key in ['render_rows','render_directions']:ref.pop(key,None)
destination.parent.mkdir(parents=True,exist_ok=True);destination.write_text(json.dumps(ref,indent=2))
print('Prepared original twenty-row QM layout; approved body poses unchanged')
