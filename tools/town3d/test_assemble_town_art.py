import unittest
import numpy as np
from assemble_town_art import gather,write_samples


class CanonicalSamples(unittest.TestCase):
    def test_repeated_locations_resolve_one_source_sample(self):
        owners=np.array([[5,6,5],[9,0,6]],dtype=np.uint32)
        rgb=np.arange(18,dtype=np.uint8).reshape(2,3,3)
        address,colours,repeated=gather(owners,rgb,{1},2)
        np.testing.assert_array_equal(address,[4,5])
        np.testing.assert_array_equal(colours,rgb[0,:2])
        self.assertEqual(repeated,2)

    def test_column_major_source_write_preserves_alpha_and_other_cells(self):
        atlas=np.full((4,4,4),255,dtype=np.uint8);before=atlas.copy()
        write_samples(atlas,np.array([4*4+3]),np.array([[10,20,30]]),2,2)
        np.testing.assert_array_equal(atlas[3,3],[10,20,30,255])
        atlas[3,3]=before[3,3];np.testing.assert_array_equal(atlas,before)

    def test_complete_occurrence_wins_over_first_cropped_occurrence(self):
        owners=np.array([[5,0,5,6],[0,0,7,8]],dtype=np.uint32)
        rgb=np.arange(24,dtype=np.uint8).reshape(2,4,3)
        address,colours,_=gather(owners,rgb,{1},2)
        np.testing.assert_array_equal(address,[4,5,6,7])
        np.testing.assert_array_equal(colours,rgb[:,2:].reshape(4,3))

    def test_rejects_translucent_or_out_of_range_owner(self):
        atlas=np.zeros((4,4,4),dtype=np.uint8)
        with self.assertRaises(ValueError):write_samples(atlas,np.array([4]),np.ones((1,3)),2,2)
        with self.assertRaises(ValueError):write_samples(atlas,np.array([20]),np.ones((1,3)),2,2)


if __name__=='__main__':unittest.main()
