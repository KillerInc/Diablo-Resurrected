"""Resample an authored NPC around its unchanged game anchor, offline only.

All cells retain their dimensions, order and count. Body, attached props and
baked shadow receive the same transform. Runtime layouts need no changes.
"""
import argparse
from PIL import Image


def rescale(sheet,rows,anchor,factor):
    if rows<1 or sheet.height%rows or not 0<factor<=1:
        raise ValueError('Invalid native sheet rows or reduction factor')
    width,height=sheet.width,sheet.height//rows
    if not 0<=anchor[0]<=width or not 0<=anchor[1]<=height:
        raise ValueError('Anchor outside native cell')
    result=Image.new('RGBA',sheet.size)
    for row in range(rows):
        frame=sheet.crop((0,row*height,width,(row+1)*height)).convert('RGBA')
        scaled=frame.transform(frame.size,Image.Transform.AFFINE,
            (1/factor,0,anchor[0]*(1-1/factor),0,1/factor,anchor[1]*(1-1/factor)),
            Image.Resampling.BICUBIC)
        result.paste(scaled,(0,row*height))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source');p.add_argument('output');p.add_argument('--rows',type=int,required=True)
    p.add_argument('--anchor',nargs=2,type=float,required=True);p.add_argument('--factor',type=float,required=True)
    a=p.parse_args();rescale(Image.open(a.source),a.rows,a.anchor,a.factor).save(a.output)
