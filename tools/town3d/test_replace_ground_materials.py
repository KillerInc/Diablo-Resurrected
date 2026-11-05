import unittest
import numpy as np
from PIL import Image
from replace_ground_materials import phase, periodic_material, sample, replace, preserve_authored_pixels


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

    def test_large_material_retains_native_texels_without_reduction(self):
        rng=np.random.default_rng(23)
        source=rng.integers(20,90,(512,512,3),dtype=np.uint8)
        expected=source[192:320,192:320].astype(np.float32)
        # Normalisation is channel-wide: it must not remove spatial detail.
        actual=periodic_material(Image.fromarray(source),(45,35,25))
        ratio=actual[16,16]/expected[16,16]
        np.testing.assert_allclose(actual[8:120,8:120],expected[8:120,8:120]*ratio,rtol=1e-6)

    def test_painted_object_base_survives_ground_replacement(self):
        original=np.full((4,4,4),[70,40,20,255],np.uint8)
        ground=np.full_like(original,[25,30,15,255]);mask=np.zeros((4,4),bool);mask[1:3,1:3]=True
        result=preserve_authored_pixels(original,ground,mask)
        np.testing.assert_array_equal(result[mask],original[mask])
        np.testing.assert_array_equal(result[~mask],ground[~mask])
        with self.assertRaises(ValueError):preserve_authored_pixels(original,ground,np.zeros((3,3),bool))

    def test_replacement_changes_rgb_preserves_mask_and_hidden_pixels(self):
        src=np.full((128,128,4),[55,42,48,0],dtype=np.uint8);src[10:118,10:118,3]=255
        dirt=np.full((128,128,3),[52,43,32],dtype=float);grass=np.full((128,128,3),[28,35,23],dtype=float)
        out=np.asarray(replace(Image.fromarray(src),dirt,grass,(0,0)))
        np.testing.assert_array_equal(out[:,:,3],src[:,:,3]);np.testing.assert_array_equal(out[src[:,:,3]==0],src[src[:,:,3]==0])
        self.assertGreater(np.abs(out[64,64,:3].astype(int)-src[64,64,:3]).max(),8)


if __name__=='__main__':unittest.main()
