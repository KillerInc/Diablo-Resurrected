from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

from install_town_art import inspect,install,within


class TownInstall(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.game=self.root/'game';self.pack=self.root/'pack';self.source=self.root/'town.png'
        index='D1R_GPU_INDEX_V1\nDEFAULTS 4 1 1 1\nSHEET levels/towndata/town.png 1 1 * * * *\ntown.p0.bc7 4 4\n0 0 0 4 4 0 0\n'
        for root,data in ((self.game,b'old'),(self.pack,b'new')):
            (root/'levels/towndata').mkdir(parents=True);(root/'sprites.gpus').write_text(index)
            (root/'layouts.csv').write_text('synthetic layout\n');(root/'levels/towndata/town.p0.bc7').write_bytes(data)
        Image.new('RGBA',(4,4),(50,60,70,255)).save(self.game/'levels/towndata/town.png')
        Image.new('RGBA',(4,4),(80,90,100,255)).save(self.source)

    def tearDown(self):self.tmp.cleanup()

    def test_geometry_and_metadata_guards(self):
        inspect(self.game,self.pack,self.source)
        with self.assertRaises(ValueError):within(self.game,'../escape')
        Image.new('RGBA',(4,4),(80,90,100,0)).save(self.source)
        with self.assertRaises(ValueError):inspect(self.game,self.pack,self.source)

    def test_foreground_is_installed_and_alpha_checked_with_terrain(self):
        for root,data in ((self.game,b'old'),(self.pack,b'new')):
            index=root/'sprites.gpus'
            index.write_text(index.read_text()+'SHEET levels/towndata/towns.png 1 1 * * * *\ntowns.p0.bc7 4 4\n0 0 0 4 4 0 0\n')
            (root/'levels/towndata/towns.p0.bc7').write_bytes(data)
        Image.new('RGBA',(4,4),(40,50,60,255)).save(self.game/'levels/towndata/towns.png')
        foreground=self.source.with_name('towns.png')
        Image.new('RGBA',(4,4),(70,80,90,255)).save(foreground)
        files,_=inspect(self.game,self.pack,self.source)
        self.assertEqual(len(files),4)
        install(SimpleNamespace(game=self.game,pack=self.pack,source=self.source,install=True,backup=self.root/'both-backup'))
        self.assertEqual((self.game/'levels/towndata/towns.p0.bc7').read_bytes(),b'new')
        Image.new('RGBA',(4,4),(70,80,90,0)).save(foreground)
        with self.assertRaises(ValueError):inspect(self.game,self.pack,self.source)

    def test_install_and_rollback_leave_index_and_layout_untouched(self):
        original=(self.game/'sprites.gpus').read_bytes();backup=self.root/'backup'
        install(SimpleNamespace(game=self.game,pack=self.pack,source=self.source,install=True,backup=backup))
        self.assertEqual((self.game/'levels/towndata/town.p0.bc7').read_bytes(),b'new')
        self.assertEqual((backup/'levels/towndata/town.p0.bc7').read_bytes(),b'old')
        self.assertEqual((self.game/'sprites.gpus').read_bytes(),original)
        (self.pack/'levels/towndata/town.p0.bc7').write_bytes(b'two')
        import os
        real=os.replace;calls=0
        def fail_second(a,b):
            nonlocal calls
            calls+=1
            if calls==2:raise OSError('synthetic interruption')
            return real(a,b)
        with patch('install_town_art.os.replace',side_effect=fail_second):
            with self.assertRaises(OSError):install(SimpleNamespace(game=self.game,pack=self.pack,source=self.source,install=True,backup=self.root/'rollback'))
        self.assertEqual((self.game/'levels/towndata/town.p0.bc7').read_bytes(),b'new')
        self.assertFalse(list(self.game.rglob('*.town-art-new')))


if __name__=='__main__':unittest.main()
