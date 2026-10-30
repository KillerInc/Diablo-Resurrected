"""Prepare all light/medium fire casts without changing any character motion."""
import argparse,copy,json,os,shutil,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from gpu_index import read_index
from hd_layouts import read_table

def prepare(equipped_plan,medium_plan,old_light_catalog,baseline,work,spell='fm'):
 equipped_plan,medium_plan,old_light_catalog,baseline,work=map(lambda p:Path(p).resolve(),(equipped_plan,medium_plan,old_light_catalog,baseline,work));assert not work.exists();work.mkdir(parents=True)
 assert spell in ('fm','lm')
 equipped=json.loads(equipped_plan.read_text());eq={j['sheet']:j for j in equipped['jobs']};medium=json.loads(medium_plan.read_text());mj={j['sheet']:j for j in medium['jobs']};light=json.loads(old_light_catalog.read_text());settings=json.loads((Path(__file__).parent/('fire_bubble_settings.json' if spell=='fm' else 'lightning_settings.json')).read_text());grids=json.loads((baseline/'compiled/gpu-pack-proof.json').read_text());index=read_index(baseline/'compiled/HD/sprites.gpus');table=read_table(baseline/'source-HD/layouts.csv');jobs=[]
 for armor in 'lm':
  for weapon in 'abdhmnstu':
   name='w'+armor+weapon+spell;source=eq.get(name)
   if source is None:
    source=mj['wmn'+spell] if armor=='m' else light['wln'+spell]
   model=Path(source['model']);ref=json.loads(Path(source['reference']).read_text());assert model.is_file()
   rel=f'plrgfx/warrior/{name[:3]}/{name}.png';rows=grids[rel]['rows'];assert len(ref['source_frames'])==rows
   header=index[rel][0].split();layout=table[rel].split();root=work/'jobs'/name;root.mkdir(parents=True)
   ref.update(sheet=name+'.png',rows=rows,cell=ref.get('cell',768),canvas_logical=list(map(int,header[4:6])),canvas_anchor=list(map(int,layout[2:4])),fire_effect=copy.deepcopy(settings),render_directions=list(range(8)),preview_prefix=name,preview_caption=settings['revision']+' | original motion and shadows',body_render_samples=32,shadow_render_samples=8,shadow_overscan=512)
   if armor=='l':ref.update(shadow_material_tokens=['base16_TRS','armor_skin','P00_HED','base01_GLV','base01_LEG','base05_BTS'],shadow_anatomy_count=6)
   else:ref.update(shadow_material_tokens=['P00_HED','Helmet dark gray metal','base06_TRS','base06_GLV','base06_LEG_mat','base06_LEG_belt_sim','base06_BTS'],shadow_anatomy_count=9)
   previous=Path(source.get('root',Path(source['reference']).parent))/'shadows'
   if (previous/'shadow.json').is_file():
    info=json.loads((previous/'shadow.json').read_text())
    # The effect cannot cast a ground silhouette. Exact existing body/gear
    # poses keep their previously validated southeast shadow images.
    dst=root/'shadows';dst.mkdir()
    for p in previous.rglob('*'):
     t=dst/p.relative_to(previous)
     if p.is_dir():t.mkdir(exist_ok=True)
     elif p.suffix in ('.png','.json'):
      try:os.link(p,t)
      except OSError:shutil.copy2(p,t)
   reference=root/'reference.json';reference.write_text(json.dumps(ref,indent=2))
   jobs.append({'sheet':name,'model':str(model),'reference':str(reference),'root':str(root),'rows':rows,'original_model':str(model),'original_reference':source['reference'],'character_motion_unchanged':True})
 plan={'work':str(work),'calibration':equipped['calibration'],'jobs':jobs,'revision':settings['revision'],'character_motion_unchanged':True,'effects_settings':settings,'baseline':str(baseline)}
 (work/'plan.json').write_text(json.dumps(plan,indent=2));print('Prepared18',spell,'sheets; existing character motion and southeast shadows retained')

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for n in ('equipped_plan','medium_plan','old_light_catalog','baseline','work'):p.add_argument(n)
 p.add_argument('--spell',choices=['fm','lm'],default='fm')
 a=p.parse_args();prepare(a.equipped_plan,a.medium_plan,a.old_light_catalog,a.baseline,a.work,a.spell)
