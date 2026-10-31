"""Inventory uncompiled private HD PNGs against their original extracted CL2 grids."""
import argparse
import json
import struct
from pathlib import Path
from PIL import Image
from gpu_index import read_index


def cl2_grid(data):
    def word(offset):
        assert 0 <= offset <= len(data) - 4, 'Truncated CL2 header'
        return struct.unpack_from('<I', data, offset)[0]
    first = word(0)
    # Same list-versus-sheet test used by the engine's Cl2ToClx converter.
    single = (first + 2) * 4 <= len(data) and word((first + 1) * 4) == len(data)
    if single:
        counts = [first]
    else:
        assert first % 4 == 0 and 0 < first <= len(data) - 4
        counts = [word(word(group * 4)) for group in range(first // 4)]
    assert counts and min(counts) > 0 and max(counts) <= 16384
    return len(counts), max(counts), counts


def inventory(hd, originals, density):
    Image.MAX_IMAGE_PIXELS = None
    existing = read_index(hd / 'sprites.gpus')
    records = {}
    for png in sorted(hd.rglob('*.png')):
        rel = png.relative_to(hd).as_posix()
        if rel in existing:
            continue
        original = (originals / rel).with_suffix('.cl2')
        columns, rows, counts = cl2_grid(original.read_bytes())
        with Image.open(png) as image:
            width, height = image.size
        assert width % (columns * density) == height % (rows * density) == 0, rel
        records[rel] = dict(columns=columns, rows=rows, source_density=density,
                            width=width // columns // density, height=height // rows // density,
                            size=[width, height], original_cl2=str(original), counts=counts)
    return records


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('hd', type=Path)
    parser.add_argument('originals', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--density', type=int, choices=(1, 2, 4, 8, 16), default=8)
    args = parser.parse_args()
    records = inventory(args.hd, args.originals, args.density)
    args.output.write_text(json.dumps(records, indent=2))
    print(f'Inventoried {len(records)} uncompiled sheets using original CL2 grids')
