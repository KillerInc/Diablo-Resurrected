"""Merge two town instance atlases which share the same original frames."""

import argparse
import json
from pathlib import Path

from PIL import Image


def merge(first, second, first_bindings, second_bindings, output):
    cell = 128
    original_width, height = 28 * cell, 128 * cell
    first_private_frame = 28 * 128 + 1
    if any(atlas.height != height or atlas.width <= original_width or atlas.width % cell
           for atlas in (first, second)):
        raise ValueError('Expected town atlases with whole appended columns')
    original = (0, 0, original_width, height)
    if first.crop(original).tobytes() != second.crop(original).tobytes():
        raise ValueError('Both atlases must share the same original art')

    count = len(first_bindings) + len(second_bindings)
    keys = {tuple(row[:4]) for row in first_bindings + second_bindings}
    if not first_bindings or not second_bindings or len(keys) != count or count > 256:
        raise ValueError('Bindings must be disjoint and fit two private columns')

    columns = (count + 127) // 128
    merged = Image.new('RGBA', (original_width + columns * cell, height))
    merged.paste(first.crop(original))
    bindings = []
    for source, rows in ((first, first_bindings), (second, second_bindings)):
        for *key, frame in rows:
            index = frame - first_private_frame
            source_column, source_row = divmod(index, 128)
            source_x = original_width + source_column * cell
            if index < 0 or source_x + cell > source.width:
                raise ValueError('Replacement frame is outside the private columns')
            tile = source.crop((source_x, source_row * cell, source_x + cell, (source_row + 1) * cell))
            column, row = divmod(len(bindings), 128)
            merged.paste(tile, (original_width + column * cell, row * cell))
            bindings.append((*key, first_private_frame + len(bindings)))

    output.mkdir(parents=True)
    merged.save(output / 'town-rc2-combined.png')
    lines = ['D1R_TOWN_INSTANCE_V1', *(' '.join(map(str, binding)) for binding in bindings)]
    (output / 'town-rc2-combined.bindings').write_bytes(('\n'.join(lines) + '\n').encode('ascii'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('first', 'second', 'first_bindings', 'second_bindings', 'output'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    merge(Image.open(args.first).convert('RGBA'), Image.open(args.second).convert('RGBA'),
          json.loads(args.first_bindings.read_text()), json.loads(args.second_bindings.read_text()), args.output)
