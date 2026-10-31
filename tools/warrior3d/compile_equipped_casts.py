"""Stage/compile a cast-only revision while preserving the complete installed class."""
import argparse,json,os,shutil,time,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pack_gpu_sprites import pack
from prepare_sprite_scale import prepare
from gpu_index import consolidate
from hd_layouts import read_table,write_table
from install_layout_table import sha

def clone(src,dst):
 dst.mkdir(parents=True,exist_ok=True)
 for p in src.rglob('*'):
  t=dst/p.relative_to(src)
  if p.is_dir():t.mkdir(exist_ok=True)
  elif not t.exists():
   if p.suffix.lower() in ('.png','.bc7'):
    try:os.link(p,t);continue
    except OSError:pass
   shutil.copy2(p,t)

def compile(plan,baseline,encoder):
 plan=json.loads(Path(plan).read_text());baseline=Path(baseline).resolve();encoder=Path(encoder).resolve();work=Path(plan['work'])/'pack'
 hd=work/'source-HD';custom=work/'custom-4x';compiled=work/'compiled'
 clone(baseline/'source-HD',hd);clone(baseline/'custom-4x',custom);clone(baseline/'compiled',compiled)
 shutil.copy2(baseline/'native-grid.log',work/'native-grid.log')
 table=read_table(hd/'layouts.csv');art_file=work/'cast-art-manifest.json';art=json.loads(art_file.read_text()) if art_file.exists() else {'sheets':{}}
 pending=list(plan['jobs'])
 while pending:
  done=[]
  for job in pending:
   name=job['sheet'];out=Path(job['root'])/'output'
   if name in art['sheets'] and (out/'validation.json').exists():
    current=json.loads((out/'validation.json').read_text())
    if current['sheet_sha256'].upper()==art['sheets'][name]['sha256'].upper():done.append(job);continue
   if not (out/'validation.json').exists():continue
   v=json.loads((out/'validation.json').read_text());src=out/(name+'.png');assert sha(src).lower()==v['sheet_sha256'].lower()
   rel=f'plrgfx/warrior/{name[:3]}/{name}.png';target=hd/rel;target.unlink();shutil.copy2(src,target)
   layout=(out/(name+'.png.layout')).read_text().strip();table[rel]=layout;write_table(hd/'layouts.csv',table)
   record={'source':str(src),'sha256':sha(src),'size':v['size'],'layout':layout,'rows':job['rows']}
   single=work/(name+'-manifest.json');single.write_text(json.dumps({'sheets':{name:record}}))
   small=work/(name+'-4x')
   if small.exists():small.rename(small.with_name(small.name+'-previous-'+str(time.time_ns())))
   prepare(hd,single,work/'native-grid.log',small,4)
   t=custom/'HD'/rel;t.parent.mkdir(parents=True,exist_ok=True);t.unlink(missing_ok=True);shutil.copy2(small/'HD'/rel,t)
   meta=(compiled/'HD'/rel).with_suffix('.gpus')
   for p in [meta,*meta.parent.glob(meta.stem+'.p*.bc7')]:p.unlink()
   pack(hd,custom,work/'native-grid.log',compiled,encoder,only=[name])
   art['sheets'][name]=record;art_file.write_text(json.dumps(art,indent=2));done.append(job)
   print('CAST_COMPILED',len(art['sheets']),len(plan['jobs']),name,flush=True)
  pending=[j for j in pending if j not in done]
  if pending:time.sleep(5)
 write_table(compiled/'HD/layouts.csv',table);consolidate(compiled/'HD')
 print('CAST_PACK_COMPLETE',len(art['sheets']),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for key in ('plan','baseline','encoder'):p.add_argument(key)
 a=p.parse_args();compile(a.plan,a.baseline,a.encoder)
