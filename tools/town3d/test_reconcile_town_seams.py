import unittest
import numpy as np
from reconcile_town_seams import matching_edges,balanced_targets


class SeamConstraints(unittest.TestCase):
    def test_only_fragment_discontinuities_with_matching_original_material(self):
        field=np.array([[30]*3,[30]*3,[30]*3,[80]*3],dtype=np.uint8)
        rgb=np.array([[20]*3,[80]*3,[80]*3,[20]*3],dtype=np.uint8)
        # a->b uses one-based source IDs. Consecutive source pixels are not seams.
        edges=matching_edges(np.array([1,1,3]),np.array([2,3,4]),field,rgb,1)
        np.testing.assert_array_equal(edges,[[0,2]])

    def test_pair_balances_without_moving_material_more_than_limit(self):
        rgb=np.array([[20,30,40],[60,70,80]],dtype=np.uint8)
        nodes,delta=balanced_targets(np.array([[0,1]]),rgb)
        np.testing.assert_allclose(rgb[nodes]+delta,[[40,50,60],[40,50,60]])
        _,delta=balanced_targets(np.array([[0,1]]),rgb,limit=5)
        self.assertLessEqual(float(abs(delta).max()),5)


if __name__=='__main__':unittest.main()
