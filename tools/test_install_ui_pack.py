import json
from pathlib import Path
import tempfile
import unittest
from install_ui_pack import install
from install_terrain_pack import sha
from gpu_index import read_index


class UiPackInstallTest(unittest.TestCase):
    def test_preserves_records_and_rejects_unknown_art(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);game=root/'game';stage=root/'stage'
            game.mkdir();(stage/'ctrlpan').mkdir(parents=True)
            original='D1R_GPU_INDEX_V1\nDEFAULTS 4 1 4 4\nSHEET monsters/test.png 1 1 * * * *\ntest.p0.bc7 16 16\n0 0 0 16 16 0 0\n'
            added='SHEET ctrlpan/test.png 1 1 * * * *\ntest.p0.bc7 16 16\n0 0 0 16 16 0 0\n'
            (game/'sprites.gpus').write_text(original)
            (game/'layouts.csv').write_text('preserve anchors')
            (stage/'sprites.gpus').write_text(original+added)
            page=stage/'ctrlpan/test.p0.bc7';page.write_bytes(bytes(range(32)))
            proof={'checks':dict.fromkeys(('ui_gpu_readback','full_pack_gpu_upload','gameplay_reference_same','gameplay_reference_repeat_same','png_free_runtime'),True),
                'ui_pack':{'previous_index_sha256':sha(game/'sprites.gpus'),'index_sha256':sha(stage/'sprites.gpus'),
                    'resources':['ctrlpan/test.png'],'page_hashes':{'ctrlpan/test.p0.bc7':sha(page)}}}
            validation=root/'proof.json';validation.write_text(json.dumps(proof))
            (game/'ctrlpan').mkdir();target=game/'ctrlpan/test.p0.bc7';target.write_bytes(b'unknown user art')
            with self.assertRaises(AssertionError):install(stage,game,root/'blocked',validation)
            self.assertEqual(target.read_bytes(),b'unknown user art');self.assertEqual((game/'sprites.gpus').read_text(),original)
            target.unlink();install(stage,game,root/'backup',validation)
            self.assertEqual((game/'layouts.csv').read_text(),'preserve anchors')
            self.assertEqual(read_index(game/'sprites.gpus')['monsters/test.png'],read_index(root/'backup/previous-sprites.gpus')['monsters/test.png'])
            self.assertEqual(sha(target),sha(page))


if __name__=='__main__':unittest.main()
