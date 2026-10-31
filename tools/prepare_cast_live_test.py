"""Show new casts in an isolated replay by aliasing visuals, never save statistics."""
import argparse,json,shutil,os
from pathlib import Path
from gpu_index import read_index,consolidate
from hd_layouts import read_table,write_table
from install_layout_table import sha

def prepare(pack,game,output):
 pack,game,output=map(Path,(pack,game,output));assert not output.exists();output.mkdir(parents=True)
 records=read_index(pack/'HD/sprites.gpus');table=read_table(pack/'HD/layouts.csv');meta=output.parent/(output.name+'-metadata');meta.mkdir();proof=[]
 for name in ('Diablo Reincarnated.exe','d1reincarnated.mpq'):shutil.copy2(game/name,output/name)
 hd=output/'HD';hd.mkdir()
 for src in (pack/'HD').rglob('*.bc7'):
  dst=hd/src.relative_to(pack/'HD');dst.parent.mkdir(parents=True,exist_ok=True)
  try:os.link(src,dst)
  except OSError:shutil.copy2(src,dst)
 for action,spell in [('as','fm'),('ht','lm'),('bl','qm')]:
  rel=f'plrgfx/warrior/wld/wld{action}.png';source=f'plrgfx/warrior/wmd/wmd{spell}.png';lines=list(records[source]);fields=lines[0].split();source_rows=int(fields[3]);target_rows=int(records[rel][0].split()[3]);count=int(fields[-1]);fields[3]=str(target_rows);lines[0]=' '.join(fields)
  frames=lines[1+count:];lines=lines[:1+count]+[frames[d*source_rows+round(r*(source_rows-1)/max(1,target_rows-1))] for d in range(8) for r in range(target_rows)]
  for i in range(1,count+1):
   name,w,h=lines[i].split();new='cast-check-'+name;src=pack/'HD'/Path(source).parent/name;dst=hd/Path(rel).parent/new;shutil.copy2(src,dst);assert sha(src)==sha(dst);lines[i]=f'{new} {w} {h}'
  records[rel]=lines;table[rel]=table[source];proof.append({'lookup':rel,'cast_source':source,'source_rows':source_rows,'lookup_rows':target_rows,'statistics_unchanged':True,'visual_resampling_only':True})
 for rel,lines in records.items():
  dst=(meta/rel).with_suffix('.gpus');dst.parent.mkdir(parents=True,exist_ok=True);dst.write_text('\n'.join(lines)+'\n')
 consolidate(meta);shutil.copy2(meta/'sprites.gpus',hd/'sprites.gpus');write_table(hd/'layouts.csv',table);(output.parent/'cast-live-alias-proof.json').write_text(json.dumps(proof,indent=2));print('Prepared three isolated cast aliases; no save or statistics edits')

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for n in ('pack','game','output'):p.add_argument(n)
 a=p.parse_args();prepare(a.pack,a.game,a.output)
