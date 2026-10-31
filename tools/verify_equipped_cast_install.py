"""Verify the installed casting revision and isolated installed-executable replay."""
import argparse,json,re,csv
from pathlib import Path
from install_layout_table import sha

def verify(root,pack,baseline,game,state):
 root,pack,baseline,game,state=map(Path,(root,pack,baseline,game,state));assets=json.loads((pack/'validated-gpu-pack.json').read_text());old=json.loads((baseline/'validated-gpu-pack.json').read_text());hd=game/'HD'
 proof=json.loads((root/'validation.json').read_text());assert sha(game/'Diablo Reincarnated.exe')==proof['executable_sha256']
 for n,h in assets['files'].items():assert sha(hd/n)==h
 for n,h in assets['source_png_hashes'].items():assert sha(hd/n)==h
 fire=proof['checks'].get('fire_anchor_fixed',False);spells=proof['checks'].get('lightning_geometry_held',False);expected=36 if spells else (18 if fire else 48)
 pattern=r'plrgfx/warrior/w[lm][abdhmnstu]/w[lm][abdhmnstu](fm|lm)\.png' if spells else (r'plrgfx/warrior/w[lm][abdhmnstu]/w[lm][abdhmnstu]fm\.png' if fire else r'plrgfx/warrior/w[lm][abdhmstu]/w[lm][abdhmstu](fm|lm|qm)\.png')
 if proof['checks'].get('shield_bounds',False):
  expected=30;pattern=r'plrgfx/warrior/wm[dhu]/wm[dhu](as|at|aw|bl|fm|ht|lm|qm|st|wl)\.png'
 if proof['checks'].get('heavy_bounds',False):
  expected=85;pattern=r'plrgfx/warrior/wh[a-z]/wh[a-z](as|at|aw|bl|dt|fm|ht|lm|qm|st|wl)\.png'
 if proof['checks'].get('medium_visual_review',False):
  expected=85;pattern=r'plrgfx/warrior/wm[a-z]/wm[a-z](as|at|aw|bl|dt|fm|ht|lm|qm|st|wl)\.png'
 changed={n for n,h in old['source_png_hashes'].items() if assets['source_png_hashes'][n]!=h};assert len(changed)==expected and all(re.fullmatch(pattern,n) for n in changed)
 assert sha(hd/'layouts.csv')==assets['layout_sha256'] and not list(hd.rglob('*.layout')) and len(list(hd.rglob('*.gpus')))==1
 assert all(sha(Path(n))==h for n,h in json.loads(state.read_text()).items())
 text=(root/'installed-smoke.log').read_text(errors='replace');err=(root/'installed-smoke-stderr.log').read_text(errors='replace');process=json.loads((root/'installed-smoke-process.json').read_text(encoding='utf-8-sig'));assert process['exit']==0
 assert 'Same outcome as initial run' in text and 'Different outcome' not in text
 assert text.count('GPU_SHEET_RESIDENT source=hd/plrgfx/warrior/')==255 and 'Loaded HD sheet: hd/plrgfx/' not in text
 assert err.count('HD_GPU_INDEX: loaded sheets=255 cache=process-lifetime')==1 and 'Test audio master gain: 0.5' in text
 end=re.search(r'HD_PLAYER_PRELOAD[^\n]+',text).end();assert 'GPU_SHEET_RESIDENT' not in text[end:]
 lines=(root/'installed-smoke-performance.csv').read_text().splitlines();start=max((i for i,l in enumerate(lines) if l.startswith('# session')),default=-1);rows=list(csv.DictReader(l for l in lines[start+1:] if not l.startswith('#')));assert rows and all(int(r['gpu_page_uploads'])==assets['pages'] and int(r['gpu_texture_bytes'])==assets['texture_bytes'] for r in rows)
 result={'installed_sheets':expected,'preserved_sheets':255-expected,'all_gpu_hashes_verified':True,'all_png_hashes_verified':True,'user_state_unchanged':True,'executable_unchanged':True,'reference_outcome_same':True,'gpu_sheets':255,'gpu_pages':assets['pages'],'gpu_texture_bytes':assets['texture_bytes'],'cpu_player_png_decodes':0,'warm_gpu_uploads':0,'runtime_indexes':1,'individual_layouts':0}
 (root/'installed-smoke-proof.json').write_text(json.dumps(result,indent=2));print('PASS: installed',expected,'preserved',255-expected,'user state and executable unchanged, reference replay and warm GPU cache verified')

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for n in ('root','pack','baseline','game','state'):p.add_argument(n)
 a=p.parse_args();verify(a.root,a.pack,a.baseline,a.game,a.state)
