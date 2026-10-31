"""Synthetic integrity checks; no game data or artwork."""
import json
from pathlib import Path
import tempfile
import unittest
from install_terrain_pack import install, sha, TERRAIN
from gpu_index import read_index


class TerrainInstallTest(unittest.TestCase):
    def fixture(self, root):
        old, staged = root/'game/HD', root/'stage/HD'
        old.mkdir(parents=True); staged.mkdir(parents=True)
        header = 'D1R_GPU_INDEX_V1\nDEFAULTS 4 1 32 32\n'
        base = 'SHEET objects/test.png 1 1 * * * *\nbase.bc7 4 4\n0 0 0 4 4 0 0\n'
        (old/'sprites.gpus').write_text(header+base)
        (old/'base.bc7').write_bytes(b'original synthetic data')
        lines = [header+base]; hashes = {}
        for key in TERRAIN:
            rel = Path(key).with_suffix('.bc7'); path = staged/rel
            path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(b'synthetic tile')
            hashes[rel.as_posix()] = sha(path)
            lines.append(f'SHEET {key} 1 1 * * * *\n{rel.name} 4 4\n0 0 0 4 4 0 0\n')
        (staged/'sprites.gpus').write_text(''.join(lines))
        hashes['sprites.gpus'] = sha(staged/'sprites.gpus')
        proof = {'checks': {key: True for key in ('terrain_gpu_readback', 'full_pack_gpu_upload',
                     'gameplay_reference_same', 'gameplay_reference_repeat_same', 'png_free_runtime')},
                 'terrain': {'previous_index_sha256': sha(old/'sprites.gpus'), 'pack_file_hashes': hashes}}
        validation = root/'validation.json'; validation.write_text(json.dumps(proof))
        return old, staged, validation

    def test_merge_preserves_existing_pack_and_has_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); old, staged, proof = self.fixture(root)
            original = (old/'sprites.gpus').read_bytes()
            install(staged, old, root/'backup', proof)
            self.assertEqual(read_index(old/'sprites.gpus'), read_index(staged/'sprites.gpus'))
            self.assertEqual((root/'backup/previous-sprites.gpus').read_bytes(), original)
            self.assertEqual((old/'base.bc7').read_bytes(), b'original synthetic data')

    def test_unknown_art_is_rejected_before_any_metadata_change(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); old, staged, proof = self.fixture(root)
            original = (old/'sprites.gpus').read_bytes()
            collision = old/Path(TERRAIN[0]).with_suffix('.bc7')
            collision.parent.mkdir(parents=True); collision.write_bytes(b'user art')
            with self.assertRaises(AssertionError): install(staged, old, root/'backup', proof)
            self.assertEqual((old/'sprites.gpus').read_bytes(), original)
            self.assertEqual(collision.read_bytes(), b'user art')
            self.assertFalse((root/'backup').exists())


if __name__ == '__main__': unittest.main()
