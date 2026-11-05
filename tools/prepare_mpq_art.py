"""Prepare private MPQ art at native 4x; never commit extracted inputs/outputs."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import struct
from PIL import Image


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_palette(path):
    data=path.read_bytes()
    if data.startswith(b'JASC-PAL'):
        lines=data.decode('ascii').splitlines()
        assert lines[:3]==['JASC-PAL','0100','256'] and len(lines)==259
        colors=[int(v) for line in lines[3:] for v in line.split()]
        assert len(colors)==768 and all(0<=v<=255 for v in colors)
        return bytes(colors)
    assert len(data)==768, 'Unsupported palette: '+str(path)
    return data


def groups(data):
    """Validate CEL list/group offsets before decoding any pixels."""
    def word(offset):
        assert 0 <= offset <= len(data)-4, 'Truncated CEL header'
        return struct.unpack_from('<I',data,offset)[0]
    first=word(0)
    if 0 < first < len(data)//4 and word(4*(first+1)) == len(data):
        starts=[0]
    else:
        assert first%4==0 and 0 < first <= len(data)-4
        starts=[word(i) for i in range(0,first,4)]
    result=[]
    for group,start in enumerate(starts):
        end=starts[group+1] if group+1<len(starts) else len(data)
        count=word(start)
        assert 0 < count <= 16384 and start+4*(count+2)<=end
        offsets=[word(start+4*i) for i in range(1,count+2)]
        assert offsets[0]>=4*(count+2) and start+offsets[-1]==end
        assert all(a<=b for a,b in zip(offsets,offsets[1:]))
        result.append([data[start+a:start+b] for a,b in zip(offsets,offsets[1:])])
    return result


def cel_frame(data,width,has_header=True,expected_height=None):
    if has_header and len(data)>=10 and struct.unpack_from('<H',data)[0]==10:
        data=data[10:]
    pixels=bytearray();alpha=bytearray();position=0
    while position<len(data) and (expected_height is None or len(pixels)<width*expected_height):
        control=data[position];position+=1
        assert control, 'Zero CEL run'
        length=control if control<128 else 256-control
        assert length<=width-len(pixels)%width, 'CEL run crosses row boundary'
        if control<128:
            assert position+length<=len(data)
            pixels.extend(data[position:position+length]);alpha.extend([255]*length);position+=length
        else:
            pixels.extend(bytes(length));alpha.extend(bytes(length))
    assert len(pixels)%width==0 and pixels
    if expected_height is not None:
        assert len(pixels)==width*expected_height
        assert len(data)-position<=3 and not any(data[position:]), 'Nonzero tile alignment padding'
    height=len(pixels)//width
    return Image.frombytes('L',(width,height),bytes(pixels)).transpose(Image.Transpose.FLIP_TOP_BOTTOM), Image.frombytes('L',(width,height),bytes(alpha)).transpose(Image.Transpose.FLIP_TOP_BOTTOM)


def header_width(decoded):
    """CEL header offsets mark 32-row boundaries, establishing stored width.

    Require every available header block in every frame to agree; never choose
    a width from plausible dimensions or an image preview.
    """
    widths=set()
    for group in decoded:
        for data in group:
            if len(data)<10 or struct.unpack_from('<H',data)[0]!=10:continue
            offsets=[v for v in struct.unpack_from('<5H',data) if v]
            assert offsets==sorted(set(offsets)) and offsets[-1]<=len(data)
            for start,end in zip(offsets,offsets[1:]):
                position=start;pixels=0
                while position<end:
                    control=data[position];position+=1
                    assert control
                    pixels+=control if control<128 else 256-control
                    if control<128:position+=control
                assert position==end and pixels%32==0
                widths.add(pixels//32)
    assert len(widths)==1 and 0<next(iter(widths))<=4096, 'CEL header blocks do not establish one width'
    return next(iter(widths))


def tile_frame(data,kind):
    if kind==1:
        indices,mask=cel_frame(data,32,False,32)
        assert indices.height==32
        return indices,mask
    assert kind in (0,2,3,4,5)
    indices=Image.new('L',(32,32));mask=Image.new('L',(32,32));offset=0
    widths=[32]*32 if kind==0 else list(range(2,33,2))+(list(range(30,1,-2)) if kind in (2,3) else [32]*16)
    for row,width in enumerate(widths):
        shaped=kind in (2,3) or (kind in (4,5) and row<16)
        padding=shaped and row%2==0
        if padding and kind in (2,4):offset+=2
        assert offset+width<=len(data)
        x=32-width if kind in (2,4) else 0
        indices.paste(Image.frombytes('L',(width,1),data[offset:offset+width]),(x,31-row))
        mask.paste(255,(x,31-row,x+width,32-row));offset+=width
        if padding and kind in (3,5):offset+=2
    assert offset==len(data), f'Tile type {kind}: consumed {offset}, size {len(data)}'
    return indices,mask


def rgba(indices,mask,palette):
    image=indices.convert('P');image.putpalette(palette)
    image=image.convert('RGBA');image.putalpha(mask)
    return image


def widths_catalog(repo):
    # Literal UI widths below are taken from the corresponding engine loaders.
    widths={
        'ctrlpan/panel8':640,'ctrlpan/talkpanl':640,'ctrlpan/p8bulbs':88,
        'ctrlpan/panel8bu':71,'ctrlpan/p8but2':33,'ctrlpan/talkbutt':61,'ctrlpan/spelicon':56,
        'data/charbut':[95,41,41,41,41,41,41,41,41], 'data/quest':320,
        'data/spellbk':320,'data/spellbkb':76,'data/spelli2':37,
        'data/square':64,'data/diabsmal':296,'data/pentspin':48,'data/pentspn2':12,
        'data/option':27,'data/optbar':287,'data/textbox':591,'data/textbox2':271,
        'data/textslid':12,'ctrlpan/golddrop':261,
        'data/inv/inv':320,'data/inv/inv_rog':320,'data/inv/inv_sor':320,
        'towners/animals/cow':128,
        # Legacy widths verified against diasurgical/devilution's original
        # Source/control.cpp and Source/gmenu.cpp, not inferred from file size.
        'ctrlpan/smaltext':13,'data/char':320,'data/bigtgold':46,'data/medtexts':22,
    }
    cursor=repo/'assets/data/inv/objcurs-widths.txt'
    widths['data/inv/objcurs']=[int(s) for s in cursor.read_text().splitlines() if s.strip()]
    with (repo/'assets/txtdata/objects/objdat.tsv').open(encoding='utf-8-sig',newline='') as f:
        for row in csv.DictReader(f,delimiter='\t'):
            key='objects/'+row['file'].lower();value=int(row['animWidth'])
            if not value:continue
            assert key not in widths or widths[key]==value
            widths[key]=value
    with (repo/'assets/txtdata/towners/towners.tsv').open(encoding='utf-8-sig',newline='') as f:
        for row in csv.DictReader(f,delimiter='\t'):
            if row['animPath']:
                widths[row['animPath'].lower().replace('\\','/')]=int(row['animWidth'])
    return widths


def prepare(raw,repo,output,resume=False):
    Image.MAX_IMAGE_PIXELS=None
    assert not output.exists() or resume, 'Use a new private output directory, or explicitly resume'
    output.mkdir(parents=True,exist_ok=resume)
    hd=output/'HD';hd.mkdir(exist_ok=resume)
    if not (hd/'layouts.csv').exists():(hd/'layouts.csv').write_text('path,layout\n')
    files={p.relative_to(raw).as_posix().lower():p for p in raw.rglob('*') if p.is_file()}
    palette_path=files['levels/towndata/town.pal']
    default_palette=palette_path.read_bytes();assert len(default_palette)==768
    widths=widths_catalog(repo);inventory={};manifest={};unresolved=[]
    if resume:
        inventory=json.loads((output/'inventory.json').read_text())
        manifest=json.loads((output/'source-manifest.json').read_text())
    def checkpoint():
        (output/'inventory.json').write_text(json.dumps(inventory,indent=2))
        (output/'source-manifest.json').write_text(json.dumps(manifest,indent=2))
        (output/'unresolved.json').write_text(json.dumps(unresolved,indent=2))
    def save(rel,frames,columns,rows,palette,details):
        cw=max(frame[0].width for frame in frames);ch=max(frame[0].height for frame in frames)
        image=Image.new('RGBA',(columns*cw,rows*ch))
        index_image=Image.new('LA',image.size)
        dimensions=[]
        for number,(indices,mask) in enumerate(frames):
            col,row=divmod(number,rows)
            position=(col*cw,row*ch+ch-indices.height)
            image.paste(rgba(indices,mask,palette),position)
            index_image.paste(Image.merge('LA',(indices,mask)),position)
            dimensions.append(list(indices.size))
        for folder,content in [('native',image),('indices',index_image)]:
            dst=output/folder/rel;dst.parent.mkdir(parents=True,exist_ok=True);content.save(dst)
        target=hd/rel;target.parent.mkdir(parents=True,exist_ok=True)
        image.resize((image.width*4,image.height*4),Image.Resampling.NEAREST).save(target)
        inventory[rel]=dict(columns=columns,rows=rows,source_density=4,width=cw,height=ch,size=[image.width*4,image.height*4])
        manifest[rel]=dict(**details,frame_sizes=dimensions,native_sha256=sha(output/'native'/rel),prepared_sha256=sha(target))
        checkpoint()
        print('PREPARED',rel,len(frames),'frames',flush=True)
    for name,path in sorted(files.items()):
        if name.split('/')[0] not in ('levels','ctrlpan','data','items','objects','towners','ui_art','gendata'):continue
        if path.suffix.lower() not in ('.cel','.pcx'):continue
        rel=str(Path(name).with_suffix('.png')).replace('\\','/')
        if rel in manifest:
            assert sha(path)==manifest[rel]['source_sha256'] and sha(hd/rel)==manifest[rel]['prepared_sha256']
            continue
        details=dict(source=name,source_sha256=sha(path))
        if path.suffix.lower()=='.pcx':
            with Image.open(path) as source:
                source.load();assert source.mode=='P'
                palette=source.getpalette();indices=source.copy();mask=Image.new('L',source.size,255)
                # These colour keys are explicit in the current engine loaders.
                key=250 if path.stem.lower() in ('logo','smlogo','focus','focus16','focus42') else (0 if path.stem.lower() in ('cursor','r1_gry') else None)
                if key is not None:mask=Image.frombytes('L',source.size,bytes(0 if v==key else 255 for v in source.tobytes()))
                cols=math.ceil(source.width/128);rows=math.ceil(source.height/128)
                frames=[]
                for col in range(cols):
                    for row in range(rows):
                        box=(col*128,row*128,min(source.width,(col+1)*128),min(source.height,(row+1)*128))
                        cell=Image.new('L',(128,128));alpha=Image.new('L',(128,128))
                        cell.paste(Image.frombytes('L',(box[2]-box[0],box[3]-box[1]),indices.crop(box).tobytes()),(0,0));alpha.paste(mask.crop(box),(0,0))
                        frames.append((cell,alpha))
                details.update(source_size=list(source.size),layout='source-image-128px-blocks',transparent_index=key)
                save(rel,frames,cols,rows,palette,details)
            continue
        key=name[:-4]
        if name.startswith('levels/') and key+'.min' in files:
            data=path.read_bytes();decoded=groups(data);assert len(decoded)==1
            kinds={}
            for (v,) in struct.iter_unpack('<H',files[key+'.min'].read_bytes()):
                if not v:continue
                frame=v&4095;kind=(v>>12)&7
                assert frame not in kinds or kinds[frame]==kind
                kinds[frame]=kind
            assert set(kinds)==set(range(1,len(decoded[0])+1))
            palette_name=key+'.pal' if key+'.pal' in files else key+'_1.pal'
            palette=read_palette(files[palette_name])
            frames=[tile_frame(b,kinds[i+1]) for i,b in enumerate(decoded[0])]
            # Store original frame order column-major, matching the GPU index.
            cols=math.ceil(len(frames)/128);rows=128
            frames.extend((Image.new('L',(32,32)),Image.new('L',(32,32))) for _ in range(cols*rows-len(frames)))
            details.update(palette=palette_name,original_frames=len(decoded[0]),tile_types=kinds,layout='microcells-source-frame-order')
            save(rel,frames,cols,rows,palette,details);continue
        width=widths.get(key)
        if name.startswith('gendata/'):width=640
        if name.startswith('items/') and '/map/' in name:width=640
        elif name.startswith('items/') and path.stem.lower()=='duricons':width=32
        elif name.startswith('items/'):width=96
        if name.startswith('levels/') and path.stem.lower().endswith('s'):width=64
        if not width:
            try:
                width=header_width(groups(path.read_bytes()))
                details['width_source']='all CEL header 32-row blocks agree'
            except (AssertionError,IndexError,struct.error) as error:
                unresolved.append(dict(**details,reason='Frame width not established: '+str(error)));continue
        try:
            decoded=groups(path.read_bytes());frame_groups=[]
            for group in decoded:
                assert not isinstance(width,list) or len(width)>=len(group)
                frame_groups.append([cel_frame(b,width[i] if isinstance(width,list) else width) for i,b in enumerate(group)])
            rows=max(map(len,frame_groups));cw=max(f[0].width for g in frame_groups for f in g)
            frames=[]
            for group in frame_groups:
                frames.extend(group);frames.extend((Image.new('L',(cw,1)),Image.new('L',(cw,1))) for _ in range(rows-len(group)))
            palette_name=key+'.pal' if key+'.pal' in files else 'levels/towndata/town.pal'
            palette=read_palette(files[palette_name])
            details.update(palette=palette_name,group_counts=list(map(len,decoded)),layout='animation-groups')
            details.setdefault('width_source','engine loader/TSV or original-engine UI reference')
            save(rel,frames,len(decoded),rows,palette,details)
        except (AssertionError,IndexError,struct.error) as error:
            unresolved.append(dict(**details,reason='Strict CEL validation failed: '+str(error)))
    (output/'inventory.json').write_text(json.dumps(inventory,indent=2))
    (output/'source-manifest.json').write_text(json.dumps(manifest,indent=2))
    (output/'unresolved.json').write_text(json.dumps(unresolved,indent=2))
    print('PREPARED',len(inventory),'sheets; UNRESOLVED',len(unresolved),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('raw',type=Path);parser.add_argument('repo',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--resume',action='store_true')
    args=parser.parse_args();prepare(args.raw,args.repo,args.output,args.resume)
