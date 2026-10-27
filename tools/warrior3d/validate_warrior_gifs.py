"""python SCRIPT GIF_COLLECTION_DIRECTORY
Decode all GIF frames, verify total action durations and test the ZIP archive.
"""
import json,zipfile,sys
from pathlib import Path
from PIL import Image
out=Path(sys.argv[1]).resolve();manifest=json.loads((out/'inventory.json').read_text());records=[]
for group in manifest['families']:
 for entry in group['actions']:
  p=out/entry['gif'];im=Image.open(p);duration=0
  for i in range(im.n_frames):im.seek(i);im.load();duration+=im.info.get('duration',0)
  assert duration==entry['frame_count']*entry['duration_ms'],(p,duration,entry);assert im.size==(1280,714);records.append({'gif':entry['gif'],'encoded_frames':im.n_frames,'source_frames':entry['frame_count'],'duration_ms':duration})
 p=out/group['overview'];im=Image.open(p);duration=0
 for i in range(im.n_frames):im.seek(i);im.load();duration+=im.info.get('duration',0)
 assert duration==4000;records.append({'gif':group['overview'],'encoded_frames':im.n_frames,'duration_ms':duration})
archive=out.parent/(out.name+'.zip')
with zipfile.ZipFile(archive) as z:
 assert len([n for n in z.namelist() if n.endswith('.gif')])==94 and z.testzip() is None
report={'action_gifs':85,'overview_gifs':9,'zip_gifs':94,'archive_bytes':archive.stat().st_size,'all_gif_frames_decoded':True,'all_durations_preserved':True,'archive_integrity_verified':True,'files':records};out.with_name(out.name+'-validation.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='files'}))
