import unittest
from PIL import Image
import numpy as np
from town_foreground import special_layers,scene_region


class ForegroundTests(unittest.TestCase):
    def test_native_special_mapping_and_bottom_anchor(self):
        layers=[dict(cell=[12,4],piece=155),dict(cell=[12,4],piece=155),dict(cell=[0,0],piece=218)]
        result=special_layers(layers)
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]['frame'],12)
        self.assertEqual(result[0]['world'],[224,33])

    def test_foreground_owner_is_separate_from_terrain(self):
        atlas=Image.new('RGBA',(32,4096),(10,20,30,255))
        special=Image.new('RGBA',(64,224*18))
        special.putpixel((0,223),(200,100,50,255))
        layer=dict(cell=[0,0],piece=359,frame=1,block=0,world=[-32,-31])
        meta=dict(density=1,cell=32,rows=128,layers=[layer])
        image,owners=scene_region(meta,atlas,special,[-32,-31,64,32])
        self.assertEqual(image.getpixel((0,31)),(200,100,50,255))
        self.assertEqual(int(owners[31,0]),atlas.width*atlas.height+223*64+1)
        self.assertEqual(int(owners[0,0]),1)
        self.assertTrue(np.all(owners[:,32:]==0))


if __name__=='__main__':unittest.main()
