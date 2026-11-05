import unittest
import numpy as np
from PIL import Image
from replace_ground_materials import phase, periodic_material, sample, replace


class MaterialTests(unittest.TestCase):
    def test_world_tile_translations_keep_shared_phase(self):
        point=(-320,2049)
        for x,z in ((1,0),(0,1),(4,-7),(-10,3)):
            self.assertEqual(phase(point),phase((point[0]+32*(x-z),point[1]+16*(x+z))))

    def test_material_opposing_edges_agree(self):
        rng=np.random.default_rng(4);image=Image.fromarray(rng.integers(10,100,(64,64,3),dtype=np.uint8))
        material=periodic_material(image,(45,35,25))
        np.testing.assert_array_equal(material[0],material[-1]);np.testing.assert_array_equal(material[:,0],material[:,-1])

    def test_neighbour_half_cells_sample_one_continuous_field(self):
        material=np.random.default_rng(1).random((128,128,3))
        a=sample(material,phase((-32,-31)),cell=256)
        b=sample(material,phase((0,-31)),cell=128)
        np.testing.assert_allclose(a[:128,128:],b)

    def test_material_does_not_reflect_quadrants(self):
        rng=np.random.default_rng(7)
        image=Image.fromarray(rng.integers(20,80,(128,128,3),dtype=np.uint8))
        material=periodic_material(image,(45,35,25))
        self.assertFalse(np.allclose(material[16:64,16:64],material[16:64,64:112][:,::-1]))

    def test_replacement_changes_rgb_preserves_mask_and_hidden_pixels(self):
        src=np.full((128,128,4),[55,42,48,0],dtype=np.uint8);src[10:118,10:118,3]=255
        dirt=np.full((128,128,3),[52,43,32],dtype=float);grass=np.full((128,128,3),[28,35,23],dtype=float)
        out=np.asarray(replace(Image.fromarray(src),dirt,grass,(0,0)))
        np.testing.assert_array_equal(out[:,:,3],src[:,:,3]);np.testing.assert_array_equal(out[src[:,:,3]==0],src[src[:,:,3]==0])
        self.assertGreater(np.abs(out[64,64,:3].astype(int)-src[64,64,:3]).max(),8)


if __name__=='__main__':unittest.main()
