import unittest
import numpy as np
from apply_scene_art import gather_scene,apply_samples


class SceneArtTests(unittest.TestCase):
    def test_reused_pixel_has_one_colour_and_sheets_stay_separate(self):
        a=np.full((1,2,4),255,np.uint8);b=a.copy()
        owners=np.array([[1,1,3,0]],np.uint32)
        rgb=np.array([[[1,2,3],[9,9,9],[4,5,6],[7,7,7]]],np.uint8)
        addresses,colours=gather_scene(owners,rgb)
        apply_samples(a,b,addresses,colours)
        self.assertEqual(a[0,0].tolist(),[1,2,3,255])
        self.assertEqual(b[0,0].tolist(),[4,5,6,255])
        self.assertTrue(np.all(a[0,1]==255))

    def test_hidden_source_cannot_be_repainted(self):
        a=np.zeros((1,1,4),np.uint8)
        with self.assertRaises(ValueError):apply_samples(a,a.copy(),np.array([0]),np.ones((1,3),np.uint8))


if __name__=='__main__':unittest.main()
