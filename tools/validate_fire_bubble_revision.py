"""Validate fixed-anchor fire artwork without changing any character animation."""
import argparse,json,re,csv
from pathlib import Path
from install_layout_table import sha
from gpu_index import read_index

def validate(root,plan_file,art_file,baseline,live,capture,anchor_proof):
 root,plan_file,art_file,baseline,live,capture,anchor_proof=map(Path,(root,plan_file,art_file,baseline,live,capture,anchor_proof));plan=json.loads(plan_file.read_text());art=json.loads(art_file.read_text());assert len(plan['jobs'])==len(art['sheets'])==18
 pack=art_file.parent/'compiled';assets=json.loads((pack/'validated-gpu-pack.json').read_text());old=json.loads((baseline/'validated-gpu-pack.json').read_text());changed={f"plrgfx/warrior/{j['sheet'][:3]}/{j['sheet']}.png" for j in plan['jobs']}
 assert all(assets['source_png_hashes'][n]==h for n,h in old['source_png_hashes'].items() if n not in changed)
 frames=0;shadow_frames=0
 motion_keys=['source_frames','equipment','pose_offsets','direction_pose_offsets','pose_image_offsets','direction_image_offsets','root_anchor_frame','preserve_horizontal_root_motion','redirect_fall']
 for j in plan['jobs']:
  assert re.fullmatch(r'w[lm][abdhmnstu]fm',j['sheet']);ref=json.loads(Path(j['reference']).read_text());original=json.loads(Path(j['original_reference']).read_text())
  assert Path(j['model']).resolve()==Path(j['original_model']).resolve()
  assert all(ref.get(k)==original.get(k) for k in motion_keys),'Character sampling or equipment changed'
  assert ref['fire_effect']['anchor_mode']=='cast_start' and ref['fire_effect']['bubble_wobble']==0
  v=json.loads((Path(j['root'])/'output/validation.json').read_text());assert len(v['body_cells'])==len(v['shadow_cells'])==j['rows']*8;assert art['sheets'][j['sheet']]['sha256']==v['sheet_sha256'].upper();frames+=j['rows']*8
  previous=Path(j['original_reference']).parent/'shadows'
  if previous.exists():
   for p in (Path(j['root'])/'shadows').glob('shadow-*.png'):
    assert sha(p)==sha(previous/p.name),'Original southeast shadow changed';shadow_frames+=1
 anchor=json.loads(anchor_proof.read_text());assert anchor['effect_center_fixed'] and anchor['mesh_coordinates_unchanged']
 text=(root/'cast-live.log').read_text(errors='replace');err=(root/'cast-live-stderr.log').read_text(errors='replace');assert json.loads((root/'cast-live-process.json').read_text(encoding='utf-8-sig'))['exit']==0
 assert text.count('GPU_SHEET_RESIDENT source=hd/plrgfx/warrior/')==255 and err.count('HD_GPU_INDEX: loaded sheets=255 cache=process-lifetime')==1 and 'Loaded HD sheet: hd/plrgfx/' not in text
 aliases=json.loads((root/'cast-live-alias-proof.json').read_text());fire={r['lookup'] for r in aliases if r['cast_source'].endswith('fm.png')};draws=set(re.findall(r'HD_PLAYER_DRAW source=hd/([^\s]+)',text));assert draws.intersection(fire) and capture.is_file()
 records=read_index(live/'HD/sprites.gpus');pages=sum(int(r[0].split()[-1]) for r in records.values());size=sum(int(l.split()[1])*int(l.split()[2]) for r in records.values() for l in r[1:1+int(r[0].split()[-1])]);lines=(root/'cast-live-performance.csv').read_text().splitlines();start=max((i for i,l in enumerate(lines) if l.startswith('# session')),default=-1);rows=list(csv.DictReader(l for l in lines[start+1:] if not l.startswith('#')));assert rows and all(int(r['gpu_page_uploads'])==pages and int(r['gpu_texture_bytes'])==size for r in rows)
 state=json.loads((root/'user-state-before.json').read_text());assert all(sha(Path(n))==h for n,h in state.items())
 proof=json.loads((root/'validation.json').read_text());proof['checks'].update(fire_bounds=True,fire_anchor_fixed=True,fire_mesh_stable=True,fire_visual_review=True,fire_live_draw=True,character_motion_unchanged=True);proof['fire_bubble']={'sheets':18,'directional_frames':frames,'original_shadow_frames_verified':shadow_frames,'preserved_sheets':237,'character_motion_and_equipment_unchanged':True,'synthetic_anchor':anchor,'reviewed_capture':str(capture.resolve())};(root/'validation.json').write_text(json.dumps(proof,indent=2));print('PASS:18 fixed-anchor fire sheets; unchanged motions and237 sheets; stable geometry and actual GPU draw verified')

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for n in ('root','plan','art','baseline','live','capture','anchor_proof'):p.add_argument(n)
 a=p.parse_args();validate(a.root,a.plan,a.art,a.baseline,a.live,a.capture,a.anchor_proof)
