import unittest
import numpy as np
from town_states import fill_tile, sector_tile, tile_frames, southern_warp_states


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

    def test_southern_warps_restore_sector_boundary_and_all_random_floor_ids(self):
        megas=np.arange(332*4,dtype=np.uint16).reshape(332,4)
        def dun(w,h,tile):
            return np.r_[np.array([w,h],dtype='<u2'),np.full(w*h,tile,dtype='<u2')].astype('<u2').tobytes()
        before={(x,z):9999 for x in range(50) for z in range(85)}
        states=southern_warp_states(before,megas,dun(23,23,5),dun(25,23,6))
        self.assertEqual(states['caves-open'][16,68],int(megas[4,0]))
        self.assertEqual(states['caves-closed'][16,68],int(megas[331,0]))
        self.assertEqual(states['caves-closed'][16,70],int(megas[330,0]))
        self.assertEqual(states['hell-open'][46,78],int(megas[5,0]))
        for floor in (1,2,3,4):
            # The final x=45 replacement overwrites the right edge of x=44.
            self.assertEqual(states[f'hell-closed-floor-{floor}'][46,78],int(megas[floor-1,1]))
        self.assertTrue(all(v==9999 for v in before.values()))


if __name__=='__main__':unittest.main()
