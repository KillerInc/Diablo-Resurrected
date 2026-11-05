"""Synthetic tests only: no game artwork or archive is required."""
import struct
import unittest
from prepare_mpq_art import cel_frame, groups, header_width, tile_frame


class ArtDecodeTests(unittest.TestCase):
    def test_cel_runs_orientation_and_transparency(self):
        indices,mask=cel_frame(bytes([2,0,7,254,252]),4,False)
        self.assertEqual(indices.size,(4,2))
        self.assertEqual(indices.tobytes(),bytes([0,0,0,0,0,7,0,0]))
        self.assertEqual(mask.tobytes(),bytes([0,0,0,0,255,255,0,0]))
        with self.assertRaises(AssertionError):cel_frame(bytes([5,1,2,3,4,5]),4,False)

    def test_tile_geometry_and_opaque_zero(self):
        indices,mask=tile_frame(bytes(1024),0)
        self.assertEqual(indices.tobytes(),bytes(1024))
        self.assertEqual(mask.tobytes(),bytes([255])*1024)
        for kind in (2,3,4,5):
            widths=list(range(2,33,2))+(list(range(30,1,-2)) if kind in (2,3) else [32]*16)
            encoded=bytearray()
            for row,width in enumerate(widths):
                pad=(kind in (2,3) or row<16) and row%2==0
                if pad and kind in (2,4):encoded.extend(b'\0\0')
                encoded.extend([row+1]*width)
                if pad and kind in (3,5):encoded.extend(b'\0\0')
            indices,mask=tile_frame(encoded,kind)
            self.assertEqual(sum(v==255 for v in mask.tobytes()),sum(widths))
            start=30 if kind in (2,4) else 0
            self.assertEqual(indices.getpixel((start,31)),1)
            self.assertEqual(mask.getpixel((start,31)),255)
            self.assertEqual(mask.getpixel((31-start,31)),0)

    def test_tile_padding_and_no_header_guess(self):
        # First two data bytes happen to equal a standard CEL header marker.
        row=bytes([10,0]+[4]*9+[22]+[5]*22)
        data=row+bytes([32]+[6]*32)*31
        indices,mask=tile_frame(data+b'\0\0',1)
        self.assertEqual(indices.getpixel((0,31)),0)
        self.assertEqual(mask.getpixel((0,31)),255)
        with self.assertRaises(AssertionError):tile_frame(data+b'\x01',1)

    def test_offsets_and_header_width(self):
        rows=bytes([4,1,2,3,4])*64
        frame=struct.pack('<5H',10,170,330,0,0)+rows
        data=struct.pack('<3I',1,12,12+len(frame))+frame
        parsed=groups(data)
        self.assertEqual(header_width(parsed),4)
        self.assertEqual(cel_frame(parsed[0][0],4)[0].size,(4,64))
        damaged=bytearray(data);struct.pack_into('<I',damaged,8,len(data)+1)
        with self.assertRaises(AssertionError):groups(damaged)


if __name__=='__main__':unittest.main()
