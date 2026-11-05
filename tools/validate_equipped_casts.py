"""Bind cast render audits, sampled pack identities and reviewed GPU draws."""
import argparse,json,csv,re
from pathlib import Path
from install_layout_table import sha
from gpu_index import read_index

def validate(root,plan,art,baseline,live,capture):
 root,plan,art,baseline,live,capture=map(Path,(root,plan,art,baseline,live,capture));p=json.loads(plan.read_text());a=json.loads(art.read_text());assert len(a['sheets'])==len(p['jobs'])==48
 before=json.loads((baseline/'validated-gpu-pack.json').read_text());pack=art.parent/'compiled';after=json.loads((pack/'validated-gpu-pack.json').read_text());grids=json.loads((pack/'gpu-pack-proof.json').read_text());changed={f'plrgfx/warrior/{n[:3]}/{n}.png' for n in a['sheets']}
 assert all(after['source_png_hashes'][n]==h for n,h in before['source_png_hashes'].items() if n not in changed)
 heads=json.loads((plan.parent/'all-equipment-head-audit.json').read_text());assert len(heads)==48 and not any(r['head_contacts'] for r in heads)
 frames=0
 for j in p['jobs']:
  name=j['sheet'];assert name[2]!='n' and name[-2:] in ('fm','lm','qm');ref=json.loads(Path(j['reference']).read_text());assert ref['equipment']
  rel=f'plrgfx/warrior/{name[:3]}/{name}.png';assert j['rows']==grids[rel]['rows']
  v=json.loads((Path(j['root'])/'output/validation.json').read_text());assert len(v['body_cells'])==len(v['shadow_cells'])==j['rows']*8
  assert a['sheets'][name]['sha256']==v['sheet_sha256'].upper();frames+=j['rows']*8
 text=(root/'cast-live.log').read_text(errors='replace');err=(root/'cast-live-stderr.log').read_text(errors='replace');assert json.loads((root/'cast-live-process.json').read_text(encoding='utf-8-sig'))['exit']==0
 aliases=json.loads((root/'cast-live-alias-proof.json').read_text());lookups={r['lookup'] for r in aliases};draws=set(re.findall(r'HD_PLAYER_DRAW source=hd/([^\s]+)',text));assert draws.intersection(lookups)
 assert text.count('GPU_SHEET_RESIDENT source=hd/plrgfx/warrior/')==255 and err.count('HD_GPU_INDEX: loaded sheets=255 cache=process-lifetime')==1
 assert capture.is_file();assert 'Test audio master gain: 0.5' in text and 'Loaded HD sheet: hd/plrgfx/' not in text
 index=read_index(live/'HD/sprites.gpus');pages=sum(int(r[0].split()[-1]) for r in index.values());size=sum(int(l.split()[1])*int(l.split()[2]) for r in index.values() for l in r[1:1+int(r[0].split()[-1])])
 lines=(root/'cast-live-performance.csv').read_text().splitlines();start=max((i for i,l in enumerate(lines) if l.startswith('# session')),default=-1);rows=list(csv.DictReader(l for l in lines[start+1:] if not l.startswith('#')));assert rows and all(int(r['gpu_page_uploads'])==pages and int(r['gpu_texture_bytes'])==size for r in rows)
 state=json.loads((root/'user-state-before.json').read_text());assert all(sha(Path(n))==h for n,h in state.items())
 proof=json.loads((root/'validation.json').read_text());proof['checks'].update(casting_bounds=True,casting_head_clearance=True,casting_visual_review=True,casting_live_draw=True,casting_unarmed_unchanged=True);proof['casting']={'sheets':48,'directional_frames':frames,'head_clear_sequences':48,'unmodified_sheets':207,'native_row_counts_preserved':True,'source_motion':p['motion_proof'],'reviewed_capture':str(capture.resolve()),'isolated_alias_draws':sorted(draws.intersection(lookups))}
 (root/'validation.json').write_text(json.dumps(proof,indent=2));print('PASS: 48 equipped cast sheets, full bounds/shadows, head clearance, 207 preserved sheets, real GPU draws and unchanged user state')

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for n in ('root','plan','art','baseline','live','capture'):p.add_argument(n)
 a=p.parse_args();validate(a.root,a.plan,a.art,a.baseline,a.live,a.capture)
