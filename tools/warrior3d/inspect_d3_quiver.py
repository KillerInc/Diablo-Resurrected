"""python SCRIPT ACTOR.acr APPEARANCE.app NEW_PRIVATE_OUTPUT
Inspect and export the static D3 v260 quiver subset, preserving source files.
Offsets follow WhiteoutLib's D3 native layout/geometry schema (BSD-3-Clause).
This guarded reader is not a universal Diablo III asset converter.
"""
import hashlib,json,struct,sys,math
from pathlib import Path
SCHEMA='https://github.com/FernandoS27/WhiteoutLib/blob/master/src/whiteout/sno/d3/native/layout.h'
def inspect(actor_file,app_file,out):
 actor_file,app_file,out=map(Path,[actor_file,app_file,out]);a=actor_file.read_bytes();b=app_file.read_bytes();out=out.resolve();assert not out.exists();out.mkdir(parents=True)
 def u(data,offset):assert 0<=offset<=len(data)-4;return struct.unpack_from('<I',data,offset)[0]
 def pointer(offset,size):start=u(b,offset)+16;length=u(b,offset+4);assert length%size==0 and 0<=start<=len(b) and start+length<=len(b);return start,length//size
 assert u(a,0)==u(b,0)==0xDEADBEEF and u(b,4)==260;actor_id=u(a,16);appearance=u(a,36);assert appearance==u(b,16);assert u(b,36)==0,'Only static, unskinned assets are supported'
 meshes=[]
 for geoset in [168,192]:
  count=u(b,geoset)
  if not count:continue
  start,n=pointer(geoset+4,400);assert n==count
  for i in range(n):
   s=start+i*400;vertex_format=u(b,s);vertices=u(b,s+4);vp,vbytes=pointer(s+8,1);index_count=u(b,s+40);ip,indices=pointer(s+44,2);assert vertex_format==121 and vbytes==44*vertices and indices==index_count and indices%3==0;positions=[list(struct.unpack_from('<3f',b,vp+j*44)) for j in range(vertices)];uv=[[(v/512)-64 for v in struct.unpack_from('<2H',b,vp+j*44+24)] for j in range(vertices)];normals=[[(b[vp+j*44+12+k]/127.5)-1 for k in range(3)] for j in range(vertices)];triangles=[list(struct.unpack_from('<3H',b,ip+j*2)) for j in range(0,indices,3)];assert all(math.isfinite(v) for p in positions for v in p) and all(max(t)<vertices for t in triangles);name=b[s+92:s+220].split(bytes([0]))[0].decode('ascii');material=b[s+220:s+348].split(bytes([0]))[0].decode('ascii');meshes.append({'name':name,'material':material,'positions':positions,'normals':normals,'uv':uv,'triangles':triangles})
 materials=[];start,n=pointer(440,144);assert n==u(b,436)
 for i in range(n):
  s=start+i*144;name=b[s:s+128].split(bytes([0]))[0].decode('ascii');vs,vn=pointer(s+128,248);variants=[]
  for j in range(vn):
   base=vs+j*248;uber=base+24;ts,tn=pointer(uber+76,160);textures=[{'slot':u(b,ts+k*160),'texture_sno':u(b,ts+k*160+8),'texture_type':u(b,ts+k*160+152)} for k in range(tn)];variants.append({'shader_map_sno':u(b,uber),'textures':textures})
  materials.append({'name':name,'variants':variants})
 obj=[];offset=1
 for mesh in meshes:
  obj.append('o '+mesh['name'])
  obj.extend('v '+' '.join(map(str,p)) for p in mesh['positions']);obj.extend('vt '+str(p[0])+' '+str(1-p[1]) for p in mesh['uv']);obj.extend('f '+' '.join(str(v+offset)+'/'+str(v+offset) for v in tri) for tri in mesh['triangles']);offset+=len(mesh['positions'])
 (out/'Quiver-untextured.obj').write_text('\n'.join(obj)+'\n');(out/'geometry-private.json').write_text(json.dumps(meshes));report={'actor':str(actor_file),'actor_sno':actor_id,'appearance':str(app_file),'appearance_sno':appearance,'appearance_version':260,'vertex_count':sum(len(m['positions']) for m in meshes),'triangle_count':sum(len(m['triangles']) for m in meshes),'materials':materials,'texture_snos':sorted({t['texture_sno'] for m in materials for v in m['variants'] for t in v['textures']}),'source_sha256':{'actor':hashlib.sha256(a).hexdigest(),'appearance':hashlib.sha256(b).hexdigest()},'schema':SCHEMA,'texture_images_available':False};(out/'inspection.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':inspect(*sys.argv[1:])
