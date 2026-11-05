"""Archive reproducible private medium inputs and review media after installation."""
import argparse,json,shutil,hashlib
from pathlib import Path
from install_layout_table import sha

def archive_inputs(plan_file,compact,archive,base_model,base_blend,compiled):
 plan_file,compact,archive,base_model,base_blend,compiled=map(Path,(plan_file,compact,archive,base_model,base_blend,compiled));plan=json.loads(plan_file.read_text());assert (archive/'install-receipt.json').exists();assert sha(base_model)==plan['model_sha256'];inputs=archive/'Inputs';inputs.mkdir(exist_ok=True);catalog=json.loads((compact/'approved-motion-catalog.json').read_text());motion_map={};gear_map={};new_catalog={};workroot=plan_file.resolve().parents[2]
 for src in (base_model,base_blend):
  dst=inputs/'Base'/src.name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);assert sha(src)==sha(dst)
 for job in plan['jobs']:
  light=job['light_sheet'];motion=Path(catalog[light]['model']);key=str(motion.resolve())
  if key not in motion_map:
   dst=inputs/'Animations'/motion.name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(motion,dst);assert sha(motion)==sha(dst);motion_map[key]=str(dst.resolve())
  ref=json.loads(Path(job['reference']).read_text())
  for item in ref.get('equipment',[]):
   src=Path(item['path']);key=str(src.resolve())
   if key not in gear_map:
    digest=sha(src);dst=inputs/'Equipment'/digest[:12]/src.name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);assert sha(dst)==digest;gear_map[key]=str(dst.resolve())
   item['path']=gear_map[key]
  reference=inputs/'References'/(light+'.json');reference.parent.mkdir(exist_ok=True);reference.write_text(json.dumps(ref,indent=2));new_catalog[light]={'sheet':light,'model':motion_map[str(motion.resolve())],'reference':str(reference.resolve())}
  src=Path(job['root'])/'output'/(job['sheet']+'-preview.gif');dst=archive/'Review'/src.name;dst.parent.mkdir(exist_ok=True);shutil.copy2(src,dst)
 (inputs/'approved-motion-catalog.json').write_text(json.dumps(new_catalog,indent=2));shutil.copy2(compact/'exact-motion-extraction.json',inputs/'exact-motion-extraction.json');shutil.copy2(plan['calibration'],inputs/'global-scale-calibration.json')
 for name in ('animation-preflight.json','all-equipment-head-audit.json','town-axe-helmet-fit.json'):
  src=plan_file.parent/name
  if src.exists():shutil.copy2(src,archive/name)
 assets=json.loads((compiled/'validated-gpu-pack.json').read_text())
 for name,digest in assets['files'].items():
  src=compiled/'HD'/name;dst=archive/'GPU'/'HD'/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);assert sha(dst)==digest
 shutil.copy2(compiled/'HD/layouts.csv',archive/'GPU/HD/layouts.csv');shutil.copy2(compiled/'validated-gpu-pack.json',archive/'GPU/validated-gpu-pack.json')
 (archive/'README.txt').write_text('Approved Medium Warrior revision medium-v1. Final contains the 85 native-NN8 source sheets. GPU/HD contains the complete class GPU pages, root sprites.gpus and layouts.csv; there are no per-sheet runtime sidecars. Inputs preserves the approved base and exact skeletal motion donors without redundant donor meshes. Review GIFs show South, West and Northwest; the sheets themselves contain all eight directions. The town stowed axe is shifted 4cm in chest-local X for helmet clearance; character motion and weapon rotation are preserved. Original model variants and previous installed medium data are preserved separately. Proprietary models, textures, animations and captures must remain private.\n')
 print('Archived approved base,',len(motion_map),'exact motions,',len(gear_map),'equipment assets and 85 review GIFs; GPU hashes verified')

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for n in ('plan','compact','archive','base_model','base_blend','compiled'):p.add_argument(n,type=Path)
 a=p.parse_args();archive_inputs(a.plan,a.compact,a.archive,a.base_model,a.base_blend,a.compiled)
