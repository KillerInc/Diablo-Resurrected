"""Recompile explicitly corrected medium sheets after the main compiler finishes."""
import argparse,json,shutil,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pack_gpu_sprites import pack
from prepare_sprite_scale import prepare
from gpu_index import consolidate
from hd_layouts import read_table,write_table
from install_layout_table import sha
p=argparse.ArgumentParser(description=__doc__)
for key in ('plan','work','encoder'):p.add_argument(key,type=Path)
p.add_argument('--sheets',nargs='+',required=True);a=p.parse_args();plan=json.loads(a.plan.read_text());work=a.work.resolve();compiled=work/'compiled';hd=work/'source-HD';custom=work/'custom-4x';art_file=work/'medium-art-manifest.json';art=json.loads(art_file.read_text());assert len(art['sheets'])==85,'Wait for the main compile to complete';table=read_table(hd/'layouts.csv');records={}
proof=json.loads((compiled/'gpu-pack-medium-proof.json').read_text())
for name in a.sheets:
 job=next(j for j in plan['jobs'] if j['sheet']==name);root=Path(job['root'])/'output';validation=json.loads((root/'validation.json').read_text());source=root/(name+'.png');assert sha(source).lower()==validation['sheet_sha256'].lower();relative=f'plrgfx/warrior/{name[:3]}/{name}.png';layout=(root/(name+'.png.layout')).read_text().strip()
 assert (hd/relative).resolve().is_relative_to(hd.resolve());shutil.copy2(source,hd/relative);table[relative]=layout;records[name]={'source':str(source),'size':validation['size'],'sha256':sha(source),'layout':layout,'rows':job['rows']};art['sheets'][name]=records[name]
 meta=(compiled/'HD'/relative).with_suffix('.gpus');saved=work/'correction-backup'/name;saved.mkdir(parents=True,exist_ok=False)
 for file in [meta,*meta.parent.glob(meta.stem+'.p*.bc7')]:
  assert file.resolve().is_relative_to(compiled.resolve());shutil.copy2(file,saved/file.name);file.unlink()
write_table(hd/'layouts.csv',table);manifest=work/'correction-manifest.json';manifest.write_text(json.dumps({'sheets':records},indent=2));small=work/'correction-4x';prepare(hd,manifest,work/'native-grid.log',small,4)
for name in a.sheets:
 relative=f'plrgfx/warrior/{name[:3]}/{name}.png';shutil.copy2(small/'HD'/relative,custom/'HD'/relative)
pack(hd,custom,work/'native-grid.log',compiled,a.encoder,only=a.sheets,proof_name='gpu-pack-medium-proof.json')
base=json.loads((compiled/'gpu-pack-base-proof.json').read_text());base.update(json.loads((compiled/'gpu-pack-medium-proof.json').read_text()));(compiled/'gpu-pack-proof.json').write_text(json.dumps(base,indent=2));write_table(compiled/'HD/layouts.csv',table);art_file.write_text(json.dumps(art,indent=2));consolidate(compiled/'HD');print('REFRESHED_MEDIUM',a.sheets)
