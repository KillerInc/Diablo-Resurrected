"""Derive an original-size LM reference from the approved grounded cast.

python SCRIPT APPROVED_FM_REFERENCE.json VANILLA_LM.cl2 OUTPUT.json
The original LM stores 21 poses; warrior gameplay plays 20 and releases at 14.
The spare last row repeats idle without stretching the approved twenty poses.
"""
import json,struct,sys
from pathlib import Path

source,cl2,destination=map(Path,sys.argv[1:4])
assert destination.resolve() not in [source.resolve(),cl2.resolve()]
ref=json.loads(source.read_text());data=cl2.read_bytes()
counts=[struct.unpack_from('<I',data,offset)[0] for offset in struct.unpack_from('<8I',data)]
assert counts==[21]*8,counts
assert ref['sheet']=='wlnfm.png' and ref['rows']==20 and ref['cell']==768
assert ref['source_frames']==list(range(20)) and len(ref['pose_offsets'])==20
ref.update(sheet='wlnlm.png',rows=21,source_frames=list(range(20))+[19],
           pose_offsets=ref['pose_offsets']+[ref['pose_offsets'][-1]],
           fire_effect={'style':'lightning','seed':811},
           preview_prefix='lightning-cast',preview_contact_row=13,
           preview_caption='Native Gizmo Operate | lightning cast | release frame 14')
for key in ['render_rows','render_directions']:ref.pop(key,None)
destination.parent.mkdir(parents=True,exist_ok=True)
destination.write_text(json.dumps(ref,indent=2))
print('Prepared original 21-row LM layout; twenty gameplay poses unchanged')
