"""Prepare medium sheets from an audited catalog of approved light motions.

Private catalog, source models, images and generated output stay outside Git.
"""
import argparse,copy,hashlib,json,sys
from pathlib import Path
import numpy as np
from merge_paladin_walk import merge

def prepare(model,catalog,manifest,gpu_proof,work,calibration=None,armor="m",registry_file=None):
 model,catalog,manifest,gpu_proof,work=map(lambda p:Path(p).resolve(),(model,catalog,manifest,gpu_proof,work))
 assert not work.exists(),'Use a fresh private work directory';work.mkdir(parents=True)
 assert armor in ('m','h')
 registry=json.loads((Path(registry_file) if registry_file else Path(__file__).parent/('heavy_warrior_source.json' if armor=='h' else 'medium_warrior_source.json')).read_text())
 expected_sha=registry['approved_model_sha256'] if armor=='h' else registry['sha256']
 assert hashlib.sha256(model.read_bytes()).hexdigest().upper()==expected_sha
 source=json.loads(catalog.read_text());installed=json.loads(manifest.read_text());grids=json.loads(gpu_proof.read_text());jobs=[];models={}
 oldroot=r'C:\Users\kille\.codex\.chatgpt-projects\g-p-6ad48fbb0ae08191a500e55129b616e6';newroot=str(manifest.parents[2])
 def fix(value):
  if isinstance(value,str):return value.replace(oldroot,newroot)
  if isinstance(value,list):return [fix(v) for v in value]
  if isinstance(value,dict):return {k:fix(v) for k,v in value.items()}
  return value
 light_names={name for name in installed['sheets'] if name.startswith('wl')}
 assert set(source)==light_names and len(source)==85
 for light,j in sorted(source.items()):
  name='w'+armor+light[2:];root=work/'jobs'/name;root.mkdir(parents=True)
  src=Path(j['model']).resolve();key=str(src)
  if key not in models:
   dst=work/'models'/(src.stem+'-'+hashlib.sha256(key.encode()).hexdigest()[:10]+'.glb');merge(model,src,dst);models[key]=str(dst)
  ref=fix(json.loads(Path(j['reference']).read_text()))
  frames=ref.get('source_frames',list(range(ref.get('rows',ref.get('output_rows',0)))))
  if ref.get('source_render_rows'):frames=[frames[i] for i in ref.pop('source_render_rows')]
  target=grids[f'plrgfx/warrior/{name[:3]}/{name}.png'];rows=target['rows']
  assert frames,(light,'Missing approved frame sampling')
  oldrows=len(frames);frames=[round(float(np.interp(i,np.linspace(0,rows-1,oldrows),frames))) for i in range(rows)] if oldrows!=rows else frames
  # Preserve complete motion duration, with integer samples expected by the
  # existing body/shadow renderer. No limb or stride attenuation is introduced.
  for field in ('pose_offsets','pose_image_offsets'):
   if ref.get(field) and len(ref[field])!=rows:
    values=np.asarray(ref[field]);ref[field]=[[float(np.interp(i,np.linspace(0,rows-1,len(values)),values[:,a])) for a in range(values.shape[1])] for i in range(rows)]
  ref.pop('render_rows',None);ref.pop('direction_pose_offsets',None) if light=='wlndt' else None
  ref.update(sheet=name+'.png',rows=rows,source_frames=frames,columns=['S','SW','W','NW','N','NE','E','SE'],render_directions=list(range(8)),preview_prefix=name,preview_caption=('Heavy' if armor=='h' else 'Medium')+' Warrior | approved motion | southeast shadows',shadow_overscan=512,shadow_material_tokens=['P00_HED','Helmet dark gray metal','base06_TRS','base06_GLV','base06_LEG_mat','base06_LEG_belt_sim','base06_BTS'],shadow_anatomy_count=9)
  if registry.get('shadow_material_tokens'):ref.update(shadow_material_tokens=registry['shadow_material_tokens'],shadow_anatomy_count=registry['shadow_anatomy_count'])
  # Final canvas and anchor follow the installed, approved padded light sheet.
  record=installed['sheets'][light];width=record['size'][0]//64
  lightrows=grids[f'plrgfx/warrior/{light[:3]}/{light}.png']['rows'];height=record['size'][1]//(lightrows*8)
  if armor=='m':ref.update(canvas_logical=[width,height],canvas_anchor=list(map(int,record['layout'].split()[2:4])))
  reference=root/'reference.json';reference.write_text(json.dumps(ref,indent=2))
  jobs.append({'sheet':name,'light_sheet':light,'model':models[key],'reference':str(reference),'root':str(root),'rows':rows,'source_frame_count':oldrows,'frame_count_resampled':rows!=oldrows})
 result={'work':str(work),'model':str(model),'model_sha256':expected_sha,'armor':armor,'jobs':jobs,'motion_models':len(models),'source_sheets':85,'status':'prepared_not_installed','calibration':str(Path(calibration).resolve() if calibration else manifest.parents[1]/'paladin-short-stride-final/output/validation.json')}
 (work/'plan.json').write_text(json.dumps(result,indent=2));print('Prepared',len(jobs),'medium sheets from',len(models),'approved motion models',flush=True)
 return result

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('model','catalog','manifest','gpu_proof','work'):p.add_argument(name)
 p.add_argument('--calibration',type=Path);p.add_argument('--armor',choices=['m','h'],default='m');p.add_argument('--registry',type=Path)
 a=p.parse_args();prepare(a.model,a.catalog,a.manifest,a.gpu_proof,a.work,a.calibration,a.armor,a.registry)
