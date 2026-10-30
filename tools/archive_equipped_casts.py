"""Keep artwork and complete reproducible casting inputs in a private archive."""
import argparse,copy,json,shutil,sys
from pathlib import Path
from install_layout_table import sha

def archive(plan_file,archive,compiled):
 plan_file,archive,compiled=map(Path,(plan_file,archive,compiled));plan=json.loads(plan_file.read_text());assert (archive/'install-receipt.json').is_file();inputs=archive/'Inputs';inputs.mkdir(exist_ok=True);models={};equipment={};saved_plan=copy.deepcopy(plan);saved_plan['work']=str((archive/'Work').resolve())
 def put(src,dst):
  dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);assert sha(src)==sha(dst);return str(dst.resolve())
 for j in saved_plan['jobs']:
  src=Path(j['model']);key=str(src.resolve())
  if key not in models:models[key]=put(src,inputs/'Models'/src.name)
  j['model']=models[key];ref=json.loads(Path(j['reference']).read_text())
  for item in ref.get('equipment',[]):
   src=Path(item['path']);key=str(src.resolve())
   if key not in equipment:equipment[key]=put(src,inputs/'Equipment'/sha(src)[:12]/src.name)
   item['path']=equipment[key]
  dst=inputs/'References'/(j['sheet']+'.json');dst.parent.mkdir(exist_ok=True);dst.write_text(json.dumps(ref,indent=2));j['reference']=str(dst.resolve());j['root']=str((archive/'Work/jobs'/j['sheet']).resolve())
  original=next(x for x in plan['jobs'] if x['sheet']==j['sheet']);preview=Path(original['root'])/'output'/(j['sheet']+'-preview.gif');put(preview,archive/'Review'/preview.name)
 saved_plan['calibration']=put(Path(plan['calibration']),inputs/'global-scale-calibration.json');(inputs/'plan.json').write_text(json.dumps(saved_plan,indent=2))
 motions={}
 if all((plan_file.parent/(mode+'-motion.glb')).is_file() for mode in ('1hsShd','2HM')):
  for mode in ('1hsShd','2HM'):put(plan_file.parent/(mode+'-motion.glb'),inputs/'Animations'/(mode+'-motion.glb'))
 else:
  sys.path.insert(0,str(Path(__file__).parent/'warrior3d'))
  from extract_approved_motion import extract
  for original,saved in models.items():
   src=Path(saved);dst=inputs/'Animations'/sha(src)[:12]/(src.stem+'-motion.glb');result=extract(src,dst);motions[original]={'model':str(dst.resolve()),'proof':result}
  (inputs/'exact-motion-extraction.json').write_text(json.dumps(motions,indent=2))
 for name in ('animation-preflight.json','all-equipment-head-audit.json','grip-clearance-fit.json'):
  if (plan_file.parent/name).exists():put(plan_file.parent/name,archive/name)
 assets=json.loads((compiled/'validated-gpu-pack.json').read_text())
 for name,digest in assets['files'].items():assert sha(compiled/'HD'/name)==digest;put(compiled/'HD'/name,archive/'GPU/HD'/name)
 put(compiled/'HD/layouts.csv',archive/'GPU/HD/layouts.csv');put(compiled/'validated-gpu-pack.json',archive/'GPU/validated-gpu-pack.json')
 revision=plan.get('revision','equipped-casts-v1')
 (archive/'README.txt').write_text(f'Warrior graphics revision {revision}: {len(plan["jobs"])} light/medium sheets. Original character motions, equipment, other actions, heavy armor, executable and user state are preserved. Source PNG density8; runtime GPU density4 with one root index/CSV. Review GIFs show South, West and Northwest; production sheets contain all eight directions. Inputs includes complete animated character models, exact compact motion donors, all equipment, references, effect settings and calibration. Keep this entire archive private; it contains proprietary artwork.\n')
 print('Archived',len(plan['jobs']),'casting PNGs/reviews,',len(models),'complete models,',len(equipment),'equipment assets and verified full GPU pack')

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for n in ('plan','archive','compiled'):p.add_argument(n)
 a=p.parse_args();archive(a.plan,a.archive,a.compiled)
