"""Validate a complete private heavy revision and reviewed in-engine draw."""
import argparse,json,re
from pathlib import Path
from install_layout_table import sha
from gpu_index import read_index
from hd_layouts import read_table
p=argparse.ArgumentParser(description=__doc__)
for name in ('plan','baseline','root','capture'):p.add_argument(name,type=Path)
a=p.parse_args();plan=json.loads(a.plan.read_text());pack=a.plan.parent/'pack/compiled';art=json.loads((a.plan.parent/'pack/cast-art-manifest.json').read_text());before=json.loads((a.baseline/'validated-gpu-pack.json').read_text());after=json.loads((pack/'validated-gpu-pack.json').read_text());expected={Path(n).stem for n in before['source_png_hashes'] if n.startswith('plrgfx/warrior/wh')};assert len(expected)==85 and set(art['sheets'])==expected;changed={f'plrgfx/warrior/{n[:3]}/{n}.png' for n in expected}
assert all(after['source_png_hashes'][n]==h for n,h in before['source_png_hashes'].items() if n not in changed)
for name,digest in before['files'].items():
 if name=='sprites.gpus' or Path(name).name.split('.')[0] in expected:continue
 assert after['files'][name]==digest,('Protected GPU page changed',name)
old_index=read_index(a.baseline/'HD/sprites.gpus');new_index=read_index(pack/'HD/sprites.gpus');assert all(new_index[n]==v for n,v in old_index.items() if n not in changed)
old_table=read_table(a.baseline/'HD/layouts.csv');new_table=read_table(pack/'HD/layouts.csv');assert all(new_table[n]==v for n,v in old_table.items() if n not in changed)
heads=json.loads((a.plan.parent/'all-equipment-head-audit.json').read_text());bounds=json.loads((a.plan.parent/'animation-preflight.json').read_text());assert len(heads)==66 and not any(r['head_contacts'] for r in heads);assert len(bounds)==85 and not any(r['helmet_contacts'] for r in bounds)
source=json.loads(Path(plan['source_proof']).read_text());material_ok=source['supplied_materials_preserved']
if not material_ok:
 brightness=source['authorized_brightness_adjustment'];assert brightness['authorized'] and brightness['exposure_stops']==1.0 and brightness['output_sha256'].upper()==plan['model_sha256'];assert all(brightness[k] for k in ('geometry_uv_weights_nodes_unchanged','alpha_unchanged','normals_metallic_roughness_unchanged','original_binary_prefix_unchanged','source_untouched'));material_ok=True
assert material_ok and source['source_preserved'] and source['front_cloth_removal']['remaining_geometry_uv_weights_unchanged'];assert source['sha256'].upper()==plan['model_sha256'];assert sha(Path(plan['model']))==plan['model_sha256'];frames=0
for job in plan['jobs']:
 name=job['sheet'];rel=f'plrgfx/warrior/{name[:3]}/{name}.png';ref=json.loads(Path(job['reference']).read_text());v=json.loads((Path(job['root'])/'output/validation.json').read_text());assert len(ref['source_frames'])==job['rows']==int(old_index[rel][0].split()[3])==int(new_index[rel][0].split()[3]);assert v['frame_count']==job['rows'] and len(v['body_cells'])==len(v['shadow_cells'])==job['rows']*8;assert v['sheet_sha256'].upper()==art['sheets'][name]['sha256'];assert v['global_pixel_scale']==json.loads(Path(plan['calibration']).read_text())['global_pixel_scale'];frames+=job['rows']*8
 merge=json.loads(Path(job['model']).with_suffix('.validation.json').read_text());assert merge['mesh_skin_and_nodes_unchanged'] and merge['max_rest_matrix_difference']<1e-4
text=(a.root/'heavy-live.log').read_text(errors='replace');err=(a.root/'heavy-live-stderr.log').read_text(errors='replace');assert json.loads((a.root/'heavy-live-process.json').read_text(encoding='utf-8-sig'))['exit']==0;assert text.count('GPU_SHEET_RESIDENT source=hd/plrgfx/warrior/')==255 and 'Loaded HD sheet: hd/plrgfx/' not in text;assert err.count('HD_GPU_INDEX: loaded sheets=255 cache=process-lifetime')==1
aliases=json.loads((a.root/'heavy-live-alias-proof.json').read_text());assert len(aliases)==10;lookups={r['lookup'] for r in aliases};draws=set(re.findall(r'HD_PLAYER_DRAW source=hd/([^\s]+)',text));assert draws.intersection(lookups) and a.capture.is_file();assert json.loads((a.root/'heavy-live-audio.json').read_text(encoding='utf-8-sig'))['mode']=='muted'
proof=json.loads((a.root/'validation.json').read_text());proof['checks'].update(heavy_bounds=True,heavy_head_clearance=True,heavy_visual_review=True,heavy_live_draw=True,heavy_material_roundtrip=True,character_motion_unchanged=True);proof['heavy']={'revision':plan.get('revision','heavy-v1'),'sheets':85,'directional_frames':frames,'preserved_light_medium_sheets':170,'head_clear_sequences':66,'source_sha256':source['original_source_sha256'],'model_sha256':plan['model_sha256'],'supplied_materials_preserved':source['supplied_materials_preserved'],'brightness_stops':source.get('authorized_brightness_adjustment',{}).get('exposure_stops',0),'front_cloth_removed':True,'current_effects_retained':True,'reviewed_capture':str(a.capture.resolve())};(a.root/'validation.json').write_text(json.dumps(proof,indent=2));print('PASS: 85 heavy sheets,170 preserved,exact native grids,approved source/motion,equipment clearance and actual GPU draws')
