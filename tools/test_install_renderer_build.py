import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from hd_layouts import write_table
from install_renderer_build import install, sha


class RendererInstallTest(unittest.TestCase):
    def fixture(self, root):
        game=root/'game'; hd=game/'HD'; image=hd/'plrgfx/warrior/wln/wlnst.png';image.parent.mkdir(parents=True);image.write_bytes(b'synthetic image')
        table=hd/'layouts.csv';write_table(table,{'plrgfx/warrior/wln/wlnst.png':'D1R_SHEET_V1 8 48 96'})
        exe=game/'Diablo Reincarnated.exe';exe.write_bytes(b'old build');binary=root/'new.exe';binary.write_bytes(b'tested new build')
        record={'version':'0.4.3-pre','sheets':{'wlnst':{'sha256':sha(image),'layout':'D1R_SHEET_V1 8 48 96'}}}
        manifest=root/'manifest.json';mirror=root/'mirror.json';manifest.write_text(json.dumps(record));mirror.write_bytes(manifest.read_bytes())
        version=(Path(__file__).resolve().parents[1]/'REINCARNATED_VERSION').read_text().strip()
        proof={'version':version,'executable_sha256':sha(binary),'class_png_count':1,'preload':{'loaded':1,'resident':1,'skipped':0},'checks':{'performance_monitor':True,'provider_tests':True,'integration':True,'gameplay_reference_same':True,'gameplay_reference_repeat_same':True,'other_class_preloads':0,'warm_player_reloads':0,'ui_exit':0}}
        validation=root/'validation.json';validation.write_text(json.dumps(proof))
        return binary,game,manifest,mirror,root/'backup',validation,image,table

    def test_install_preserves_metadata_and_art(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary,game,manifest,mirror,backup,validation,image,table=self.fixture(Path(tmp));before=(image.read_bytes(),table.read_bytes())
            with contextlib.redirect_stdout(io.StringIO()):install(binary,game,manifest,mirror,backup,validation)
            self.assertEqual((image.read_bytes(),table.read_bytes()),before);self.assertEqual((game/'Diablo Reincarnated.exe').read_bytes(),binary.read_bytes());self.assertEqual(manifest.read_bytes(),mirror.read_bytes());self.assertEqual(json.loads(manifest.read_bytes())['version'],json.loads(validation.read_text())['version'])

    def test_failed_verification_rolls_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary,game,manifest,mirror,backup,validation,image,table=self.fixture(Path(tmp));original={p:p.read_bytes() for p in [game/'Diablo Reincarnated.exe',manifest,mirror,image,table]};real_sha=sha;count=0
            def fail_after_replace(path):
                nonlocal count
                if Path(path)==image:
                    count+=1
                    if count==2:raise OSError('Synthetic verification failure')
                return real_sha(path)
            with patch('install_renderer_build.sha',side_effect=fail_after_replace):
                with self.assertRaises(OSError):install(binary,game,manifest,mirror,backup,validation)
            for path,data in original.items():self.assertEqual(path.read_bytes(),data)


if __name__=='__main__':unittest.main()
