import unittest
import numpy as np
from PIL import Image
from audit_town_art import visible_sources


class SourceVisibility(unittest.TestCase):
    def test_repeated_source_and_partial_occlusion_across_stripes(self):
        tiles={1:Image.new('RGBA',(2,2),(10,20,30,255)),2:Image.new('RGBA',(2,2),(40,50,60,255))}
        layers=[dict(frame=1,x=0,y=0),dict(frame=1,x=2,y=0),dict(frame=2,x=1,y=1)]
        result=visible_sources(layers,tiles,4,4,2,2,stripe=1)
        # Both occurrences of frame one lose different bottom corners, so all
        # four of its canonical pixels still appear somewhere in the scene.
        self.assertTrue(result[4:8].all());self.assertTrue(result[8:12].all())
        self.assertEqual(int(result.sum()),8)


if __name__=='__main__':unittest.main()
