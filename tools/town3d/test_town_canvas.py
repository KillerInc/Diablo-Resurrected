"""Synthetic layered-editor round trips; no game artwork."""
from argparse import Namespace
from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

import numpy as np
from PIL import Image

from town_canvas import create, export, png, fragments, region, apply_region


class CanvasTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        image=Image.new('RGBA',(32,4096),(7,8,9,0))
        image.paste((90,60,30,255),(4,4,28,28));image.save(self.root/'atlas.png')
        values=np.zeros((1,16),dtype='<u2');values[0,14]=1
        (self.root/'town.min').write_bytes(values.tobytes())
        (self.root/'objects.json').write_text(json.dumps([dict(source_cells=[[1,1,0,0],[2,1,0,0]])]))
        self.project=self.root/'project'
        create(Namespace(atlas=self.root/'atlas.png',minimum=self.root/'town.min',
                         objects=self.root/'objects.json',output=self.project,density=1))

    def rewrite(self,edit):
        target=self.root/'edited.ora'
        with zipfile.ZipFile(self.project/'Tristram-layered.ora') as archive:
            data={name:archive.read(name) for name in archive.namelist()}
        edit(data)
        with zipfile.ZipFile(target,'w') as archive:
            for name,value in data.items():archive.writestr(name,value)
        return target

    def run_export(self,ora):
        output=self.root/'export'
        export(Namespace(project=self.project,ora=ora,output=output))
        return output

    def test_exact_round_trip_and_composite(self):
        out=self.run_export(self.project/'Tristram-layered.ora')
        np.testing.assert_array_equal(np.asarray(Image.open(out/'town.png')),np.asarray(Image.open(self.root/'atlas.png')))
        with Image.open(self.project/'mergedimage.png') as image:
            self.assertEqual(image.size,tuple(json.loads((self.project/'project.json').read_text())['canvas']))
        self.assertEqual(json.loads((out/'export-report.json').read_text())['changed_frames'],[])

    def test_consistent_linked_edit_changes_one_frame(self):
        def edit(data):
            image=Image.open(BytesIO(data['data/frame-0001.png'])).convert('RGBA')
            image.putpixel((10,10),(130,80,20,255));data['data/frame-0001.png']=png(image)
        out=self.run_export(self.rewrite(edit))
        self.assertEqual(json.loads((out/'export-report.json').read_text())['changed_frames'],[1])
        self.assertEqual(Image.open(out/'town.png').getpixel((10,10)),(130,80,20,255))

    def test_conflicting_shared_edit_rejected(self):
        def edit(data):
            root=ET.fromstring(data['stack.xml']);layer=next(root.iter('layer'))
            image=Image.open(BytesIO(data[layer.get('src')])).convert('RGBA')
            image.putpixel((10,10),(0,255,0,255));data['data/different.png']=png(image)
            layer.set('src','data/different.png');data['stack.xml']=ET.tostring(root)
        with self.assertRaisesRegex(ValueError,'Shared-frame'):self.run_export(self.rewrite(edit))

    def test_changed_alpha_rejected(self):
        def edit(data):
            image=Image.open(BytesIO(data['data/frame-0001.png'])).convert('RGBA')
            image.putpixel((0,0),(0,255,0,255));data['data/frame-0001.png']=png(image)
        with self.assertRaisesRegex(ValueError,'Alpha coverage'):self.run_export(self.rewrite(edit))

    def test_editor_transparent_crop_is_supported(self):
        def edit(data):
            root=ET.fromstring(data['stack.xml'])
            for layer in root.iter('layer'):
                layer.set('x',str(int(layer.get('x'))+4));layer.set('y',str(int(layer.get('y'))+4))
            data['stack.xml']=ET.tostring(root)
            image=Image.open(BytesIO(data['data/frame-0001.png'])).crop((4,4,28,28))
            data['data/frame-0001.png']=png(image)
        out=self.run_export(self.rewrite(edit))
        self.assertEqual(json.loads((out/'export-report.json').read_text())['changed_frames'],[])

    def test_reordered_layers_rejected(self):
        def edit(data):
            root=ET.fromstring(data['stack.xml']);stack=root.find('stack')
            stack[:]=list(reversed(list(stack)));data['stack.xml']=ET.tostring(root)
        with self.assertRaisesRegex(ValueError,'Layer order'):self.run_export(self.rewrite(edit))

    def make_region(self):
        target=self.root/'region'
        region(Namespace(project=self.project,output=target,rect=[-32,0,96,64]))
        return target

    def test_flat_paint_reslices_and_propagates_shared_frame(self):
        target=self.make_region();owners=np.load(target/'owners.npz')['owners']
        y,x=np.argwhere(owners>0)[0];image=Image.open(target/'paint.png').convert('RGBA')
        image.putpixel((int(x),int(y)),(10,20,30,255));image.save(target/'paint.png')
        edited=self.root/'edited-project'
        apply_region(Namespace(region=target,edited=target/'paint.png',output=edited))
        out=self.root/'edited-export'
        export(Namespace(project=edited,ora=edited/'Tristram-layered.ora',output=out))
        self.assertEqual(json.loads((out/'export-report.json').read_text())['changed_frames'],[1])
        self.assertEqual(json.loads((edited/'paint-report.json').read_text())['propagated_world_layers'],2)

    def test_flat_paint_conflicting_source_pixel_rejected(self):
        target=self.make_region();owners=np.load(target/'owners.npz')['owners']
        values,counts=np.unique(owners[owners>0],return_counts=True);value=values[counts>1][0]
        points=np.argwhere(owners==value);image=Image.open(target/'paint.png').convert('RGBA')
        for (y,x),colour in zip(points,[(10,20,30,255),(30,20,10,255)]):image.putpixel((int(x),int(y)),colour)
        image.save(target/'paint.png')
        with self.assertRaisesRegex(ValueError,'different colours'):
            apply_region(Namespace(region=target,edited=target/'paint.png',output=self.root/'bad-project'))
        self.assertFalse((self.root/'bad-project').exists())


if __name__=='__main__':unittest.main()
