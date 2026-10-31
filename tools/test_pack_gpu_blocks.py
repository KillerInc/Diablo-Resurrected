"""Synthetic bit-exact check for the optional native-4x BC7 shortcut."""
import sys
from pathlib import Path
import numpy as np
from PIL import Image
from pack_gpu_sprites import constant_blocks


if __name__=='__main__':
    assert len(sys.argv)==2,'Usage: test_pack_gpu_blocks.py PRIVATE_ENCODER_PACKAGE_DIRECTORY'
    sys.path.insert(0,str(Path(sys.argv[1]).resolve()))
    import ispc_texcomp as bc
    settings=bc.BC7EncSettings.from_profile('alpha_fast');rng=np.random.default_rng(17)
    cache={}
    for alpha_mode in ('binary','continuous'):
        pixels=rng.integers(0,256,(32,32,4),dtype=np.uint8)
        if alpha_mode=='binary':pixels[:,:,3]=np.where(pixels[:,:,3]>128,255,0)
        image=Image.fromarray(pixels,'RGBA').resize((128,128),Image.Resampling.NEAREST)
        expected=bc.compress_blocks_bc7(bc.RGBASurface(image.tobytes(),128,128),settings)
        assert constant_blocks(image,bc,settings,cache)==expected
        assert constant_blocks(image,bc,settings,cache)==expected
        image.putpixel((1,1),(123,17,8,200))
        assert constant_blocks(image,bc,settings,cache) is None
    print('PASS: solid-block BC7 shortcut is bit-exact, reuses cached colours and preserves general fallback')
