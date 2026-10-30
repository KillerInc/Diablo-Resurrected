import itertools,json,tempfile,unittest,os
from pathlib import Path
from unittest.mock import patch
from install_medium_warrior import install
from install_layout_table import sha
from hd_layouts import write_table

class MediumInstallTest(unittest.TestCase):
 def fixture(self,root):
  game=root/'game';hd=game/'HD';hd.mkdir(parents=True);(game/'Diablo Reincarnated.exe').write_bytes(b'unchanged synthetic engine')
  pack=root/'pack';(pack/'HD').mkdir(parents=True);baseline=root/'baseline';baseline.mkdir();source=root/'rendered';source.mkdir();mirror=root/'mirror/install-manifest.json';mirror.parent.mkdir();master=root/'master.json';before_png={};after_png={};art={};layouts={}
  def write(path,data):path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
  for suffix in itertools.islice(itertools.product('abcdefghijklmnopqrstuvwxyz',repeat=3),85):
   name='wm'+''.join(suffix);rel=f'plrgfx/warrior/{name[:3]}/{name}.png';write(hd/rel,('old '+name).encode());before_png[rel]=sha(hd/rel);new=source/(name+'.png');new.write_bytes(('new '+name).encode());after_png[rel]=sha(new);layouts[rel]='D1R_SHEET_V1 8 48 96';art[name]={'source':str(new),'size':[6144,6144],'sha256':sha(new),'layout':layouts[rel]}
  for rel in ('plrgfx/warrior/wln/wlnst.png','plrgfx/warrior/whn/whnst.png'):
   write(hd/rel,b'preserved other armor');before_png[rel]=after_png[rel]=sha(hd/rel)
  write(hd/'sprites.gpus',b'old index');write(hd/'plrgfx/warrior/wmn/wmnst.p0.bc7',b'old page');write(hd/'plrgfx/warrior/wmn/wmnst.p9.bc7',b'obsolete page')
  before_files={p.relative_to(hd).as_posix():sha(p) for p in hd.rglob('*') if p.is_file() and p.suffix in ('.gpus','.bc7')};write_table(hd/'layouts.csv',{})
  old={'sheets':{'wlnst':{'sha256':sha(hd/'plrgfx/warrior/wln/wlnst.png')}},'version':'0.4.7-pre'};master.write_text(json.dumps(old));mirror.write_text(json.dumps(old))
  write(pack/'HD/sprites.gpus',b'new index');write(pack/'HD/plrgfx/warrior/wmn/wmnst.p0.bc7',b'new page');write_table(pack/'HD/layouts.csv',layouts)
  files={p.relative_to(pack/'HD').as_posix():sha(p) for p in (pack/'HD').rglob('*') if p.is_file() and p.suffix in ('.gpus','.bc7')}
  assets={'sheets':255,'pages':1,'texture_bytes':64,'files':files,'source_png_hashes':after_png,'layout_sha256':sha(pack/'HD/layouts.csv')};(pack/'validated-gpu-pack.json').write_text(json.dumps(assets));(baseline/'validated-gpu-pack.json').write_text(json.dumps({'files':before_files,'source_png_hashes':before_png,'layout_sha256':sha(hd/'layouts.csv')}))
  art_file=root/'art.json';art_file.write_text(json.dumps({'model_sha256':'synthetic approved model','sheets':art}));validation=root/'validation.json';validation.write_text(json.dumps({'executable_sha256':sha(game/'Diablo Reincarnated.exe'),'medium_model_sha256':'synthetic approved model','checks':{k:True for k in ('gpu_sprites','medium_visual_review','medium_live_draw','gameplay_reference_same','gameplay_reference_repeat_same','gpu_index_process_cache')},'gpu_sprites':{'pack_file_hashes':files}}))
  return (pack,art_file,baseline,game,master,mirror,root/'archive',root/'backup',validation)
 def test_install_preserves_other_armor_and_engine(self):
  with tempfile.TemporaryDirectory() as temp:
   args=self.fixture(Path(temp));before=sha(args[3]/'Diablo Reincarnated.exe');install(*args)
   self.assertEqual(sha(args[3]/'Diablo Reincarnated.exe'),before);self.assertEqual(len(json.loads(args[4].read_text())['sheets']),86);self.assertFalse((args[3]/'HD/plrgfx/warrior/wmn/wmnst.p9.bc7').exists());self.assertTrue((args[7]/'files/game/plrgfx/warrior/wmn/wmnst.p9.bc7').exists())
 def test_failure_after_page_retirement_restores_all_files(self):
  with tempfile.TemporaryDirectory() as temp:
   args=self.fixture(Path(temp));paths=[*args[3].rglob('*'),args[4],args[5]];before={p:p.read_bytes() for p in paths if p.is_file()};real=os.replace;calls=0
   def fail(source,target):
    nonlocal calls
    calls+=1
    if calls==172:raise OSError('Synthetic index/table transaction failure')
    return real(source,target)
   with patch('install_medium_warrior.os.replace',side_effect=fail):
    with self.assertRaises(OSError):install(*args)
   self.assertEqual(calls,172)
   for p,data in before.items():self.assertEqual(p.read_bytes(),data,str(p))
   self.assertFalse(list(args[3].rglob('*.medium-new')))

if __name__=='__main__':unittest.main()
