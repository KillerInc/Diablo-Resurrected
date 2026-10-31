"""Build owned HLSL into embedded DXBC; no game art is involved."""
from pathlib import Path
import subprocess
import tempfile
root=Path(__file__).resolve().parents[1]
fxc=Path('C:/Program Files (x86)/Windows Kits/10/bin/10.0.22621.0/x64/fxc.exe')
for kind,profile in [('vert','vs_5_1'),('frag','ps_5_1'),('comp','cs_5_1')]:
    with tempfile.TemporaryDirectory() as temporary:
        binary=Path(temporary)/'shader.dxbc'
        subprocess.run([str(fxc),'/nologo','/O3','/T',profile,'/E','main','/Fo',str(binary),str(root/('Source/reincarnated/shaders/nearest.comp.hlsl' if kind=='comp' else f'Source/reincarnated/shaders/sprite.{kind}.hlsl'))],check=True)
        data=binary.read_bytes()
    text='#pragma once\ninline constexpr unsigned char Sprite'+kind.title()+'[] = {\n'
    text+='\n'.join(','.join(str(b) for b in data[i:i+24])+',' for i in range(0,len(data),24))+'\n};\n'
    (root/f'Source/reincarnated/shaders/sprite_{kind}.hpp').write_bytes(text.encode())
    print(kind,len(data),'bytes')
