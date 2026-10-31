"""Prepare an isolated in-engine heavy look test without changing save equipment.

The copied test pack aliases the fixture's light sword/shield visuals to the heavy sword/shield
pages; gameplay/save data and the real installed pack remain unchanged.
"""
import argparse,json,shutil
from pathlib import Path
from gpu_index import read_index,consolidate
from hd_layouts import read_table,write_table
from install_layout_table import sha

def prepare(pack,game,output):
 pack,game,output=map(Path,(pack,game,output));assert not output.exists();output.mkdir(parents=True)
 records=read_index(pack/'HD/sprites.gpus');table=read_table(pack/'HD/layouts.csv');meta=output.parent/(output.name+'-metadata');meta.mkdir();proof=[]
 for name in ('Diablo Reincarnated.exe','d1reincarnated.mpq'):shutil.copy2(game/name,output/name)
 hd=output/'HD';hd.mkdir()
 # Copy original pages once. All edits are confined to the isolated test pack.
 for src in (pack/'HD').rglob('*.bc7'):
  dst=hd/src.relative_to(pack/'HD');dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
 for rel,lines in list(records.items()):
  if not rel.startswith('plrgfx/warrior/wld/'):continue
  heavy=rel.replace('/wld/','/whd/').replace('/wld','/whd');replacement=list(records[heavy]);count=int(replacement[0].split()[-1])
  # Resample only the private visual alias when native row counts differ.
  source_rows=int(replacement[0].split()[3]);target_rows=int(lines[0].split()[3]);header=replacement[0].split();header[3]=str(target_rows);frames=replacement[1+count:];replacement=[' '.join(header)]+replacement[1:1+count]+[frames[d*source_rows+round(r*(source_rows-1)/max(1,target_rows-1))] for d in range(8) for r in range(target_rows)]
  for i in range(1,count+1):
   name,w,h=replacement[i].split();newname='heavy-check-'+name;source=pack/'HD'/Path(heavy).parent/name;target=hd/Path(rel).parent/newname;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target);assert sha(source)==sha(target);replacement[i]=f'{newname} {w} {h}'
  records[rel]=replacement;table[rel]=table[heavy];proof.append({'lookup':rel,'heavy_source':heavy,'texture_bytes_verified':True})
 assert len(proof)==10
 for rel,lines in records.items():
  dst=meta/'plrgfx'/Path(rel).relative_to('plrgfx').with_suffix('.gpus');dst.parent.mkdir(parents=True,exist_ok=True);dst.write_text('\n'.join(lines)+'\n')
 consolidate(meta);shutil.copy2(meta/'sprites.gpus',hd/'sprites.gpus');write_table(hd/'layouts.csv',table);(output.parent/'heavy-live-alias-proof.json').write_text(json.dumps(proof,indent=2));print('Prepared ten verified heavy sword/shield aliases for an isolated visual test')

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('pack','game','output'):p.add_argument(name,type=Path)
 a=p.parse_args();prepare(a.pack,a.game,a.output)
