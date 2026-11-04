"""Lossless layered town authoring with native fragment identities.

Create a private OpenRaster project from the user's atlas/MIN/native cell map.
Export edited ORA layers back into the original sheet, rejecting shared-frame
conflicts and changes to the engine's native alpha coverage. No game writes.
"""
import argparse
from collections import defaultdict
import hashlib
from io import BytesIO
import json
from pathlib import Path
import shutil
import struct
import xml.etree.ElementTree as ET
import zipfile
import zlib

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS=None  # The authored atlas/canvas dimensions are checked below.


def digest(image):
    return hashlib.sha256(image.convert('RGBA').tobytes()).hexdigest()


def png(image):
    stream=BytesIO();image.save(stream,format='PNG');return stream.getvalue()


def fragments(micros,cells,rows=128):
    result=[]
    for (x,z),piece in sorted(cells.items(),key=lambda item:(sum(item[0]),item[0][0])):
        if not 0<=piece<len(micros):raise ValueError('MIN piece outside table')
        for block in range(16):
            value=int(micros[piece,14+(block&1)-(block&14)])
            frame=value&4095
            if not frame:continue
            col,row=divmod(frame-1,rows)
            result.append(dict(name=f'cell_{x}_{z}_block_{block}_frame_{frame}',
                               cell=[x,z],piece=piece,block=block,frame=frame,
                               column=col,row=row,type=(value>>12)&7,
                               world=[32*(x-z)-32+(block&1)*32,
                                      16*(x+z)-(block//2)*32-31]))
    return result


def write_composite(path,width,height,layers,frames,density):
    """Stream PNG stripes so a full 4x town needs no giant RGBA allocation."""
    stripe=128
    buckets=defaultdict(list)
    for layer in layers:
        top=layer['y'];bottom=top+frames[layer['frame']].height-1
        for band in range(top//stripe,bottom//stripe+1):buckets[band].append(layer)
    preview=Image.new('RGBA',(width//density,height//density))
    compressor=zlib.compressobj(3)
    with path.open('wb') as stream:
        stream.write(b'\x89PNG\r\n\x1a\n')
        def chunk(kind,data):
            stream.write(struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff))
        chunk(b'IHDR',struct.pack('>2I5B',width,height,8,6,0,0,0))
        for top in range(0,height,stripe):
            image=Image.new('RGBA',(width,min(stripe,height-top)))
            for layer in buckets[top//stripe]:
                image.alpha_composite(frames[layer['frame']],(layer['x'],layer['y']-top))
            small=image.resize((width//density,image.height//density),Image.Resampling.NEAREST)
            preview.paste(small,(0,top//density))
            data=np.asarray(image)
            for row in data:
                encoded=compressor.compress(b'\0'+row.tobytes())
                if encoded:chunk(b'IDAT',encoded)
        tail=compressor.flush()
        if tail:chunk(b'IDAT',tail)
        chunk(b'IEND',b'')
    return preview


def create(args):
    output=args.output.resolve()
    if output.exists():raise ValueError('Use a new project directory')
    atlas=Image.open(args.atlas).convert('RGBA')
    density=args.density;cell=32*density;rows=128
    if density not in (1,2,4,8,16) or atlas.width%cell or atlas.height!=rows*cell:raise ValueError('Atlas dimensions do not match native cells')
    columns=atlas.width//cell
    raw=args.minimum.read_bytes()
    if len(raw)%32:raise ValueError('Malformed MIN table')
    micros=np.frombuffer(raw,dtype='<u2').reshape(-1,16)
    objects=json.loads(args.objects.read_text());cells={}
    for obj in objects:
        for x,z,piece,_ in obj['source_cells']:
            if (x,z) in cells and cells[x,z]!=piece:raise ValueError('Conflicting source cells')
            cells[x,z]=piece
    layers=fragments(micros,cells,rows)
    if not layers or max(l['frame'] for l in layers)>columns*rows:raise ValueError('Frame outside atlas')
    left=min(l['world'][0] for l in layers);top=min(l['world'][1] for l in layers)
    right=max(l['world'][0]+32 for l in layers);bottom=max(l['world'][1]+32 for l in layers)
    # Keep dimensions divisible by density and stripe height in the pixel writer.
    width=(right-left)*density;height=((bottom-top+31)//32)*32*density
    for layer in layers:
        layer['x']=(layer['world'][0]-left)*density
        layer['y']=(layer['world'][1]-top)*density
    output.mkdir();(output/'frames').mkdir()
    shutil.copy2(args.atlas,output/'base-atlas.png')
    frames={};frame_records=[]
    for frame in range(1,columns*rows+1):
        col,row=divmod(frame-1,rows)
        image=atlas.crop((col*cell,row*cell,(col+1)*cell,(row+1)*cell))
        filename=f'frames/{frame:04}.png';image.save(output/filename)
        frames[frame]=image
        frame_records.append(dict(frame=frame,path=filename,pixel_sha256=digest(image)))
    root=ET.Element('image',w=str(width),h=str(height),name='Tristram - native layered canvas',version='0.0.3')
    stack=ET.SubElement(root,'stack',name='Native draw order - preserve positions')
    # OpenRaster lists the frontmost item first. Group only contiguous draw
    # diagonals; regrouping every roof above every tree would change occlusion.
    groups={}
    for layer in reversed(layers):
        diagonal=sum(layer['cell'])
        if diagonal not in groups:
            groups[diagonal]=ET.SubElement(stack,'stack',name=f'Draw diagonal {diagonal}',
                                           opacity='1.0',visibility='visible',**{'composite-op':'svg:src-over'})
        ET.SubElement(groups[diagonal],'layer',name=layer['name'],
                      src=f"data/frame-{layer['frame']:04}.png",x=str(layer['x']),y=str(layer['y']),
                      opacity='1.0',visibility='visible',**{'composite-op':'svg:src-over'})
    manifest=dict(format='d1r.town-canvas-v1',density=density,columns=columns,rows=rows,
                  cell=cell,canvas=[width,height],world_origin=[left,top],
                  atlas_size=list(atlas.size),base_atlas_sha256=hashlib.sha256(args.atlas.read_bytes()).hexdigest(),
                  minimum_sha256=hashlib.sha256(raw).hexdigest(),frames=frame_records,layers=layers,
                  note='Pixel editing only. Preserve names, positions, dimensions and native alpha. Shared edits must agree.')
    (output/'project.json').write_text(json.dumps(manifest,separators=(',',':')))
    preview=write_composite(output/'mergedimage.png',width,height,layers,frames,density)
    preview.save(output/'town-native-preview.png')
    preview.thumbnail((2400,1600));preview.save(output/'town-preview.png')
    thumb=preview.copy();thumb.thumbnail((256,256))
    with zipfile.ZipFile(output/'Tristram-layered.ora','w',allowZip64=True) as archive:
        archive.writestr('mimetype','image/openraster',compress_type=zipfile.ZIP_STORED)
        archive.writestr('stack.xml',ET.tostring(root,encoding='utf-8',xml_declaration=True),compress_type=zipfile.ZIP_DEFLATED)
        for frame in sorted({l['frame'] for l in layers}):
            archive.write(output/f'frames/{frame:04}.png',f'data/frame-{frame:04}.png')
        archive.write(output/'mergedimage.png','mergedimage.png')
        archive.writestr('Thumbnails/thumbnail.png',png(thumb))
    print(json.dumps(dict(canvas=[width,height],layers=len(layers),unique_frames=len({l['frame'] for l in layers}),project=str(output))))


def edited_layers(root):
    def walk(node,x=0,y=0):
        x+=int(node.get('x','0'));y+=int(node.get('y','0'))
        if float(node.get('opacity','1'))!=1 or node.get('composite-op','svg:src-over')!='svg:src-over':
            raise ValueError('Opacity/blend changes cannot be baked into native tile identities')
        if node.tag=='layer':yield node,x,y
        else:
            for child in node:yield from walk(child,x,y)
    yield from walk(root)


def export(args):
    project=args.project.resolve();manifest=json.loads((project/'project.json').read_text())
    if manifest['format']!='d1r.town-canvas-v1':raise ValueError('Unsupported project')
    if hashlib.sha256((project/'base-atlas.png').read_bytes()).hexdigest()!=manifest['base_atlas_sha256']:
        raise ValueError('Base atlas changed; create a new project instead')
    if args.output.exists():raise ValueError('Use a new output directory')
    expected={l['name']:l for l in manifest['layers']};seen=set();variants={};conflicts=set();changed=[]
    base=Image.open(project/'base-atlas.png').convert('RGBA');cell=manifest['cell'];rows=manifest['rows']
    original={};cache={}
    with zipfile.ZipFile(args.ora) as archive:
        root=ET.fromstring(archive.read('stack.xml'))
        if [int(root.get('w')),int(root.get('h'))]!=manifest['canvas']:raise ValueError('Canvas resized')
        ordered=list(edited_layers(root))
        if [l.get('name') for l,_,_ in ordered]!=[l['name'] for l in reversed(manifest['layers'])]:
            raise ValueError('Layer order/names changed; preserve native draw order')
        for layer,x,y in ordered:
            name=layer.get('name')
            if name not in expected or name in seen:raise ValueError('Unknown or duplicate layer: '+str(name))
            seen.add(name);record=expected[name];frame=record['frame'];src=layer.get('src')
            if src not in cache:
                info=archive.getinfo(src)
                if info.file_size>4*cell*cell+1048576:raise ValueError('Oversized layer image')
                with Image.open(BytesIO(archive.read(src))) as im:
                    if im.width>cell or im.height>cell:raise ValueError('Layer resized')
                    cache[src]=im.convert('RGBA')
            image=cache[src];dx=x-record['x'];dy=y-record['y']
            if dx<0 or dy<0 or dx+image.width>cell or dy+image.height>cell:raise ValueError('Layer moved or extends outside its source cell')
            restored=Image.new('RGBA',(cell,cell));restored.paste(image,(dx,dy))
            if frame not in original:
                col,row=divmod(frame-1,rows);original[frame]=base.crop((col*cell,row*cell,(col+1)*cell,(row+1)*cell))
            # Terrain's native coverage remains the occlusion authority.
            if not np.array_equal(np.asarray(restored)[:,:,3],np.asarray(original[frame])[:,:,3]):
                raise ValueError(f'Alpha coverage changed in {name}; native occlusion would no longer match')
            # Editors can discard RGB under fully transparent texels. Retain
            # those source bytes rather than inventing conflicts between crops.
            pixels=np.array(restored);source=np.asarray(original[frame]);transparent=source[:,:,3]==0
            pixels[transparent]=source[transparent];restored=Image.fromarray(pixels)
            value=digest(restored)
            if frame in variants and variants[frame][0]!=value:conflicts.add(frame)
            else:variants[frame]=(value,restored)
    if seen!=set(expected):raise ValueError('Missing source layers')
    if conflicts:raise ValueError('Shared-frame edits disagree: '+','.join(map(str,sorted(conflicts))))
    for frame,(value,image) in variants.items():
        if value!=digest(original[frame]):changed.append(frame)
        col,row=divmod(frame-1,rows);base.paste(image,(col*cell,row*cell))
    args.output.mkdir(parents=True)
    base.save(args.output/'town.png')
    report=dict(source_layers=len(seen),changed_frames=sorted(changed),alpha_unchanged=True,
                shared_frame_conflicts=0,atlas_size=list(base.size),
                pixel_sha256=digest(base),installed=False)
    (args.output/'export-report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report))


def region(args):
    """Flatten an editable local view, retaining a per-pixel source address."""
    project=args.project.resolve();m=json.loads((project/'project.json').read_text())
    if args.output.exists():raise ValueError('Use a new region directory')
    left,top,width,height=args.rect;density=m['density'];cell=m['cell']
    if width<=0 or height<=0:raise ValueError('Invalid region size')
    image=Image.new('RGBA',(width*density,height*density))
    owners=np.zeros((height*density,width*density),dtype=np.uint32);cache={}
    for layer in m['layers']:
        x=(layer['world'][0]-left)*density;y=(layer['world'][1]-top)*density
        if x>=image.width or y>=image.height or x+cell<=0 or y+cell<=0:continue
        frame=layer['frame']
        if frame not in cache:cache[frame]=Image.open(project/f'frames/{frame:04}.png').convert('RGBA')
        tile=cache[frame];image.alpha_composite(tile,(x,y))
        x0,y0=max(0,x),max(0,y);x1,y1=min(image.width,x+cell),min(image.height,y+cell)
        sx,sy=x0-x,y0-y
        alpha=np.asarray(tile)[sy:sy+y1-y0,sx:sx+x1-x0,3]
        yy,xx=np.mgrid[sy:sy+y1-y0,sx:sx+x1-x0]
        address=1+frame*cell*cell+yy*cell+xx
        dest=owners[y0:y1,x0:x1]
        # Partial alpha mixes two sources: keep it unpaintable rather than
        # pretending the composite colour belongs to just the top fragment.
        dest[alpha>0]=0;opaque=alpha==255;dest[opaque]=address[opaque]
    args.output.mkdir(parents=True)
    image.save(args.output/'paint.png');image.save(args.output/'reference.png')
    np.savez_compressed(args.output/'owners.npz',owners=owners)
    (args.output/'region.json').write_text(json.dumps(dict(project=str(project),rect=args.rect,
        density=density,reference_sha256=digest(image),
        frame_hashes={str(f):digest(im) for f,im in cache.items()},
        owners_sha256=hashlib.sha256((args.output/'owners.npz').read_bytes()).hexdigest(),
        policy='Apply RGB edits to their source pixels and propagate shared fragments throughout town.'),indent=2))
    preview=image.copy();preview.thumbnail((1400,1000));preview.save(args.output/'preview.png')
    print(json.dumps(dict(region=str(args.output.resolve()),editable_pixels=int((owners>0).sum()))))


def apply_region(args):
    """Re-slice a flat paint edit; a reused source pixel must have one colour."""
    meta=json.loads((args.region/'region.json').read_text());project=Path(meta['project'])
    if args.output.resolve().is_relative_to(project.resolve()):raise ValueError('Edited project must be outside its source project')
    m=json.loads((project/'project.json').read_text());cell=m['cell']
    for frame,value in meta['frame_hashes'].items():
        if digest(Image.open(project/f'frames/{int(frame):04}.png'))!=value:raise ValueError('Region is stale: source frame changed')
    if hashlib.sha256((args.region/'owners.npz').read_bytes()).hexdigest()!=meta['owners_sha256']:
        raise ValueError('Region source address map changed')
    reference=Image.open(args.region/'reference.png').convert('RGBA')
    if digest(reference)!=meta['reference_sha256']:raise ValueError('Region reference was modified')
    with Image.open(args.edited) as image:
        if image.size!=reference.size:raise ValueError('Paint image resized')
        edited=np.array(image.convert('RGBA'))
    source=np.asarray(reference);owners=np.load(args.region/'owners.npz')['owners']
    if not np.array_equal(source[:,:,3],edited[:,:,3]):raise ValueError('Paint changed alpha coverage')
    changed=np.any(source[:,:,:3]!=edited[:,:,:3],axis=2)&(source[:,:,3]>0)
    if np.any(changed&(owners==0)):raise ValueError('Paint changed mixed-alpha/unowned pixels')
    addresses=owners[changed];colours=edited[changed]
    order=np.argsort(addresses);addresses=addresses[order];colours=colours[order]
    if len(addresses)>1:
        conflict=(addresses[1:]==addresses[:-1])&np.any(colours[1:]!=colours[:-1],axis=1)
        if conflict.any():raise ValueError('Shared source pixel painted different colours within region')
    if args.output.exists():raise ValueError('Use a new edited project directory')
    unique=np.r_[True,addresses[1:]!=addresses[:-1]] if len(addresses) else np.array([],dtype=bool)
    addresses=addresses[unique]-1;colours=colours[unique]
    frames=addresses//(cell*cell);pixels=addresses%(cell*cell)
    touched=sorted(map(int,np.unique(frames)))
    # Read all inputs before creating an output: invalid edits leave no project.
    updates={}
    for frame in touched:
        tile=Image.open(project/f'frames/{frame:04}.png').convert('RGBA');data=np.array(tile)
        selected=frames==frame;positions=pixels[selected]
        data[positions//cell,positions%cell]=colours[selected];updates[frame]=Image.fromarray(data)
    shutil.copytree(project,args.output,ignore=shutil.ignore_patterns('round-trip','compiled','regions','edited-*',
                    'candidate-source','validation.json','gpu-upload.log','empty.log'))
    for frame,tile in updates.items():tile.save(args.output/f'frames/{frame:04}.png')
    with zipfile.ZipFile(project/'Tristram-layered.ora') as original,zipfile.ZipFile(args.output/'Tristram-layered.ora','w',allowZip64=True) as target:
        for entry in original.infolist():
            if entry.filename in ('mergedimage.png','Thumbnails/thumbnail.png'):continue
            frame=int(Path(entry.filename).stem.removeprefix('frame-')) if entry.filename.startswith('data/frame-') else None
            target.writestr(entry,png(updates[frame]) if frame in updates else original.read(entry.filename))
        images={f['frame']:Image.open(args.output/f['path']).convert('RGBA') for f in m['frames']}
        preview=write_composite(args.output/'mergedimage.png',*m['canvas'],m['layers'],images,m['density'])
        target.write(args.output/'mergedimage.png','mergedimage.png')
        thumb=preview.copy();thumb.thumbnail((256,256));target.writestr('Thumbnails/thumbnail.png',png(thumb))
    preview.save(args.output/'town-native-preview.png');preview.thumbnail((2400,1600));preview.save(args.output/'town-preview.png')
    report=dict(changed_visible_pixels=int(changed.sum()),changed_source_pixels=len(addresses),
                touched_frames=touched,propagated_world_layers=sum(l['frame'] in touched for l in m['layers']),
                alpha_unchanged=True,installed=False)
    (args.output/'paint-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('create')
    for name in ('atlas','minimum','objects','output'):p.add_argument(name,type=Path)
    p.add_argument('--density',type=int,default=4);p.set_defaults(run=create)
    p=sub.add_parser('export')
    for name in ('project','ora','output'):p.add_argument(name,type=Path)
    p.set_defaults(run=export)
    p=sub.add_parser('region')
    p.add_argument('project',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--rect',type=int,nargs=4,required=True,metavar=('LEFT','TOP','WIDTH','HEIGHT'))
    p.set_defaults(run=region)
    p=sub.add_parser('apply-region')
    for name in ('region','edited','output'):p.add_argument(name,type=Path)
    p.set_defaults(run=apply_region)
    args=parser.parse_args();args.run(args)
