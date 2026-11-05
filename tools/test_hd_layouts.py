import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import hd_layouts
import install_layout_table as migration


class LayoutMigrationTest(unittest.TestCase):
    def fixture(self, root):
        game = root / 'game'; hd = game / 'HD'; image = hd / 'plrgfx/warrior/wln/wlnst.png'
        image.parent.mkdir(parents=True); image.write_bytes(b'synthetic PNG fixture')
        sidecar = image.with_name(image.name + '.layout'); sidecar.write_bytes(b'D1R_SHEET_V1 8 48 96\r\n')
        (game / 'Diablo Reincarnated.exe').write_bytes(b'old synthetic executable')
        binary = root / 'new.exe'; binary.write_bytes(b'new synthetic executable')
        record = {'version': '0.4.2-pre', 'sheets': {'wlnst': {'layout': 'D1R_SHEET_V1 8 48 96', 'sha256': migration.sha(image)}}}
        manifest = root / 'manifest.json'; mirror = root / 'mirror.json'
        manifest.write_text(json.dumps(record)); mirror.write_bytes(manifest.read_bytes())
        return binary, game, manifest, mirror, root / 'backup', image, sidecar

    def test_collect_csv_and_quoted_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); _, game, _, _, _, _, _ = self.fixture(root)
            rows = hd_layouts.collect(game / 'HD'); rows['players/a,b.png'] = '128 256 64 256'
            table = root / 'layouts.csv'; hd_layouts.write_table(table, rows)
            self.assertEqual(hd_layouts.read_table(table), rows)
            self.assertIn(b'"players/a,b.png"', table.read_bytes())

    def test_invalid_keys_and_duplicates(self):
        for name in ('../a.png', '/a.png', 'a\\b.png', 'C:/a.png', 'a//b.png'):
            with self.assertRaises(ValueError): hd_layouts.key(name)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'layouts.csv'; path.write_text('path,layout\na.png,D1R_SHEET_V1 8 48 96\nA.PNG,D1R_SHEET_V1 8 48 96\n')
            with self.assertRaises(ValueError): hd_layouts.read_table(path)

    def test_migration_preserves_png_and_backups(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary, game, manifest, mirror, backup, image, sidecar = self.fixture(Path(tmp))
            old_png = image.read_bytes(); old_layout = sidecar.read_bytes()
            with contextlib.redirect_stdout(io.StringIO()): migration.install(binary, game, manifest, mirror, backup)
            self.assertEqual(image.read_bytes(), old_png); self.assertFalse(sidecar.exists())
            self.assertEqual((backup / 'sidecars/plrgfx/warrior/wln/wlnst.png.layout').read_bytes(), old_layout)
            self.assertEqual((game / 'Diablo Reincarnated.exe').read_bytes(), binary.read_bytes())
            self.assertEqual(json.loads(manifest.read_bytes())['version'], '0.4.3-pre')
            self.assertEqual(manifest.read_bytes(), mirror.read_bytes())
            self.assertEqual(len(hd_layouts.read_table(game / 'HD/layouts.csv')), 1)

    def test_failure_after_removal_restores_everything(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary, game, manifest, mirror, backup, image, sidecar = self.fixture(Path(tmp))
            old = {p: p.read_bytes() for p in (game / 'Diablo Reincarnated.exe', manifest, mirror, image, sidecar)}
            real_sha = migration.sha; count = 0
            def fail_during_verification(path):
                nonlocal count
                if Path(path) == image:
                    count += 1
                    if count == 2: raise OSError('Synthetic verification failure after sidecar removal')
                return real_sha(path)
            with patch.object(migration, 'sha', side_effect=fail_during_verification):
                with self.assertRaises(OSError): migration.install(binary, game, manifest, mirror, backup)
            for path, data in old.items(): self.assertEqual(path.read_bytes(), data)
            self.assertFalse((game / 'HD/layouts.csv').exists())


if __name__ == '__main__': unittest.main()
