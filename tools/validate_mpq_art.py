"""Validate private prepared MPQ art, BC7 pages and native engine references."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess
from PIL import Image,ImageChops,ImageStat
from gpu_index import read_index
from validate_gpu_pack import dds


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(raw,prepared,pack,references,cel_validator):
    Image.MAX_IMAGE_PIXELS=None
    inventory=json.loads((prepared/'inventory.json').read_text())
    manifest=json.loads((prepared/'source-manifest.json').read_text())
    proofs={}
    for name in ('gpu-pack-proof.json','proof-extra.json'):
        part=json.loads((pack/name).read_text());assert not set(part)&set(proofs);proofs.update(part)
    records=read_index(pack/'HD/sprites.gpus')
    assert set(inventory)==set(manifest)==set(proofs)==set(records)
    assert not json.loads((prepared/'unresolved.json').read_text())
    references.mkdir(parents=True,exist_ok=True)
    pages=total=tile_count=cel_count=0;worst_rgb=worst_alpha=0;files={}
    for number,(rel,item) in enumerate(sorted(manifest.items()),1):
        source=raw/item['source'];assert sha(source)==item['source_sha256']
        png=prepared/'HD'/rel;assert sha(png)==item['prepared_sha256']==proofs[rel]['source_sha256'].lower()
        native=prepared/'indices'/rel
        indices=Image.open(native);assert indices.mode=='LA'
        grid=inventory[rel];cols,rows=grid['columns'],grid['rows'];cw,ch=grid['width'],grid['height']
        assert indices.size==(cw*cols,ch*rows)
        if item['layout']=='microcells-source-frame-order':
            binary=references/('engine-'+Path(rel).parts[1]+'.bin')
            data=binary.read_bytes();n=struct.unpack_from('<I',data)[0];assert n==item['original_frames']
            assert len(data)==4+n*2048
            for i in range(n):
                col,row=divmod(i,rows);cell=indices.crop((col*32,row*32,(col+1)*32,(row+1)*32))
                assert cell.getchannel('L').tobytes()==data[4+i*2048:4+i*2048+1024],(rel,i,'tile indices')
                assert cell.getchannel('A').tobytes()==data[4+i*2048+1024:4+(i+1)*2048],(rel,i,'tile alpha')
            tile_count+=n
        elif item['source'].endswith('.cel'):
            binary=references/Path(rel).with_suffix('.bin');binary.parent.mkdir(parents=True,exist_ok=True)
            sizes=binary.with_suffix('.widths.txt')
            sizes.write_text('\n'.join(str(width) for width,height in item['frame_sizes'][:rows])+'\n')
            assert not binary.exists(),'Use a fresh reference folder for CEL checks'
            result=subprocess.run([str(cel_validator),str(source),str(sizes),str(binary)],capture_output=True,text=True,check=True)
            data=binary.read_bytes();assert struct.unpack_from('<4I',data)==(cols,rows,cw,ch),rel
            size=cw*ch;assert len(data)==16+2*size*cols*rows
            for i in range(cols*rows):
                col,row=divmod(i,rows);cell=indices.crop((col*cw,row*ch,(col+1)*cw,(row+1)*ch));offset=16+i*size*2
                assert cell.getchannel('L').tobytes()==data[offset:offset+size],(rel,i,'CEL indices')
                assert cell.getchannel('A').tobytes()==data[offset+size:offset+size*2],(rel,i,'CEL alpha')
            cel_count+=1
        else:
            original=Image.open(source);width,height=original.size
            native_cell=indices.crop((0,0,width,height))
            assert original.tobytes()==native_cell.getchannel('L').tobytes(),rel
            key=item['transparent_index']
            expected=bytes(0 if key is not None and value==key else 255 for value in original.tobytes())
            assert native_cell.getchannel('A').tobytes()==expected,rel
        image=Image.open(png).convert('RGBA');metadata=records[rel]
        values=metadata[0].split();density,mc,mr,mw,mh,count=map(int,values[1:])
        assert (density,mc,mr,mw,mh)==(4,cols,rows,cw,ch)
        decoded=[]
        for entry in metadata[1:1+count]:
            name,w,h=entry.split();w,h=int(w),int(h);path=pack/'HD'/Path(rel).parent/name
            data=path.read_bytes();assert struct.unpack_from('<II',data)==(w,h) and len(data)==8+w*h
            assert w%4==h%4==0 and max(w,h)<=4096
            decoded.append(dds(data[8:],w,h));files[path.relative_to(pack/'HD').as_posix()]=sha(path)
            total+=w*h;pages+=1
        for i,line in enumerate(metadata[1+count:]):
            page,x,y,w,h,left,top=map(int,line.split());col,row=divmod(i,rows)
            cell=image.crop((col*cw*4,row*ch*4,(col+1)*cw*4,(row+1)*ch*4))
            box=cell.getchannel('A').getbbox()
            if not w or not h:assert box is None;continue
            assert box==(left,top,left+w,top+h)
            assert x>=4 and y>=4 and x+w+4<=decoded[page].width and y+h+4<=decoded[page].height
            actual=decoded[page].crop((x,y,x+w,y+h));expected=cell.crop(box)
            difference=ImageChops.difference(actual,expected)
            alpha=ImageStat.Stat(difference.getchannel('A')).rms[0]
            rgb=ImageStat.Stat(difference.convert('RGB'),expected.getchannel('A')).rms
            error=math.sqrt(sum(value*value for value in rgb)/3)
            worst_rgb=max(worst_rgb,error);worst_alpha=max(worst_alpha,alpha)
            assert alpha==0 and error<=2,(rel,i,error,alpha)
        if number%25==0:print('VALIDATED',number,'of',len(manifest),flush=True)
    files['sprites.gpus']=sha(pack/'HD/sprites.gpus')
    report=dict(sheets=len(manifest),pages=pages,texture_bytes=total,tile_microcells=tile_count,
        cel_sheets_engine_verified=cel_count,pcx_atlases_verified=sum(v['source'].endswith('.pcx') for v in manifest.values()),
        maximum_frame_rgb_rmse=worst_rgb,maximum_frame_alpha_rmse=worst_alpha,files=files,
        source_files={v['source']:v['source_sha256'] for v in manifest.values()})
    (pack/'validated-art-pack.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k not in ('files','source_files')},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('raw','prepared','pack','references','cel_validator'):parser.add_argument(name,type=Path)
    args=parser.parse_args();validate(args.raw,args.prepared,args.pack,args.references,args.cel_validator.resolve())
