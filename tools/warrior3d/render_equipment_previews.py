"""Render an explicitly private candidate plan without changing game files.

python SCRIPT PREVIEW_PLAN.json BLENDER.exe
Retains the existing body motion, scale, full shadows and selected directions.
"""
import json,sys,concurrent.futures
from pathlib import Path
plan_file=Path(sys.argv[1]);root=plan_file.parent;tools=Path(__file__).parent;sys.path.insert(0,str(tools));from build_equipped_sets import command
plan=json.loads(plan_file.read_text());assert plan.get('preview_only') and not plan.get('superseded'),'Superseded preview plan';blender=Path(sys.argv[2])
def run(j):
 out=Path(j['root']);ref=json.loads(Path(j['reference']).read_text());expected=ref['rows']*len(ref['render_directions']);reuse=False
 if '--reuse-existing' in sys.argv and (out/'frames/render.json').exists():
  meta=json.loads((out/'frames/render.json').read_text());reuse=all(meta.get(k)==ref.get(k) for k in ['equipment','source_frames','pose_offsets','render_directions']) and len(list((out/'frames').glob('body-*.png')))==expected and len(list((out/'shadows').glob('shadow-*.png')))==expected
 print('START',j['name'],'existing captures' if reuse else 'render',flush=True)
 if not reuse:
  command([blender,'-b','--python',tools/'render_paladin_town_walk.py','--',j['model'],j['reference'],out/'frames'],out/'body.log')
  command([blender,'-b','--python',tools/'render_paladin_shadows.py','--',out/'frames/Paladin-town-walk-render.blend',out/'frames/render.json',out/'shadows'],out/'shadow.log')
 command([sys.executable,tools/'assemble_equipment_preview.py',out/'frames',out/'shadows',out/'frames/render.json',plan['calibration'],out/'output'],out/'assembly.log')
 print('DONE',j['name'],flush=True);return {'name':j['name'],'validation':json.loads((out/'output/validation.json').read_text())}
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,plan['jobs']))
(root/'validation.json').write_text(json.dumps(results,indent=2));print('All four fitted previews completed; no game files changed',flush=True)
