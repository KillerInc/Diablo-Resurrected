import unittest
import numpy as np
from PIL import Image
from pack_ground_art import compatible_frame, inset_distance, ground_only_frames


class GroundTests(unittest.TestCase):
    def test_exact_rim_alpha_and_hidden_rgb(self):
        original=np.full((64,64,4),[20,30,10,0],dtype=np.uint8);original[4:60,4:60]=[20,30,10,255]
        paint=np.full_like(original,[100,70,40,255]);paint[20:35,20:35,:3]=[30,60,90]
        out,report=compatible_frame(Image.fromarray(original),Image.fromarray(paint),border=4,feather=4)
        out=np.asarray(out);edge=inset_distance(original[:,:,3])<=4
        np.testing.assert_array_equal(out[edge],original[edge]);np.testing.assert_array_equal(out[:,:,3],original[:,:,3])
        self.assertGreater(report['changed_pixels'],0)

    def test_opaque_frame_edges_also_protected(self):
        original=Image.new('RGBA',(32,32),(20,20,20,255));paint=Image.new('RGBA',(32,32),(90,20,30,255))
        paint.putpixel((16,16),(200,200,200,255));out,_=compatible_frame(original,paint,border=4)
        self.assertEqual(out.getpixel((0,16)),original.getpixel((0,16)))
        self.assertEqual(out.getpixel((31,16)),original.getpixel((31,16)))

    def test_shared_architecture_frame_is_excluded(self):
        micros=np.zeros((2,16),dtype='<u2');micros[0,14]=5;micros[1,12]=5
        self.assertNotIn(5,ground_only_frames(micros,bytes([0,0])))
        micros[1,12]=6
        self.assertIn(5,ground_only_frames(micros,bytes([0,0])))
        self.assertNotIn(5,ground_only_frames(micros,bytes([1,0])))

    def test_missing_painted_interior_rejected(self):
        with self.assertRaises(ValueError):compatible_frame(Image.new('RGBA',(32,32),'white'),Image.new('RGBA',(32,32)))

    def test_constant_paint_does_not_flatten_native_material_transition(self):
        pixels=np.zeros((64,64,4),dtype=np.uint8);pixels[:,:,3]=255
        pixels[:,:,:3]=np.arange(64,dtype=np.uint8)[None,:,None]+10
        result,_=compatible_frame(Image.fromarray(pixels),Image.new('RGBA',(64,64),(180,90,30,255)),2,4)
        delta=np.abs(np.asarray(result).astype(int)-pixels.astype(int))
        self.assertLessEqual(delta[12:52,12:52,:3].max(),1)


if __name__=='__main__':unittest.main()
