"""Synthetic transaction and rollback tests; no proprietary artwork required."""
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import install_equipped_casts as installer
from install_layout_table import sha
from hd_layouts import write_table

class InstallTests(unittest.TestCase):
 def fixture(self,root):
  game=root/'game';hd=game/'HD';pack=root/'pack';baseline=root/'baseline'
  for p in [hd,pack/'HD',baseline]:p.mkdir(parents=True)
  exe=game/'Diablo Reincarnated.exe';exe.write_bytes(b'synthetic unchanged executable')
  names={f'w{a}{w}{s}' for a in 'lm' for w in 'abdhmstu' for s in ('fm','lm','qm')};protected=['wlnfm','wmnqm','whnas'];table={};oldpng={};newpng={};oldfiles={};newfiles={};art={};manifest={'sheets':{}}
  def put(path,data):path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);return sha(path)
  for n in sorted(names|set(protected)):
   rel=f'plrgfx/warrior/{n[:3]}/{n}.png';layout='D1R_SHEET_V1 8 48 96';table[rel]=layout;oldpng[rel]=put(hd/rel,('old '+n).encode());newpng[rel]=oldpng[rel];manifest['sheets'][n]={'sha256':oldpng[rel]}
   if n in names:
    src=root/'renders'/(n+'.png');newpng[rel]=put(src,('new '+n).encode());art[n]={'source':str(src),'sha256':newpng[rel],'size':[8,20],'layout':layout,'rows':20}
    page=rel.replace('.png','.p0.bc7');oldfiles[page]=put(hd/page,b'old page');newfiles[page]=put(pack/'HD'/page,b'new page')
  obsolete='plrgfx/warrior/wmd/wmdfm.p1.bc7';oldfiles[obsolete]=put(hd/obsolete,b'old obsolete page')
  oldfiles['sprites.gpus']=put(hd/'sprites.gpus',b'old index');newfiles['sprites.gpus']=put(pack/'HD/sprites.gpus',b'new index')
  write_table(hd/'layouts.csv',table);write_table(pack/'HD/layouts.csv',table)
  old={'source_png_hashes':oldpng,'files':oldfiles,'layout_sha256':sha(hd/'layouts.csv')};new={'source_png_hashes':newpng,'files':newfiles,'layout_sha256':sha(pack/'HD/layouts.csv'),'pages':48,'texture_bytes':1024}
  (baseline/'validated-gpu-pack.json').write_text(json.dumps(old));(pack/'validated-gpu-pack.json').write_text(json.dumps(new));artfile=root/'art.json';artfile.write_text(json.dumps({'sheets':art}))
  master=root/'master.json';mirror=root/'mirror/install-manifest.json';mirror.parent.mkdir();master.write_text(json.dumps(manifest));mirror.write_bytes(master.read_bytes())
  proof={'executable_sha256':sha(exe),'checks':{k:True for k in ['gpu_sprites','gameplay_reference_same','gameplay_reference_repeat_same','gpu_index_process_cache','casting_bounds','casting_head_clearance','casting_visual_review','casting_live_draw']},'gpu_sprites':{'pack_file_hashes':newfiles}};validation=root/'validation.json';validation.write_text(json.dumps(proof))
  args=[pack,artfile,baseline,game,master,mirror,root/'archive',root/'backup',validation]
  return args,old,new,obsolete
 def test_success(self):
  with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
   args,old,new,obsolete=self.fixture(Path(tmp));installer.install(*args);hd=args[3]/'HD'
   self.assertTrue(all(sha(hd/n)==h for n,h in new['source_png_hashes'].items()));self.assertFalse((hd/obsolete).exists());self.assertTrue((args[7]/'files/game'/obsolete).is_file());self.assertEqual(args[4].read_bytes(),args[5].read_bytes())
 def test_rollback_after_page_retirement(self):
  with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
   args,old,new,obsolete=self.fixture(Path(tmp));original=args[4].read_bytes();real=installer.shutil.copy2
   def fail(src,dst,*a,**kw):
    if Path(src)==args[0]/'HD/sprites.gpus':raise OSError('Synthetic final index failure')
    return real(src,dst,*a,**kw)
   with patch.object(installer.shutil,'copy2',side_effect=fail):
    with self.assertRaises(OSError):installer.install(*args)
   hd=args[3]/'HD';self.assertTrue(all(sha(hd/n)==h for n,h in old['files'].items()));self.assertTrue(all(sha(hd/n)==h for n,h in old['source_png_hashes'].items()));self.assertEqual(args[4].read_bytes(),original);self.assertEqual(args[5].read_bytes(),original);self.assertFalse(list(hd.rglob('*.cast-new')))

if __name__=='__main__':unittest.main()
