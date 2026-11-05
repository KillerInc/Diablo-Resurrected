"""Compile completed medium renders alongside the running private render batch."""
import argparse,json,time,shutil,sys,os
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pack_gpu_sprites import pack
from gpu_index import consolidate
from hd_layouts import read_table,write_table
from install_layout_table import sha
p=argparse.ArgumentParser(description=__doc__)
for name in ['plan','baseline_pack','baseline_custom','game_hd','encoder','work']:p.add_argument(name,type=Path)
a=p.parse_args();plan=json.loads(a.plan.read_text());work=a.work.resolve();work.mkdir(parents=True,exist_ok=True);hd=work/'source-HD';custom=work/'custom-4x';compiled=work/'compiled';baseline=json.loads((a.baseline_pack/'gpu-pack-proof.json').read_text());proof={r:v for r,v in baseline.items() if not r.startswith('plrgfx/warrior/wm')};rows=read_table(a.game_hd/'layouts.csv');done={};log=work/'native-grid.log';Image.MAX_IMAGE_PIXELS=None
# Preserve all light/heavy source identities and compiled pages. No installed
# artwork is written by this staging tool; only completed medium renders change.
for rel,record in proof.items():
 target=hd/rel;target.parent.mkdir(parents=True,exist_ok=True)
 if not target.exists():shutil.copy2(a.game_hd/rel,target)
 assert sha(target)==record['source_sha256']
 source=a.baseline_custom/'HD'/rel
 if source.exists():
  target=custom/'HD'/rel;target.parent.mkdir(parents=True,exist_ok=True)
  if not target.exists():shutil.copy2(source,target)
 meta=Path(rel).with_suffix('.gpus');src=a.baseline_pack/'HD'/meta;dst=compiled/'HD'/meta;dst.parent.mkdir(parents=True,exist_ok=True)
 if not dst.exists():shutil.copy2(src,dst)
 for page in src.parent.glob(src.stem+'.p*.bc7'):
  dest=dst.parent/page.name
  if not dest.exists():shutil.copy2(page,dest)
baseproof=compiled/'gpu-pack-base-proof.json';baseproof.parent.mkdir(parents=True,exist_ok=True);baseproof.write_text(json.dumps(proof,indent=2));write_table(hd/'layouts.csv',rows)
# The loader's frame counts are unchanged even when a target animation has
# a different number of rows from the light donor.
lines=[]
for rel,r in baseline.items():lines.append(f'Loaded HD sheet: hd/{rel} (native, {r["columns"]} directions, {r["rows"]} frames, native density)')
log.write_text('\n'.join(lines));print('Preserved 170 light/heavy sources and GPU records',flush=True)
last_progress=time.time()
while len(done)<len(plan['jobs']):
 for job in plan['jobs']:
  name=job['sheet'];validation=Path(job['root'])/'output/validation.json'
  if name in done or not validation.exists():continue
  result=json.loads(validation.read_text());assert result['frame_count']==job['rows'] and result['direction_count']==8
  output=validation.parent/(name+'.png');assert sha(output).lower()==result['sheet_sha256'].lower();rel=f'plrgfx/warrior/{name[:3]}/{name}.png';target=hd/rel;target.parent.mkdir(parents=True,exist_ok=True)
  if not target.exists():shutil.copy2(output,target)
  assert sha(target)==sha(output)
  layout=(output.with_name(output.name+'.layout')).read_text().strip();rows[rel]=layout
  target=custom/'HD'/rel;target.parent.mkdir(parents=True,exist_ok=True)
  if not target.exists():
   with Image.open(output) as original:
    original=original.convert('RGBA');w,h=original.size;cw,ch=w//8,h//job['rows'];assert cw%2==ch%2==0
    scaled=Image.new('RGBA',(w//2,h//2))
    for d in range(8):
     for r in range(job['rows']):scaled.paste(original.crop((d*cw,r*ch,(d+1)*cw,(r+1)*ch)).resize((cw//2,ch//2),Image.Resampling.LANCZOS),(d*cw//2,r*ch//2))
    scaled.save(target)
  pack(hd,custom,log,compiled,a.encoder,only=[name],proof_name='gpu-pack-medium-proof.json')
  done[name]={'source':str(output),'size':result['size'],'sha256':sha(output),'layout':layout,'rows':job['rows']};(work/'medium-art-manifest.json').write_text(json.dumps({'version':'medium-v1','model_sha256':plan['model_sha256'],'sheets':done},indent=2));last_progress=time.time();print('MEDIUM_COMPILED',len(done),len(plan['jobs']),name,flush=True)
 if len(done)<len(plan['jobs']):
  tail=(Path(plan['work'])/'render.log').read_bytes()[-16000:].decode(errors='replace')
  if 'Traceback (most recent call last)' in tail or 'Error: Python:' in tail:raise RuntimeError('Renderer failed; compiled progress is retained')
  if time.time()-last_progress>1800:raise RuntimeError('No completed render for 30 minutes; inspect renderer before resuming')
  time.sleep(10)
write_table(hd/'layouts.csv',rows);write_table(compiled/'HD/layouts.csv',rows);proof.update(json.loads((compiled/'gpu-pack-medium-proof.json').read_text()));(compiled/'gpu-pack-proof.json').write_text(json.dumps(proof,indent=2));consolidate(compiled/'HD');print('MEDIUM_COMPILE_DONE',len(done),flush=True)
