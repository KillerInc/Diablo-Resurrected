"""Offline, cropped 4x BC7 pages. Input/output art must stay private."""
import argparse,json,re,struct,sys
from pathlib import Path
from PIL import Image
from hd_layouts import read_table
from install_layout_table import sha


def constant_blocks(image,bc,settings,cache):
    """Native-4x nearest-neighbour art has solid 4x4 BC7 blocks.

    Encode each distinct colour once with the same BC7 encoder/profile, then
    reuse that block. Fall back if any block contains more than one colour.
    """
    import numpy as np
    pixels=np.asarray(image);samples=pixels[::4,::4]
    if any(not np.array_equal(pixels[y::4,x::4],samples) for y in range(4) for x in range(4)):
        return None
    colors,indices=np.unique(samples.reshape(-1,4).view('<u4').ravel(),return_inverse=True)
    missing=[int(color) for color in colors if int(color) not in cache]
    if missing:
        rgba=np.asarray(missing,dtype='<u4').view('u1').reshape(-1,4)
        strip=np.broadcast_to(np.repeat(rgba,4,axis=0)[None,:,:],(4,len(missing)*4,4)).copy()
        encoded=bc.compress_blocks_bc7(bc.RGBASurface(strip.tobytes(),len(missing)*4,4),settings)
        assert len(encoded)==16*len(missing)
        cache.update((color,encoded[i*16:(i+1)*16]) for i,color in enumerate(missing))
    blocks=np.frombuffer(b''.join(cache[int(color)] for color in colors),dtype='u1').reshape(-1,16)
    return blocks[indices].tobytes()


def pack(hd,custom,log,output,encoder_path,only=None,proof_name="gpu-pack-proof.json", inventory=None, page_size=2048, solid_blocks=False, encoder_profile='alpha_fast'):
    assert page_size in (2048,4096), 'Supported offline page sizes: 2048, 4096'
    sys.path.insert(0,str(encoder_path));import ispc_texcomp as bc
    assert encoder_profile in ('alpha_fast','alpha_basic','alpha_slow')
    settings=bc.BC7EncSettings.from_profile(encoder_profile)
    Image.MAX_IMAGE_PIXELS=None
    layouts=read_table(hd/'layouts.csv')
    grids={p.removeprefix('hd/'):(int(c),int(r)) for p,c,r in re.findall(r'Loaded HD sheet: (hd/[^ ]+) \([^\n]*?, (\d+) directions, (\d+) frames,',log.read_text(errors='replace'))}
    if inventory is not None:
        grids={name:(v['columns'],v['rows']) for name,v in inventory.items()}
    proof_file=output/proof_name
    assert Path(proof_name).name==proof_name
    proofs=json.loads(proof_file.read_text()) if proof_file.exists() else {}
    block_cache={}
    for number,(rel,(cols,rows)) in enumerate(sorted(grids.items()),1):
        if (inventory is None and not rel.startswith('plrgfx/warrior/')) or (only and Path(rel).stem not in only):continue
        source=hd/rel; authored=custom/'HD'/rel
        path=authored if authored.exists() else source
        source_density=inventory[rel]['source_density'] if inventory is not None else (4 if authored.exists() else 8)
        image=Image.open(path).convert('RGBA');cw,ch=image.width//cols,image.height//rows
        assert image.width%cols==image.height%rows==0 and cw%source_density==ch%source_density==0
        lw,lh=cw//source_density,ch//source_density
        dst=output/'HD'/rel;dst.parent.mkdir(parents=True,exist_ok=True)
        meta=dst.with_suffix('.gpus')
        if meta.exists():
            assert rel in proofs, 'Existing sheet has no proof: '+rel
            assert proofs[rel]['encoder_profile']==encoder_profile, 'Encoder profile changed: use a new output pack'
            assert proofs[rel]['source_sha256']==sha(source) and proofs[rel]['prepared_sha256']==sha(path), 'Input changed: use a new output pack for '+rel
            continue
        pages=[];frames=[];page=Image.new('RGBA',(page_size,page_size));x=y=rowh=0
        def finish():
            nonlocal page,x,y,rowh
            height=max(4,((y+rowh+3)//4)*4)
            trimmed=page.crop((0,0,page_size,height))
            data=constant_blocks(trimmed,bc,settings,block_cache) if solid_blocks else None
            if data is None:data=bc.compress_blocks_bc7(bc.RGBASurface(trimmed.tobytes(),page_size,height),settings)
            assert len(data)==page_size*height
            index=len(pages);name=dst.with_suffix(f'.p{index}.bc7')
            name.write_bytes(struct.pack('<II',page_size,height)+data)
            pages.append((name.name,page_size,height,len(data)))
            page=Image.new('RGBA',(page_size,page_size));x=y=rowh=0
        for col in range(cols):
            for row in range(rows):
                cell=image.crop((col*cw,row*ch,(col+1)*cw,(row+1)*ch))
                if source_density!=4:cell=cell.resize((lw*4,lh*4),Image.Resampling.NEAREST)
                box=cell.getchannel('A').getbbox()
                if box is None:frames.append((0,0,0,0,0,0,0));continue
                left,top,right,bottom=box
                # 4-texel transparent gutter; BC7 blocks cannot mix adjacent frames.
                w=((right-left+8+3)//4)*4;h=((bottom-top+8+3)//4)*4
                assert w<=page_size and h<=page_size
                if x+w>page_size:x=0;y+=rowh;rowh=0
                if y+h>page_size:finish()
                page.paste(cell.crop(box),(x+4,y+4))
                frames.append((len(pages),x+4,y+4,right-left,bottom-top,left,top))
                x+=w;rowh=max(rowh,h)
        finish()
        with meta.open('w',newline='\n') as f:
            f.write(f'D1R_GPU_SHEET_V1 4 {cols} {rows} {lw} {lh} {len(pages)}\n')
            for name,w,h,size in pages:f.write(f'{name} {w} {h}\n')
            for frame in frames:f.write(' '.join(map(str,frame))+'\n')
        proofs[rel]={'source_sha256':sha(source),'prepared_sha256':sha(path),'columns':cols,'rows':rows,'density':4,'pages':len(pages),'gpu_bytes':sum(p[3] for p in pages),'rgba_equivalent':lw*lh*16*4*cols*rows,'frames':frames,'encoder_profile':encoder_profile}
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
    p.add_argument('--inventory',type=Path,help='Validated original-CL2 grids for arbitrary installed world sheets')
    p.add_argument('--proof-name',default='gpu-pack-proof.json')
    p.add_argument('--finalize-index',action='store_true',help='After all workers finish, publish the one runtime index')
    p.add_argument('--page-size',type=int,choices=(2048,4096),default=2048)
    p.add_argument('--solid-blocks',action='store_true',help='Reuse identical native-4x solid BC7 blocks; requires numpy')
    p.add_argument('--encoder-profile',choices=('alpha_fast','alpha_basic','alpha_slow'),default='alpha_fast')
    a=p.parse_args();pack(a.hd,a.custom,a.log,a.output,a.encoder_path,a.only,a.proof_name,json.loads(a.inventory.read_text()) if a.inventory else None,a.page_size,a.solid_blocks,a.encoder_profile)
    if a.finalize_index:
        from gpu_index import consolidate
        consolidate(a.output/'HD')
