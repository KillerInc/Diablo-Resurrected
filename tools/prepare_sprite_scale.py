"""Prepare a private lower-density custom pack, preserving every frame and anchor.
Source PNGs and the installed game are never modified. Artwork is not a Git input.
"""
import argparse
import copy
import json
from pathlib import Path
import re
from PIL import Image
from hd_layouts import read_table, write_table
from install_layout_table import sha


def prepare(hd, manifest, grid_log, output, density=4):
    hd, manifest, grid_log, output = map(Path, (hd, manifest, grid_log, output))
    if output.exists(): raise ValueError('Output must be a new directory')
    if density not in (1,2,4,8,16): raise ValueError('Invalid density')
    grids = {}
    for path, columns, rows in re.findall(r'Loaded HD sheet: (hd/[^ ]+) \([^\n]*?, (\d+) directions, (\d+) frames,', grid_log.read_text(errors='replace')):
        grids[path.removeprefix('hd/')] = (int(columns), int(rows))
    record=json.loads(manifest.read_text()); result=copy.deepcopy(record)
    layouts=read_table(hd/'layouts.csv'); changed={}
    Image.MAX_IMAGE_PIXELS=None
    # Preflight all source identities and grids before producing any pack files.
    for name, sheet in record['sheets'].items():
        relative='plrgfx/warrior/'+name[:3]+'/'+name+'.png'
        assert sha(hd/relative) == sheet['sha256'].upper(), relative
        assert layouts[relative] == sheet['layout']
        assert relative in grids, relative
    output.mkdir(parents=True)
    for number,(name,sheet) in enumerate(record['sheets'].items(),1):
        relative='plrgfx/warrior/'+name[:3]+'/'+name+'.png'
        version, old_density, x, y=sheet['layout'].split();old_density=int(old_density)
        assert version=='D1R_SHEET_V1' and density<=old_density and old_density%density==0
        step=old_density//density;columns,rows=grids[relative]
        source=hd/relative; target=output/'HD'/relative;target.parent.mkdir(parents=True,exist_ok=True)
        with Image.open(source) as original:
            original=original.convert('RGBA');w,h=original.size
            assert w%columns==0 and h%rows==0
            cw,ch=w//columns,h//rows
            assert cw%step==0 and ch%step==0
            scaled=Image.new('RGBA',(w//step,h//step))
            for col in range(columns):
                for row in range(rows):
                    cell=original.crop((col*cw,row*ch,(col+1)*cw,(row+1)*ch))
                    cell=cell.resize((cw//step,ch//step),Image.Resampling.LANCZOS)
                    scaled.paste(cell,(col*cw//step,row*ch//step))
            scaled.save(target)
            size=list(scaled.size)
        layout=f'D1R_SHEET_V1 {density} {x} {y}'
        layouts[relative]=layout
        result['sheets'][name].update(source=str(target.resolve()),size=size,sha256=sha(target),layout=layout)
        changed[relative]={'original_sha256':sha(source),'sha256':sha(target),'original_size':[w,h],'size':size,'columns':columns,'rows':rows,'layout':layout,'rgba_bytes':size[0]*size[1]*4}
        if number%10==0: print(f'Prepared {number}/{len(record["sheets"])} sheets',flush=True)
    write_table(output/'HD/layouts.csv',layouts)
    result['scale_revision']={'density':density,'pixel_area_relative_to_vanilla':density*density,'resampling':'per-frame Lanczos; original logical anchors preserved','original_manifest':str(manifest.resolve()),'installed':False}
    (output/'install-manifest.json').write_text(json.dumps(result,indent=2))
    (output/'scale-proof.json').write_text(json.dumps(changed,indent=2))
    print('Prepared',len(changed),'sheets;',sum(v['rgba_bytes'] for v in changed.values()),'RGBA bytes; source pack unchanged',flush=True)
    return changed


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['hd','manifest','grid_log','output']:parser.add_argument(name,type=Path)
    parser.add_argument('--density',type=int,default=4)
    args=parser.parse_args();prepare(args.hd,args.manifest,args.grid_log,args.output,args.density)
