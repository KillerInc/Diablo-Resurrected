"""Convert a private Diablo3D Tristram cache to editable mesh/texture inputs.

No game data or upstream implementation is embedded. Binary records are read
from their documented little-endian fields. Geometry remains in native tile
units; metadata retains original anchors, source cells and material identities.
"""
import argparse
import configparser
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import struct

import numpy as np
from PIL import Image


class Reader:
    def __init__(self, path):
        self.data = Path(path).read_bytes()
        self.offset = 0

    def take(self, size):
        if size < 0 or self.offset+size > len(self.data):
            raise ValueError('Truncated scene record')
        result = self.data[self.offset:self.offset+size]
        self.offset += size
        return result

    def unpack(self, fmt):
        return struct.unpack('<'+fmt, self.take(struct.calcsize('<'+fmt)))

    def text(self):
        size, = self.unpack('I')
        if size > 4096:
            raise ValueError('Oversized scene string')
        return self.take(size).decode('utf-8')


def transform(points, pivot, translation, yaw, scale, authored=(1,1,1)):
    c, s = math.cos(yaw), math.sin(yaw)
    p = (points-np.array(pivot))*np.array(authored)*scale
    x, z = p[:,0].copy(), p[:,2].copy()
    p[:,0], p[:,2] = c*x+s*z, -s*x+c*z
    return p+np.array(pivot)+np.array(translation)


def read_static(path, palette, output):
    r = Reader(path)
    assert r.take(8) == b'D3DSTAT1'
    version, gx, gz, textures, count = r.unpack('5I')
    assert version == 1 and gx == gz == 112 and textures <= 4096 and count <= 30000
    materials = []
    ground_shapes = []
    for i in range(textures):
        w, h, flags = r.unpack('3I')
        assert 0 < w <= 4096 and 0 < h <= 4096 and flags <= 3
        indices = np.frombuffer(r.take(w*h),dtype=np.uint8).reshape(h,w)
        alpha = np.frombuffer(r.take(w*h),dtype=np.uint8).reshape(h,w)*255 if flags & 2 else np.full((h,w),255,np.uint8)
        rgba = np.dstack((palette[indices], alpha))
        # Native floor rectangles overlap in world space. Remove alpha-zero
        # geometry before Blender depth testing; coplanar transparent quads
        # otherwise hide each other in both raster and ray-traced previews.
        strips=[]
        for row in range(h):
            covered=alpha[row]>0
            changes=np.diff(np.r_[False,covered,False].astype(np.int8))
            for left,right in zip(np.flatnonzero(changes==1),np.flatnonzero(changes==-1)):
                strips.append([(left/w,row/h),(right/w,row/h),
                               (right/w,(row+1)/h),(left/w,(row+1)/h)])
        ground_shapes.append(np.asarray(strips,dtype=np.float32).reshape(-1,4,2))
        name = f'native-{i:04}.png'
        Image.fromarray(rgba).save(output/'textures'/name)
        materials.append(dict(name=f'Native texture {i:04}',image='textures/'+name,repeat=bool(flags&1)))
    groups = defaultdict(list)
    objects, dpieces = [], {}
    triangle_dtype = np.dtype([('v','<f4',(3,5)),('meta','u1',(4,))])
    assert triangle_dtype.itemsize == 64
    for i in range(count):
        identity = r.text()
        kind, flags, phase, event = r.unpack('4B')
        ax, az = r.unpack('2I')
        tx, th, tz, yaw, scale = r.unpack('5f')
        tex, cells, triangles = r.unpack('3I')
        dimensions = r.unpack('3f')
        assert kind < 4 and tex < textures and cells <= 12544 and triangles <= 200000
        source = np.frombuffer(r.take(cells*8),dtype='<u2').reshape(-1,4).tolist()
        for x,z,piece,special in source:
            if (x,z) in dpieces:
                assert dpieces[x,z] == piece
            dpieces[x,z] = piece
        data = np.frombuffer(r.take(triangles*64),dtype=triangle_dtype)
        objects.append(dict(id=identity,kind=kind,flags=flags,phase=phase,event=event,
                            anchor=[ax,az],texture=tex,source_cells=source,triangles=triangles))
        if not flags & 2 or flags & 4:
            continue
        if kind == 0:
            # Ground draw is a native 64x32 footprint, independent of mesh payload.
            uv=ground_shapes[tex][:,[0,1,2,0,2,3]].reshape(-1,2)
            p=np.stack((-1.46875+uv[:,0]+uv[:,1],np.zeros(len(uv)),
                        -.46875-uv[:,0]+uv[:,1]),axis=1)
            p=transform(p,(0,0,0),(ax+tx,th,az+tz),yaw,scale)
            v=np.concatenate((p,uv),axis=1)
        else:
            v=data['v'].reshape(-1,5).copy()
            # Static volumes use a fixed sprite-ray frame, not world coordinates.
            x,depth=v[:,0].copy(),v[:,2].copy()
            v[:,0]=(x+depth)/math.sqrt(2)
            v[:,2]=(-x+depth)/math.sqrt(2)
            if not flags & 1:
                v[:,1]+=depth/math.sqrt(2)-1/32
            v[:,:3]=transform(v[:,:3],(0,0,0),(ax+tx,th,az+tz),yaw,scale)
        assert np.isfinite(v).all()
        groups[(tex,kind,phase)].append(v.astype(np.float32))
    assert r.offset == len(r.data), 'Trailing static bytes'
    return groups,materials,objects,dpieces


def read_model(path):
    r=Reader(path)
    assert r.take(8)==b'D3DVIS1\0'
    version,kind,flags=r.unpack('3I')
    assert version==1 and kind<7 and flags<=3
    minimum,maximum=r.unpack('2i'),r.unpack('2i')
    physical=r.unpack('5fI')
    reference,origin,size=r.unpack('2i'),r.unpack('2i'),r.unpack('2i')
    enabled,=r.unpack('I')
    artmin,artmax=r.unpack('2i'),r.unpack('2i')
    fringe_min,fringe_max,triangles,patches,width,height,adjunct=r.unpack('7I')
    provenance=[r.text() for _ in range(7)]
    assert triangles<=200000 and patches<=256 and width<=2048 and height<=2048
    dtype=np.dtype([('v','<f4',(3,5)),('material','<u4'),('source','<i4',(2,)),
                    ('pick','<i4',(2,)),('projected','<u4'),('normal','<f4',(3,)),
                    ('role','<u4'),('detail','<u4')])
    assert dtype.itemsize==104
    geometry=np.frombuffer(r.take(triangles*104),dtype=dtype).copy()
    r.take(patches*112)
    rgb=r.take(width*height*3)
    assert adjunct in (0,1)
    if not adjunct:
        assert r.offset==len(r.data)
    return dict(geometry=geometry,width=width,height=height,rgb=rgb,
                minimum=minimum,maximum=maximum,reference=reference,origin=origin,
                artwork_min=artmin,artwork_max=artmax,fringe=[fringe_min,fringe_max],
                kind=kind,flags=flags,adjunct_bytes=len(r.data)-r.offset,provenance=provenance)


def native_facade(model, dpieces, micros, sol, atlas):
    x0,z0=model['artwork_min'];x1,z1=model['artwork_max']
    dx,dz=x1-x0,z1-z0
    w,h=32*(dx+dz+2)+16,16*(dx+dz)+272
    origin=(32*(dz+1)+8,263)
    result=Image.new('RGBA',(w,h))
    cache={}
    for x,z in sorted(((x,z) for x in range(x0,x1+1) for z in range(z0,z1+1)),key=lambda p:(sum(p),p[0])):
        piece=dpieces.get((x,z),0)
        if piece>=len(micros):
            continue
        outside=not(model['minimum'][0]<=x<=model['maximum'][0] and model['minimum'][1]<=z<=model['maximum'][1])
        lo,hi=model['fringe']
        if (outside or model['kind'] in (3,5)) and lo and not lo<=piece<=hi:
            continue
        floor=not sol[piece]&5
        for i in range(16):
            block=int(micros[piece,14+(i&1)-(i&14)])
            frame=(block&4095)-1
            if frame<0 or (floor and i<2):
                continue
            if frame not in cache:
                col,row=divmod(frame,128)
                cache[frame]=atlas.crop((col*128,row*128,col*128+128,row*128+128)).resize((32,32),Image.Resampling.NEAREST)
            left=origin[0]-32+32*(x-x0-z+z0)+(i&1)*32
            top=origin[1]+16*(x-x0+z-z0)-(i//2)*32-31
            result.alpha_composite(cache[frame],(left,top))
    return result,origin,(x0,z0)


def convert(args):
    output=args.output.resolve();(output/'textures').mkdir(parents=True,exist_ok=True)
    palette=np.frombuffer((args.static/'palette.rgb').read_bytes(),dtype=np.uint8).reshape(256,3)
    groups,materials,objects,dpieces=read_static(args.static/'tristram.d3dvis',palette,output)
    archive={};meshes=[]
    for (tex,kind,phase),chunks in sorted(groups.items()):
        key=f'mesh{len(meshes)}';archive[key]=np.concatenate(chunks)
        meshes.append(dict(key=key,name=f'Native {kind} texture {tex:04} phase {phase}',material=tex,collection='Native terrain and scenery'))
    micros=np.frombuffer((args.native/'levels/towndata/town.min').read_bytes(),dtype='<u2').reshape(-1,16)
    sol=(args.native/'levels/towndata/town.sol').read_bytes()
    atlas=Image.open(args.atlas).convert('RGBA')
    manifest=configparser.ConfigParser(strict=False,interpolation=None)
    manifest.read(args.scene/'d3d-scenes/tristram.ini',encoding='utf-8')
    buildings=[]
    palette_reports=[]
    registrations={}
    if args.registrations:
        registration_data=json.loads(args.registrations.read_text())
        assert registration_data['format']=='d1r.tristram-registration-v1'
        registrations={identity:group for group in registration_data['groups'] if group['apply'] for identity in group['ids']}
    for identity in manifest.sections():
        if identity=='Scene':continue
        section=manifest[identity];path=args.scene/section['model'];raw=path.read_bytes()
        assert hashlib.sha256(raw).hexdigest()==section['sha256']
        model=read_model(path);data=model['geometry']
        if model['width']:
            filename=identity+'-basecolor.png'
            embedded=Image.frombytes('RGB',(model['width'],model['height']),model['rgb'])
            embedded.save(output/'textures'/filename)
            if args.native_palette:
                from native_palette import match_palette
                native_image,_,_=native_facade(model,dpieces,micros,sol,atlas)
                matched,report=match_palette(embedded,native_image,data['v'][:,:,3:5])
                filename=identity+'-native-palette.png'
                matched.save(output/'textures'/filename)
                palette_reports.append(dict(id=identity,**report))
        else:
            image,origin,reference=native_facade(model,dpieces,micros,sol,atlas)
            filename=identity+'-native-front.png';image.save(output/'textures'/filename)
        mat=len(materials);materials.append(dict(name=identity+' replaceable base color',image='textures/'+filename,repeat=False,architecture=True))
        # Keep distinct material surfaces for later replacement/retexturing.
        for material in np.unique(data['material']):
            selected=data[data['material']==material]
            v=selected['v'].reshape(-1,5).copy()
            if not model['width']:
                v[:,3]=(32*(v[:,0]-v[:,2]-reference[0]+reference[1])+origin[0])/image.width
                v[:,4]=(16*(v[:,0]+v[:,2]-reference[0]-reference[1])-32*v[:,1]+origin[1])/image.height
            pivot=tuple(map(float,section['pivot'].split(',')))
            translation=tuple(map(float,section['translation'].split(',')))
            authored=tuple(map(float,section.get('authoredscale','1,1,1').split(',')))
            v[:,:3]=transform(v[:,:3],pivot,translation,math.radians(float(section['yawdegrees'])),float(section['uniformscale']),authored)
            if identity in registrations:
                from register_buildings import apply_registration
                v[:,:3]=apply_registration(v[:,:3],registrations[identity])
            key=f'mesh{len(meshes)}';archive[key]=v
            meshes.append(dict(key=key,name=identity+f' surface {material}',material=mat,collection='Tristram buildings',building=identity,surface=int(material)))
        buildings.append(dict(id=identity,source=str(path),sha256=section['sha256'],native_min=model['minimum'],native_max=model['maximum'],triangles=len(data),embedded_texture=bool(model['width']),unimported_interior_bytes=model['adjunct_bytes']))
    np.savez_compressed(output/'meshes.npz',**archive)
    summary=dict(format='d1r.tristram-authoring-v1',grid=[112,112],native_projection={'x':'32*(x-z)','y':'16*(x+z)-32*height'},
                 blender_height_scale=math.sqrt(2/3),materials=materials,meshes=meshes,buildings=buildings,
                 static_object_count=len(objects),static_texture_count=len(materials)-len(buildings),
                 registration_file=str(args.registrations.resolve()) if args.registrations else None,
                 native_palette_candidates=palette_reports,
                 static_archive_sha256=hashlib.sha256((args.static/'tristram.d3dvis').read_bytes()).hexdigest(),
                 limitations=['Imported building geometry is a supplied candidate, not verified against vanilla silhouettes.',
                              'Hidden interior/light adjuncts are recorded but not imported.',
                              'Native static vegetation/scenery includes fixed sprite-ray relief rather than newly authored full models.',
                              'Front projection and procedural unseen surfaces require visual validation before a production tile bake.'])
    (output/'scene.json').write_text(json.dumps(summary,indent=2))
    (output/'native-object-map.json').write_text(json.dumps(objects,separators=(',',':')))
    print(json.dumps({'meshes':len(meshes),'materials':len(materials),'buildings':len(buildings),
                      'triangles':sum(len(v)//3 for v in archive.values()),'output':str(output)}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for field in ('static','scene','native','atlas','output'):p.add_argument(field,type=Path)
    p.add_argument('--registrations',type=Path)
    p.add_argument('--native-palette',action='store_true')
    convert(p.parse_args())
