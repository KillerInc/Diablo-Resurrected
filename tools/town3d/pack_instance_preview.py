"""Append cloned terrain frames for one registered RC2 scene preview."""

import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np
from PIL import Image

from town_foreground import scene_region


def pack(meta, atlas, foreground, rect, edited, output):
    baseline, owners = scene_region(meta, atlas, foreground, rect)
    if edited.size != baseline.size or edited.getchannel('A').tobytes() != baseline.getchannel('A').tobytes():
        raise ValueError('The edited scene must retain the native projection and alpha')
    pixels = np.asarray(edited)
    changed = np.any(np.asarray(baseline) != pixels, axis=2)
    consumed = np.zeros_like(changed)
    size, rows, density = (meta[k] for k in ('cell', 'rows', 'density'))
    if atlas.width != size * meta['columns'] or atlas.height != size * rows:
        raise ValueError('The original atlas must match the project geometry')
    expanded = Image.new('RGBA', (atlas.width + size, atlas.height))
    expanded.paste(atlas)
    bindings = {}
    slot_counts = Counter((*layer['cell'], layer['piece'], layer['frame']) for layer in meta['layers'])
    first_frame = meta['columns'] * rows + 1
    for layer in meta['layers']:
        x, y = ((layer['world'][i] - rect[i]) * density for i in (0, 1))
        left, top = max(0, x), max(0, y)
        right, bottom = min(edited.width, x + size), min(edited.height, y + size)
        if left >= right or top >= bottom:
            continue
        col, row = divmod(layer['frame'] - 1, rows)
        ax, ay = col * size, row * size
        yy, xx = np.mgrid[top:bottom, left:right]
        addresses = (ay + yy - y) * atlas.width + ax + xx - x + 1
        region = np.s_[top:bottom, left:right]
        selected = (owners[region] == addresses) & changed[region]
        if not selected.any():
            continue
        key = (*layer['cell'], layer['piece'], layer['frame'])
        if slot_counts[key] != 1 or len(bindings) >= rows:
            raise ValueError('Bindings must be unique and fit the appended column')
        tile = np.array(atlas.crop((ax, ay, ax + size, ay + size)))
        tile[yy[selected] - y, xx[selected] - x] = pixels[yy[selected], xx[selected]]
        expanded.paste(Image.fromarray(tile), (atlas.width, len(bindings) * size))
        bindings[key] = first_frame + len(bindings)
        consumed[region] |= selected
    if not bindings or not np.array_equal(consumed, changed):
        raise ValueError('All changed pixels must belong to opaque terrain slots')
    output.mkdir(parents=True)
    expanded.save(output / 'town-rc2-rock.png')
    (output / 'bindings.json').write_text(json.dumps([(*key, index) for key, index in bindings.items()], indent=2))
    print(f'Packed {len(bindings)} draw slots for {int(changed.sum())} changed pixels')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('project', 'atlas', 'foreground', 'rect', 'edited', 'output'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    pack(json.loads(args.project.read_text()), Image.open(args.atlas).convert('RGBA'),
         Image.open(args.foreground).convert('RGBA'), json.loads(args.rect.read_text()),
         Image.open(args.edited).convert('RGBA'), args.output)
