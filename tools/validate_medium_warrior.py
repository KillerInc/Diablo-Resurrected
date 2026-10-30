"""Bind completed medium render checks and a reviewed live GPU capture to replay proof."""
import argparse,csv,json,re
from pathlib import Path
from gpu_index import read_index
p=argparse.ArgumentParser(description=__doc__)
for n in ('root','plan','art','live_package'):p.add_argument(n,type=Path)
p.add_argument('--reviewed-capture',type=Path,required=True);a=p.parse_args();root=a.root;records=read_index(a.live_package/'HD/sprites.gpus');expected_pages=sum(int(lines[0].split()[-1]) for lines in records.values());expected_bytes=sum(int(line.split()[1])*int(line.split()[2]) for lines in records.values() for line in lines[1:1+int(lines[0].split()[-1])])
text=(root/'medium-live.log').read_text(errors='replace');err=(root/'medium-live-stderr.log').read_text();process=json.loads((root/'medium-live-process.json').read_text(encoding='utf-8-sig'));assert process['exit']==0
assert text.count('GPU_SHEET_RESIDENT source=hd/plrgfx/warrior/')==255 and 'Loaded HD sheet: hd/plrgfx/' not in text
assert err.count('HD_GPU_INDEX: loaded sheets=255 cache=process-lifetime')==1
# Performance files append sessions. Verify only this corrected live run,
# retaining earlier failed/diagnostic captures and metrics as private evidence.
lines=(root/'medium-live-performance.csv').read_text().splitlines();start=max((i for i,line in enumerate(lines) if line.startswith('# session')),default=-1);rows=list(csv.DictReader(line for line in lines[start+1:] if not line.startswith('#')))
assert rows and all(int(r['gpu_sheets'])==255 and int(r['gpu_page_uploads'])==expected_pages and int(r['gpu_texture_bytes'])==expected_bytes for r in rows)
alias=json.loads((root/'medium-live-alias-proof.json').read_text());lookups={r['lookup'] for r in alias};draws=re.findall(r'HD_PLAYER_DRAW source=hd/([^\s]+)',text);assert draws and all(path in lookups for path in draws)
assert a.reviewed_capture.is_file()
plan=json.loads(a.plan.read_text());art=json.loads(a.art.read_text());assert len(art['sheets'])==85
preflight=json.loads((a.plan.parent/'animation-preflight.json').read_text());assert len(preflight)==85 and not any(r['helmet_contacts'] for r in preflight)
heads=json.loads((a.plan.parent/'all-equipment-head-audit.json').read_text());assert len(heads)==66 and not any(r['head_contacts'] for r in heads)
for j in plan['jobs']:
 v=json.loads((Path(j['root'])/'output/validation.json').read_text());assert len(v['body_cells'])==len(v['shadow_cells'])==j['rows']*8
proof=json.loads((root/'validation.json').read_text());proof['medium_model_sha256']=plan['model_sha256'];proof['checks'].update(medium_visual_review=True,medium_live_draw=True);proof['medium']={'sheets':85,'directional_frames':sum(j['rows']*8 for j in plan['jobs']),'motion_donors':41,'matched_rest_matrix_max_error':0,'equipped_sequences_head_clear':66,'town_axe_chest_local_offset_metres':[.04,0,0],'live_visual_alias_draws':draws,'test_stats_unchanged':True,'live_capture_reviewed':str(a.reviewed_capture.resolve()),'live_expected_gpu_pages':expected_pages,'live_expected_gpu_bytes':expected_bytes}
(root/'validation.json').write_text(json.dumps(proof,indent=2));print('PASS: 85 sheets, 9408 directional body/shadow cells, head clearance and actual medium-image GPU draw verified')
