"""Prepare private light/medium equipped casts, preserving unarmed and other actions."""
import argparse,copy,json,struct
from pathlib import Path
from merge_paladin_walk import read,merge
from extract_approved_motion import extract

def write_glb(doc,blob,path):
 text=json.dumps(doc,separators=(',',':')).encode();text+=b' '*(-len(text)%4)
 path.write_bytes(struct.pack('<III',0x46546c67,2,28+len(text)+len(blob))+struct.pack('<II',len(text),0x4e4f534a)+text+struct.pack('<II',len(blob),0x004e4942)+blob)

def prepare(collection,catalog,medium_plan,work,grids):
 collection,catalog,medium_plan,work=map(lambda p:Path(p).resolve(),(collection,catalog,medium_plan,work))
 assert not work.exists();work.mkdir(parents=True)
 light=json.loads(catalog.read_text());medium=json.loads(medium_plan.read_text());mj={j['sheet']:j for j in medium['jobs']}
 grids=json.loads(Path(grids).read_text())
 doc,blob=read(collection);motion={};models={};proof={}
 for mode in ('1hsShd','2HM'):
  name=f'palM_{mode}_aura_fanaticism';selected=copy.deepcopy(doc);selected['animations']=[a for a in doc['animations'] if a['name']==name];assert len(selected['animations'])==1
  temp=work/'selected.glb';write_glb(selected,blob,temp);target=work/(mode+'-motion.glb');proof[mode]=extract(temp,target);temp.unlink();motion[mode]=target
 for armor,source in [('l',Path(light['wlnfm']['model'])),('m',Path(medium['model']))]:
  base,data=read(source);base.pop('animations',None);static=work/(armor+'-static.glb');write_glb(base,data,static)
  for mode in motion:
   dst=work/f'{armor}-{mode}.glb';merge(static,motion[mode],dst);models[armor,mode]=dst
  static.unlink()
 jobs=[]
 for armor in ('l','m'):
  for weapon in 'abdhmstu':
   for spell in ('fm','lm','qm'):
    name='w'+armor+weapon+spell;old=mj['wm'+weapon+spell];ref=json.loads(Path(old['reference']).read_text())
    idle=json.loads(Path(mj['wm'+weapon+'as']['reference']).read_text())
    mode='2HM' if weapon in 'abt' else '1hsShd'
    md,_=read(motion[mode]);duration=max(md['accessors'][s['input']]['max'][0] for s in md['animations'][0]['samplers']);rows=ref['rows']
    # Motion donors can have extra samples. The installed native sheet grid,
    # rather than the donor's row count, determines runtime animation timing.
    rows=grids[f'plrgfx/warrior/{name[:3]}/{name}.png']['rows']
    for k in ('pose_offsets','pose_image_offsets','direction_pose_offsets','direction_image_offsets','redirect_fall','source_render_rows','render_rows'):ref.pop(k,None)
    ref.update(sheet=name+'.png',rows=rows,source_frames=[round(duration*30*i/(rows-1)) for i in range(rows)],equipment=idle['equipment'],root_anchor_frame=0,
               preview_prefix=name,preview_caption='Equipped Fanaticism cast | original effects | southeast shadows',body_render_samples=32,shadow_render_samples=8)
    if armor=='l':ref.update(shadow_material_tokens=['base16_TRS','armor_skin','P00_HED','base01_GLV','base01_LEG','base05_BTS'],shadow_anatomy_count=6)
    root=work/'jobs'/name;root.mkdir(parents=True);reference=root/'reference.json';reference.write_text(json.dumps(ref,indent=2))
    jobs.append({'sheet':name,'root':str(root),'reference':str(reference),'model':str(models[armor,mode]),'rows':rows,'native_clip':f'palM_{mode}_aura_fanaticism'})
 result={'work':str(work),'calibration':medium['calibration'],'jobs':jobs,'motion_proof':proof,'unarmed_unchanged':True,'armor_classes':['light','medium'],'status':'prepared_not_installed'}
 (work/'plan.json').write_text(json.dumps(result,indent=2));print('Prepared',len(jobs),'equipped spell sheets; no installed files changed')

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for key in ('collection','catalog','medium_plan','work','grids'):p.add_argument(key)
 a=p.parse_args();prepare(a.collection,a.catalog,a.medium_plan,a.work,a.grids)
