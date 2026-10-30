"""Synthetic transaction and rollback tests; no proprietary artwork required."""
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import install_equipped_casts as installer
from install_layout_table import sha
from hd_layouts import write_table

class InstallTests(unittest.TestCase):
 def fixture(self,root,revision='equipped-casts-v1'):
  game=root/'game';hd=game/'HD';pack=root/'pack';baseline=root/'baseline'
  for p in [hd,pack/'HD',baseline]:p.mkdir(parents=True)
  exe=game/'Diablo Reincarnated.exe';exe.write_bytes(b'synthetic unchanged executable')
  names={f'w{a}{w}{s}' for a in 'lm' for w in 'abdhmstu' for s in ('fm','lm','qm')} if revision=='equipped-casts-v1' else {f'w{a}{w}{s}' for a in 'lm' for w in 'abdhmnstu' for s in (('fm','lm') if revision=='spell-effects-v2' else ('fm',))};protected=['wlnfm','wmnqm','whnas'];table={};oldpng={};newpng={};oldfiles={};newfiles={};art={};manifest={'sheets':{}}
  if revision=='medium-shield-v1':names={f'wm{w}{action}' for w in 'dhu' for action in ('as','at','aw','bl','fm','ht','lm','qm','st','wl')}
  def put(path,data):path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);return sha(path)
  for n in sorted(names|set(protected)):
   rel=f'plrgfx/warrior/{n[:3]}/{n}.png';layout='D1R_SHEET_V1 8 48 96';table[rel]=layout;oldpng[rel]=put(hd/rel,('old '+n).encode());newpng[rel]=oldpng[rel];manifest['sheets'][n]={'sha256':oldpng[rel]}
   if n in names:
    src=root/'renders'/(n+'.png');newpng[rel]=put(src,('new '+n).encode());art[n]={'source':str(src),'sha256':newpng[rel],'size':[8,20],'layout':layout,'rows':20}
    page=rel.replace('.png','.p0.bc7');oldfiles[page]=put(hd/page,b'old page');newfiles[page]=put(pack/'HD'/page,b'new page')
  obsolete='plrgfx/warrior/wmd/wmdfm.p1.bc7';oldfiles[obsolete]=put(hd/obsolete,b'old obsolete page')
  oldfiles['sprites.gpus']=put(hd/'sprites.gpus',b'old index');newfiles['sprites.gpus']=put(pack/'HD/sprites.gpus',b'new index')
  write_table(hd/'layouts.csv',table);write_table(pack/'HD/layouts.csv',table)
  old={'source_png_hashes':oldpng,'files':oldfiles,'layout_sha256':sha(hd/'layouts.csv')};new={'source_png_hashes':newpng,'files':newfiles,'layout_sha256':sha(pack/'HD/layouts.csv'),'pages':len(names),'texture_bytes':1024}
  (baseline/'validated-gpu-pack.json').write_text(json.dumps(old));(pack/'validated-gpu-pack.json').write_text(json.dumps(new));artfile=root/'art.json';artfile.write_text(json.dumps({'sheets':art}))
  master=root/'master.json';mirror=root/'mirror/install-manifest.json';mirror.parent.mkdir();master.write_text(json.dumps(manifest));mirror.write_bytes(master.read_bytes())
  proof={'executable_sha256':sha(exe),'checks':{k:True for k in ['gpu_sprites','gameplay_reference_same','gameplay_reference_repeat_same','gpu_index_process_cache','casting_bounds','casting_head_clearance','casting_visual_review','casting_live_draw','fire_bounds','fire_anchor_fixed','fire_mesh_stable','fire_visual_review','fire_live_draw','character_motion_unchanged','lightning_growth','lightning_paths_fixed','lightning_geometry_held','lightning_visual_review','shield_bounds','shield_visual_review','shield_live_draw']},'gpu_sprites':{'pack_file_hashes':newfiles}};validation=root/'validation.json';validation.write_text(json.dumps(proof))
  args=[pack,artfile,baseline,game,master,mirror,root/'archive',root/'backup',validation]
  return args,old,new,obsolete
 def success(self,revision):
  with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
   args,old,new,obsolete=self.fixture(Path(tmp),revision);installer.install(*args,revision=revision);hd=args[3]/'HD'
   self.assertTrue(all(sha(hd/n)==h for n,h in new['source_png_hashes'].items()));self.assertFalse((hd/obsolete).exists());self.assertTrue((args[7]/'files/game'/obsolete).is_file());self.assertEqual(args[4].read_bytes(),args[5].read_bytes())
 def rollback(self,revision):
  with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
   args,old,new,obsolete=self.fixture(Path(tmp),revision);original=args[4].read_bytes();real=installer.shutil.copy2
   def fail(src,dst,*a,**kw):
    if Path(src)==args[0]/'HD/sprites.gpus':raise OSError('Synthetic final index failure')
    return real(src,dst,*a,**kw)
   with patch.object(installer.shutil,'copy2',side_effect=fail):
    with self.assertRaises(OSError):installer.install(*args,revision=revision)
   hd=args[3]/'HD';self.assertTrue(all(sha(hd/n)==h for n,h in old['files'].items()));self.assertTrue(all(sha(hd/n)==h for n,h in old['source_png_hashes'].items()));self.assertEqual(args[4].read_bytes(),original);self.assertEqual(args[5].read_bytes(),original);self.assertFalse(list(hd.rglob('*.cast-new')))
 def test_shield_success(self):self.success('medium-shield-v1')
 def test_shield_rollback(self):self.rollback('medium-shield-v1')
 def test_equipped_success(self):self.success('equipped-casts-v1')
 def test_equipped_rollback(self):self.rollback('equipped-casts-v1')
 def test_fire_success(self):self.success('fire-bubble-v2')
 def test_fire_rollback(self):self.rollback('fire-bubble-v2')
 def test_spell_success(self):self.success('spell-effects-v2')
 def test_spell_rollback(self):self.rollback('spell-effects-v2')

if __name__=='__main__':unittest.main()
