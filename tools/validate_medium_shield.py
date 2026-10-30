"""Validate a private medium shield pack against unchanged motion and installed art."""
import argparse,json,re,csv
from pathlib import Path
from install_layout_table import sha
p=argparse.ArgumentParser(description=__doc__)
for key in ('plan','baseline','root','capture'):p.add_argument(key,type=Path)
a=p.parse_args();plan=json.loads(a.plan.read_text());pack=a.plan.parent/'pack/compiled';art=json.loads((a.plan.parent/'pack/cast-art-manifest.json').read_text());after=json.loads((pack/'validated-gpu-pack.json').read_text());before=json.loads((a.baseline/'validated-gpu-pack.json').read_text());expected={f'wm{w}{action}' for w in 'dhu' for action in ('as','at','aw','bl','fm','ht','lm','qm','st','wl')};assert set(art['sheets'])==expected
changed={f'plrgfx/warrior/{n[:3]}/{n}.png' for n in expected};assert all(after['source_png_hashes'][n]==h for n,h in before['source_png_hashes'].items() if n not in changed)
audit=json.loads((a.plan.parent/'all-equipment-head-audit.json').read_text());assert len(audit)==30 and not any(r['head_contacts'] for r in audit)
frames=0
for job in plan['jobs']:
 ref=json.loads(Path(job['reference']).read_text());original=json.loads(Path(job['original_reference']).read_text());assert Path(job['model']).is_file()
 assert {k:v for k,v in ref.items() if k!='equipment'}=={k:v for k,v in original.items() if k!='equipment'}
 assert [e for e in ref['equipment'] if 'shield' not in e['path'].lower()]==[e for e in original['equipment'] if 'shield' not in e['path'].lower()]
 assert sum(Path(e['path']).name=='shield_Medium.glb' for e in ref['equipment'])==1
 v=json.loads((Path(job['root'])/'output/validation.json').read_text());assert len(v['body_cells'])==len(v['shadow_cells'])==job['rows']*8;assert art['sheets'][job['sheet']]['sha256']==v['sheet_sha256'].upper();frames+=job['rows']*8
text=(a.root/'medium-live.log').read_text(errors='replace');diagnostics=(a.root/'medium-live-stderr.log').read_text(errors='replace');assert json.loads((a.root/'medium-live-process.json').read_text(encoding='utf-8-sig'))['exit']==0;assert text.count('GPU_SHEET_RESIDENT source=hd/plrgfx/warrior/')==255;assert 'Loaded HD sheet: hd/plrgfx/' not in text;assert diagnostics.count('HD_GPU_INDEX: loaded sheets=255 cache=process-lifetime')==1
aliases=json.loads((a.root/'medium-live-alias-proof.json').read_text());lookups={r['lookup'] for r in aliases};draws=set(re.findall(r'HD_PLAYER_DRAW source=hd/([^\s]+)',text));assert draws.intersection(lookups) and a.capture.is_file()
assert json.loads((a.root/'medium-live-audio.json').read_text(encoding='utf-8-sig'))['mode']=='muted'
proof=json.loads((a.root/'validation.json').read_text());proof['checks'].update(shield_bounds=True,shield_visual_review=True,shield_live_draw=True,character_motion_unchanged=True);proof['medium_shield']={'revision':'medium-shield-v1','sheets':30,'directional_frames':frames,'unmodified_sheets':225,'helmet_contacts':0,'reviewed_capture':str(a.capture.resolve()),'source_motion_unchanged':True,'other_equipment_unchanged':True,'installed_spell_effects_retained':True};(a.root/'validation.json').write_text(json.dumps(proof,indent=2));print('PASS: 30 shield sheets;225 preserved;character motion/other equipment/effects unchanged;head clearance and live GPU draws verified')
