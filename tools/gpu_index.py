"""Consolidate GPU metadata without decoding or changing BC7 pages.

Private per-sheet intermediates may remain in an authoring pack. Runtime uses
only HD/sprites.gpus. Run after all parallel encoder workers have completed.
"""
import argparse
from collections import Counter
from pathlib import Path
import os


def read_index(path):
    lines=iter(Path(path).read_text().splitlines())
    assert next(lines)=='D1R_GPU_INDEX_V1'
    tag,*defaults=next(lines).split();assert tag=='DEFAULTS' and len(defaults)==4
    defaults=list(map(int,defaults));records={}
    for line in lines:
        if not line:continue
        tag,rel,rows,pages,*fields=line.split()
        assert tag=='SHEET' and len(fields)==4 and rel not in records
        assert rel.startswith(('plrgfx/','monsters/','missiles/','objects/','towners/','levels/','ctrlpan/','data/','items/','ui_art/','gendata/')) and '..' not in rel and '\\' not in rel and rel.endswith('.png')
        density,columns,width,height=[default if field=='*' else int(field) for field,default in zip(fields,defaults)]
        rows,pages=int(rows),int(pages)
        assert min(density,columns,width,height,rows,pages)>0
        body=[next(lines) for _ in range(pages+columns*rows)]
        records[rel]=[f'D1R_GPU_SHEET_V1 {density} {columns} {rows} {width} {height} {pages}',*body]
    return records


def consolidate(hd,base_index=None):
    hd=Path(hd);records=read_index(base_index) if base_index else {};headers=[]
    for path in sorted(hd.rglob('*.gpus')):
        if path==hd/'sprites.gpus':continue
        lines=path.read_text().splitlines()
        magic,*numbers=lines[0].split();assert magic=='D1R_GPU_SHEET_V1'
        density,columns,rows,width,height,pages=map(int,numbers)
        assert len(lines)==1+pages+columns*rows
        rel=path.relative_to(hd).with_suffix('.png').as_posix()
        assert rel not in records, "Duplicate GPU record: "+rel
        records[rel]=lines
    headers=[tuple(int(lines[0].split()[i]) for i in (1,2,4,5)) for lines in records.values()]
    assert records,'No intermediate GPU metadata found'
    defaults=[Counter(header[i] for header in headers).most_common(1)[0][0] for i in range(4)]
    output=['D1R_GPU_INDEX_V1','DEFAULTS '+' '.join(map(str,defaults))]
    for (rel,lines),values in zip(records.items(),headers):
        _,density,columns,rows,width,height,pages=lines[0].split()
        fields=['*' if value==default else str(value) for value,default in zip(values,defaults)]
        output.append(f'SHEET {rel} {rows} {pages} '+ ' '.join(fields));output.extend(lines[1:])
    target=hd/'sprites.gpus';temporary=target.with_suffix('.gpus-new')
    assert not temporary.exists()
    try:
        temporary.write_bytes(('\n'.join(output)+'\n').encode())
        assert read_index(temporary)==records,'Consolidation must preserve every original record'
        os.replace(temporary,target)
    finally:temporary.unlink(missing_ok=True)
    print(f'Consolidated {len(records)} sheets into {target} ({target.stat().st_size} bytes); BC7 pages unchanged')
    return target


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('hd',type=Path)
    p.add_argument('--base-index',type=Path,help='Preserve existing compiled records and pages')
    a=p.parse_args();consolidate(a.hd,a.base_index)
