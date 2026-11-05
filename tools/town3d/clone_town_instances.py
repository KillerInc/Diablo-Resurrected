"""Allocate private atlas frames for one building's native draw slots."""

import argparse
from collections import Counter
import json
from pathlib import Path

from PIL import Image


def clone(meta, atlas, rect, selected_frames, output):
    size, columns, rows = (meta[k] for k in ('cell', 'columns', 'rows'))
    if atlas.size != (columns * size, rows * size):
        raise ValueError('Atlas does not match the town project')
    left, top, width, height = rect
    layers = [layer for layer in meta['layers'] if layer['frame'] in selected_frames
              and left <= layer['world'][0] < left + width and top <= layer['world'][1] < top + height]
    if not layers or len(layers) > rows:
        raise ValueError('Select between one and one column of native draw slots')

    def key(layer):
        return (*layer['cell'], layer['piece'], layer['frame'])

    occurrences = Counter(key(layer) for layer in meta['layers'])
    if any(occurrences[key(layer)] != 1 for layer in layers):
        raise ValueError('A binding must identify exactly one native slot')

    expanded = Image.new('RGBA', (atlas.width + size, atlas.height))
    expanded.paste(atlas)
    bindings = []
    for index, layer in enumerate(layers):
        col, row = divmod(layer['frame'] - 1, rows)
        box = (col * size, row * size, (col + 1) * size, (row + 1) * size)
        expanded.paste(atlas.crop(box), (atlas.width, index * size))
        bindings.append((*key(layer), columns * rows + index + 1))

    output.mkdir(parents=True)
    expanded.save(output / 'town-rc2-house.png')
    lines = ['D1R_TOWN_INSTANCE_V1', *(' '.join(map(str, binding)) for binding in bindings)]
    (output / 'town-rc2-house.bindings').write_bytes(('\n'.join(lines) + '\n').encode('ascii'))
    print(f'Cloned {len(bindings)} native draw slots')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('project', 'atlas', 'region', 'selection', 'output'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    clone(json.loads(args.project.read_text()), Image.open(args.atlas).convert('RGBA'),
          json.loads(args.region.read_text())['rect'], set(json.loads(args.selection.read_text())['frames']), args.output)
