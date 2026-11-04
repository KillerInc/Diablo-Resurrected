import unittest
import numpy as np
from town_states import fill_tile, sector_tile, tile_frames


class StateTests(unittest.TestCase):
    def test_mega_substitution_is_local_and_row_major(self):
        before={(x,z):0 for x in range(4) for z in range(4)}
        after=fill_tile(before,np.array([[1,2,3,4]]),1,1,1)
        self.assertEqual([after[p] for p in ((1,1),(2,1),(1,2),(2,2))],[1,2,3,4])
        self.assertEqual(sum(before[p]!=after[p] for p in before),4)
        self.assertTrue(all(v==0 for v in before.values()))

    def test_open_state_comes_from_sector_not_guessed_tile_id(self):
        data=np.array([3,2,11,12,13,14,15,16],dtype='<u2').tobytes()
        self.assertEqual(sector_tile(data,1,1),15)
        with self.assertRaises(ValueError):sector_tile(data,3,1)
        with self.assertRaises(ValueError):sector_tile(data[:4],0,0)

    def test_frame_types_do_not_change_frame_identity(self):
        micros=np.zeros((4,16),dtype='<u2');micros[0,0]=0x2005;micros[1,0]=6
        self.assertEqual(tile_frames(micros,np.array([[0,1,2,3]]),1),[5,6])


if __name__=='__main__':unittest.main()
