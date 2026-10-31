import json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from install_gpu_renderer import install
from install_layout_table import sha
import test_install_renderer_build as base


class GpuInstallTest(unittest.TestCase):
    def fixture(self,root):
        fixture=base.RendererInstallTest().fixture(root)
        binary,game,manifest,mirror,backup,validation,image,table=fixture
        pack=root/'pack';(pack/'HD').mkdir(parents=True)
        gpu=pack/'HD/test.gpus';gpu.write_bytes(b'new synthetic GPU metadata')
        proof=json.loads(validation.read_text());proof['gpu_sprites'].update(texture_bytes=64,pack_file_hashes={'test.gpus':sha(gpu)})
        validation.write_text(json.dumps(proof))
        assets={'sheets':1,'pages':1,'texture_bytes':64,'layout_sha256':sha(table),'source_png_hashes':{'plrgfx/warrior/wln/wlnst.png':sha(image)},'files':{'test.gpus':sha(gpu)}}
        (pack/'validated-gpu-pack.json').write_text(json.dumps(assets))
        return pack,fixture

    def test_install_preserves_png_table_and_old_assets_backup(self):
        with tempfile.TemporaryDirectory() as temp:
            pack,fixture=self.fixture(Path(temp));binary,game,manifest,mirror,backup,validation,image,table=fixture
            before=(image.read_bytes(),table.read_bytes());old=(game/'HD/test.gpus').read_bytes()
            install(pack,binary,game,manifest,mirror,backup,validation)
            self.assertEqual((image.read_bytes(),table.read_bytes()),before)
            self.assertEqual((backup/'gpu-before/test.gpus').read_bytes(),old)
            self.assertEqual((game/'HD/test.gpus').read_bytes(),(pack/'HD/test.gpus').read_bytes())

    def test_failed_renderer_install_restores_overwritten_gpu_files(self):
        with tempfile.TemporaryDirectory() as temp:
            pack,fixture=self.fixture(Path(temp));binary,game,manifest,mirror,backup,validation,image,table=fixture
            before={p:p.read_bytes() for p in [game/'Diablo Reincarnated.exe',game/'HD/test.gpus',manifest,mirror,image,table]}
            with patch('install_gpu_renderer.install_build',side_effect=OSError('Synthetic install failure')):
                with self.assertRaises(OSError):install(pack,binary,game,manifest,mirror,backup,validation)
            for path,data in before.items():self.assertEqual(path.read_bytes(),data)

    def test_failed_install_removes_new_gpu_files(self):
        with tempfile.TemporaryDirectory() as temp:
            pack,fixture=self.fixture(Path(temp));binary,game,manifest,mirror,backup,validation,image,table=fixture
            target=game/'HD/test.gpus';target.unlink()
            before=(image.read_bytes(),table.read_bytes())
            with patch('install_gpu_renderer.install_build',side_effect=OSError('Synthetic install failure')):
                with self.assertRaises(OSError):install(pack,binary,game,manifest,mirror,backup,validation)
            self.assertFalse(target.exists())
            self.assertEqual((image.read_bytes(),table.read_bytes()),before)

    def test_consolidation_retires_metadata_and_failure_restores_it(self):
        for fail in (False,True):
            with self.subTest(fail=fail), tempfile.TemporaryDirectory() as temp:
                pack,fixture=self.fixture(Path(temp));binary,game,manifest,mirror,backup,validation,image,table=fixture
                central=pack/'HD/sprites.gpus';central.write_bytes(b'synthetic central index')
                digest=sha(central)
                assets=json.loads((pack/'validated-gpu-pack.json').read_text());assets['files']={'sprites.gpus':digest}
                (pack/'validated-gpu-pack.json').write_text(json.dumps(assets))
                proof=json.loads(validation.read_text());proof['gpu_sprites']['pack_file_hashes']=assets['files'];validation.write_text(json.dumps(proof))
                old=game/'HD/plrgfx/warrior/wln/wlnst.gpus';old.write_bytes(b'old sheet metadata')
                if fail:
                    with patch('install_gpu_renderer.install_build',side_effect=OSError('Synthetic failure')):
                        with self.assertRaises(OSError):install(pack,binary,game,manifest,mirror,backup,validation)
                    self.assertEqual(old.read_bytes(),b'old sheet metadata')
                    self.assertFalse((game/'HD/sprites.gpus').exists())
                else:
                    install(pack,binary,game,manifest,mirror,backup,validation)
                    self.assertFalse(old.exists())
                    self.assertEqual((backup/'gpu-before/plrgfx/warrior/wln/wlnst.gpus').read_bytes(),b'old sheet metadata')



if __name__=='__main__':unittest.main()
