"""Validate private BC7 pages, grids, source identities and sampled RGBA quality."""
import argparse,io,json,math,struct
from pathlib import Path
from PIL import Image,ImageChops,ImageStat
from gpu_index import read_index
from hd_layouts import read_table
from install_layout_table import sha


def dds(data,w,h):
    header=b'DDS '+struct.pack('<7I',124,0x81007,h,w,w*h,0,0)+bytes(44)
    header+=struct.pack('<II4sIIIII',32,4,b'DX10',0,0,0,0,0)+struct.pack('<5I',0x1000,0,0,0,0)
    header+=struct.pack('<5I',98,3,0,1,0)
    return Image.open(io.BytesIO(header+data)).convert('RGBA')


def validate(pack,hd,custom,proof_names):
    pack,hd,custom=map(Path,(pack,hd,custom));proof={}
    for name in proof_names:proof.update(json.loads((pack/name).read_text()))
    assert len(proof)==255,len(proof)
    assert read_table(pack/'HD/layouts.csv')==read_table(hd/'layouts.csv')
    index=pack/'HD/sprites.gpus';records=read_index(index)
    assert set(records)==set(proof)
    files={'sprites.gpus':sha(index)};total=0;pages_count=0;qualities={}
    Image.MAX_IMAGE_PIXELS=None
    for rel,record in sorted(proof.items()):
        assert rel.startswith('plrgfx/warrior/') and '..' not in rel
        assert sha(hd/rel)==record['source_sha256'],rel
        manifest=(pack/'HD'/rel).with_suffix('.gpus');lines=records[rel]
        magic,density,columns,rows,lw,lh,count=lines[0].split();density,columns,rows,lw,lh,count=map(int,(density,columns,rows,lw,lh,count))
        assert magic=='D1R_GPU_SHEET_V1' and density==4 and (columns,rows)==(record['columns'],record['rows'])
        assert len(lines)==1+count+columns*rows
        assert len(record['frames'])==columns*rows
        decoded=None
        for page_index,line in enumerate(lines[1:1+count]):
            name,w,h=line.split();w,h=int(w),int(h);assert Path(name).name==name and w%4==h%4==0 and 0<w<=2048 and 0<h<=2048
            path=manifest.parent/name;data=path.read_bytes();assert struct.unpack('<II',data[:8])==(w,h) and len(data)==w*h+8
            files[path.relative_to(pack/'HD').as_posix()]=sha(path);total+=w*h;pages_count+=1
            # Exercise the real BC7 decoder for every page. Retain one for quality sampling.
            image=dds(data[8:],w,h)
            if page_index==0:decoded=image
        for line,expected in zip(lines[1+count:],record['frames']):
            frame=tuple(map(int,line.split()));assert frame==tuple(expected)
            pi,x,y,w,h,cx,cy=frame;assert 0<=pi<count and x>=0 and y>=0 and w>=0 and h>=0 and cx+w<=lw*4 and cy+h<=lh*4
            name,pw,ph=lines[1+pi].split();assert x+w<=int(pw) and y+h<=int(ph)
        prepared=custom/'HD'/rel
        if prepared.exists():
            frame=next((f for f in record['frames'] if f[0]==0 and f[3] and f[4]),None)
            assert frame is not None
            index=record['frames'].index(frame);column,row=index//rows,index%rows
            pi,x,y,w,h,cx,cy=frame
            with Image.open(prepared) as source:
                reference=source.convert('RGBA').crop((column*lw*4+cx,row*lh*4+cy,column*lw*4+cx+w,row*lh*4+cy+h))
            actual=decoded.crop((x,y,x+w,y+h));difference=ImageChops.difference(reference,actual)
            rgba=ImageStat.Stat(difference).rms
            visible=reference.getchannel('A').point(lambda alpha:255 if alpha>16 else 0)
            visible_rms=ImageStat.Stat(difference.convert('RGB'),visible).rms
            rgb=math.sqrt(sum(v*v for v in visible_rms)/3)
            assert rgb<20 and rgba[3]<20,(rel,rgba)
            qualities[rel]={'rgb_rmse':round(rgb,4),'alpha_rmse':round(rgba[3],4)}
    assert len(qualities)==85,len(qualities)
    assert total==sum(v['gpu_bytes'] for v in proof.values())
    result={'sheets':len(proof),'pages':pages_count,'texture_bytes':total,'density':4,'cpu_player_rgba_bytes':0,'files':files,'source_png_hashes':{p:r['source_sha256'] for p,r in proof.items()},'layout_sha256':sha(hd/'layouts.csv'),'quality_samples':qualities,'worst_rgb_rmse':max(v['rgb_rmse'] for v in qualities.values()),'worst_alpha_rmse':max(v['alpha_rmse'] for v in qualities.values())}
    (pack/'validated-gpu-pack.json').write_text(json.dumps(result,indent=2))
    (pack/'gpu-pack-proof.json').write_text(json.dumps(proof,indent=2))
    print('PASS: 255 BC7 sheets;',pages_count,'pages;',round(total/2**30,3),'GiB; grids, anchors/table, source hashes and 85 quality samples verified')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['pack','hd','custom']:p.add_argument(name,type=Path)
    p.add_argument('--proofs',nargs='+',default=['gpu-pack-proof.json','gpu-pack-medium-proof.json','gpu-pack-heavy-proof.json'])
    a=p.parse_args();validate(a.pack,a.hd,a.custom,a.proofs)
