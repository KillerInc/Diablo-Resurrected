"""Synthetic format/calibration checks; no Diablo artwork or private fixtures."""
import math
from pathlib import Path
import struct
import tempfile
import unittest

import numpy as np

from convert_scene import Reader, read_model, read_static, transform
from register_buildings import apply_registration, envelope, fit
from native_palette import match_palette


class SceneTests(unittest.TestCase):
    def test_native_camera_calibration(self):
        # Blender's 30-degree camera and z conversion reproduce native pixels.
        xyz=np.array([[1,0,0],[0,0,1],[0,1,0],[12.25,3.5,21.75]])
        blender=np.stack((xyz[:,0],-xyz[:,2],xyz[:,1]*math.sqrt(2/3)),axis=1)
        right=np.array([1,1,0])/math.sqrt(2)
        up=np.array([-1/(2*math.sqrt(2)),1/(2*math.sqrt(2)),math.sqrt(3)/2])
        pixels=np.stack((blender@right,-blender@up),axis=1)*32*math.sqrt(2)
        expected=np.stack((32*(xyz[:,0]-xyz[:,2]),16*(xyz[:,0]+xyz[:,2])-32*xyz[:,1]),axis=1)
        np.testing.assert_allclose(pixels,expected,atol=1e-12)

    def test_transform_retains_native_pivot(self):
        points=np.array([[4,2,6],[5,2,6]],dtype=float)
        out=transform(points,(4,2,6),(1,0,-1),math.pi/2,2)
        np.testing.assert_allclose(out,[[5,2,5],[5,2,3]],atol=1e-12)

    def test_registration_matches_envelope_and_keeps_ground_flat(self):
        points=np.array([[x,h,z] for x in (2.,7.) for h in (0.,6.) for z in (4.,8.)])
        known=dict(pivot=[4.,0.,6.],horizontal_scale=.8,height_scale=1.2,translation=[.7,0.,-.3])
        target=envelope(apply_registration(points,known))
        record=fit(points,target,[4.,0.,6.])
        repaired=apply_registration(points,record)
        np.testing.assert_allclose(envelope(repaired),target,atol=1e-10)
        np.testing.assert_array_equal(repaired[points[:,1]==0,1],0)
        np.testing.assert_array_equal(points[:,1],[0,0,6,6,0,0,6,6])

    def test_palette_candidate_preserves_source_size_and_detail_order(self):
        from PIL import Image
        pixels=np.repeat(np.array([[[30],[90],[150],[240]]],dtype=np.uint8),3,axis=2)
        original=Image.fromarray(pixels)
        native=Image.fromarray(np.array([[[4,8,16,255],[10,20,40,255],
                                         [20,40,80,255],[30,60,120,255]]],dtype=np.uint8))
        image,report=match_palette(original,native,np.array([[[0,0],[1,0],[1,1]],[[0,0],[1,1],[0,1]]]))
        self.assertEqual(image.size,original.size)
        np.testing.assert_array_equal(np.asarray(original),pixels)
        result=np.asarray(image)
        self.assertTrue(np.all(np.diff(result[0,:,0].astype(int))>=0))
        self.assertTrue(np.all(result[:,:,2]>=result[:,:,0]))

    def test_static_ground_and_coverage(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'textures').mkdir()
            data=b'D3DSTAT1'+struct.pack('<5I',1,112,112,1,1)
            data+=struct.pack('<3I',2,1,2)+bytes([1,2])+bytes([1,0])
            identity=b'ground-test'
            data+=struct.pack('<I',len(identity))+identity+struct.pack('<4B',0,2,0,0)
            data+=struct.pack('<2I5f3I3f',4,6,0,0,0,0,1,0,1,0,0,0,0)
            data+=struct.pack('<4H',4,6,217,0)
            path=root/'static.bin';path.write_bytes(data)
            palette=np.zeros((256,3),dtype=np.uint8);palette[1]=[10,20,30]
            groups,materials,objects,cells=read_static(path,palette,root)
            self.assertEqual(cells,{(4,6):217})
            self.assertEqual(len(objects),1)
            self.assertEqual(len(groups[0,0,0][0]),6)
            # Alpha-zero floor areas must have no coplanar geometry, otherwise
            # they can occlude a neighbour before alpha blending is resolved.
            self.assertLessEqual(groups[0,0,0][0][:,3].max(),.5)
            from PIL import Image
            texture=Image.open(root/materials[0]['image'])
            self.assertEqual(texture.getpixel((0,0)),(10,20,30,255))
            self.assertEqual(texture.getpixel((1,0))[3],0)
            path.write_bytes(data[:-1])
            with self.assertRaises(ValueError):read_static(path,palette,root)

    def test_architecture_triangle_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'model.bin'
            data=b'D3DVIS1\0'+struct.pack('<3I',1,0,0)+struct.pack('<4i',1,2,3,4)
            data+=struct.pack('<5fI',1,2,3,4,5,1)
            data+=struct.pack('<6iI4i7I',1,2,0,0,64,256,1,1,2,3,4,0,0,1,0,0,0,0)
            data+=struct.pack('<7I',0,0,0,0,0,0,0)
            vertices=[1,0,2,0,0,3,0,2,1,0,1,2,2,0,1]
            data+=struct.pack('<15fI4iI3f2I',*vertices,1,1,2,1,2,1,0,0,1,0,2)
            path.write_bytes(data)
            model=read_model(path)
            self.assertEqual(model['minimum'],(1,2))
            self.assertEqual(model['geometry']['detail'][0],2)
            np.testing.assert_array_equal(model['geometry']['v'][0,:,0],[1,3,1])
            path.write_bytes(data[:-1])
            with self.assertRaises(ValueError):read_model(path)


if __name__=='__main__':unittest.main()
