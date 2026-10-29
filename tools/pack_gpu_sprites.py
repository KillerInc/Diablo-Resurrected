"""Offline, cropped 4x BC7 pages. Input/output art must stay private."""
import argparse,json,re,struct,sys
from pathlib import Path
from PIL import Image
from hd_layouts import read_table
from install_layout_table import sha


def pack(hd,custom,log,output,encoder_path,only=None,proof_name="gpu-pack-proof.json"):
    sys.path.insert(0,str(encoder_path));import ispc_texcomp as bc
    settings=bc.BC7EncSettings.from_profile('alpha_fast')
    Image.MAX_IMAGE_PIXELS=None
    layouts=read_table(hd/'layouts.csv')
    grids={p.removeprefix('hd/'):(int(c),int(r)) for p,c,r in re.findall(r'Loaded HD sheet: (hd/[^ ]+) \([^\n]*?, (\d+) directions, (\d+) frames,',log.read_text(errors='replace'))}
    proof_file=output/proof_name
    assert Path(proof_name).name==proof_name
    proofs=json.loads(proof_file.read_text()) if proof_file.exists() else {}
    for number,(rel,(cols,rows)) in enumerate(sorted(grids.items()),1):
        if not rel.startswith('plrgfx/warrior/') or (only and Path(rel).stem not in only):continue
        source=hd/rel; authored=custom/'HD'/rel
        path=authored if authored.exists() else source
        source_density=4 if authored.exists() else 8
        image=Image.open(path).convert('RGBA');cw,ch=image.width//cols,image.height//rows
        assert image.width%cols==image.height%rows==0 and cw%source_density==ch%source_density==0
        lw,lh=cw//source_density,ch//source_density
        dst=output/'HD'/rel;dst.parent.mkdir(parents=True,exist_ok=True)
        meta=dst.with_suffix('.gpus')
        if meta.exists():
            assert rel in proofs, 'Existing sheet has no proof: '+rel
            continue
        pages=[];frames=[];page=Image.new('RGBA',(2048,2048));x=y=rowh=0
        def finish():
            nonlocal page,x,y,rowh
            height=max(4,((y+rowh+3)//4)*4)
            trimmed=page.crop((0,0,2048,height))
            data=bc.compress_blocks_bc7(bc.RGBASurface(trimmed.tobytes(),2048,height),settings)
            assert len(data)==2048*height
            index=len(pages);name=dst.with_suffix(f'.p{index}.bc7')
            name.write_bytes(struct.pack('<II',2048,height)+data)
            pages.append((name.name,2048,height,len(data)))
            page=Image.new('RGBA',(2048,2048));x=y=rowh=0
        for col in range(cols):
            for row in range(rows):
                cell=image.crop((col*cw,row*ch,(col+1)*cw,(row+1)*ch))
                if source_density!=4:cell=cell.resize((lw*4,lh*4),Image.Resampling.NEAREST)
                box=cell.getchannel('A').getbbox()
                if box is None:frames.append((0,0,0,0,0,0,0));continue
                left,top,right,bottom=box
                # 4-texel transparent gutter; BC7 blocks cannot mix adjacent frames.
                w=((right-left+8+3)//4)*4;h=((bottom-top+8+3)//4)*4
                assert w<=2048 and h<=2048
                if x+w>2048:x=0;y+=rowh;rowh=0
                if y+h>2048:finish()
                page.paste(cell.crop(box),(x+4,y+4))
                frames.append((len(pages),x+4,y+4,right-left,bottom-top,left,top))
                x+=w;rowh=max(rowh,h)
        finish()
        with meta.open('w',newline='\n') as f:
            f.write(f'D1R_GPU_SHEET_V1 4 {cols} {rows} {lw} {lh} {len(pages)}\n')
            for name,w,h,size in pages:f.write(f'{name} {w} {h}\n')
            for frame in frames:f.write(' '.join(map(str,frame))+'\n')
        proofs[rel]={'source_sha256':sha(source),'prepared_sha256':sha(path),'columns':cols,'rows':rows,'density':4,'pages':len(pages),'gpu_bytes':sum(p[3] for p in pages),'rgba_equivalent':lw*lh*16*4*cols*rows,'frames':frames,'encoder_profile':'alpha_fast'}
        proof_file.write_text(json.dumps(proofs,indent=2))
        print(f'{number}: {Path(rel).stem}: {len(pages)} pages, {sum(p[3] for p in pages)/2**20:.2f} MiB',flush=True)
    # Retain the single runtime anchor table, never sidecars.
    target=output/'HD/layouts.csv';target.parent.mkdir(parents=True,exist_ok=True)
    if not target.exists():target.write_bytes((hd/'layouts.csv').read_bytes())
    proof_file.write_text(json.dumps(proofs,indent=2))
    print('GPU pack bytes:',sum(p['gpu_bytes'] for p in proofs.values()),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['hd','custom','log','output','encoder_path']:p.add_argument(name,type=Path)
    p.add_argument('--only',nargs='+')
    p.add_argument('--proof-name',default='gpu-pack-proof.json')
    a=p.parse_args();pack(a.hd,a.custom,a.log,a.output,a.encoder_path,a.only,a.proof_name)
