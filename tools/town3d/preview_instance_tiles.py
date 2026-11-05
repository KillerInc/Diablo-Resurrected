"""Prove that two houses can use independent art at their original draw slots."""

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

from town_foreground import scene_region


def preview(project, atlas_path, foreground_path, selection_path, output):
    meta = json.loads((project / 'project.json').read_text())
    atlas = Image.open(atlas_path).convert('RGBA')
    foreground = Image.open(foreground_path).convert('RGBA')
    selected_frames = set(json.loads(selection_path.read_text())['frames'])
    names = ('cabin-east', 'cabin-west')
    regions = {
        name: json.loads((project / 'regions' / name / 'region.json').read_text())['rect']
        for name in names
    }
    bindings = {name: [] for name in names}
    instances = {}
    size = meta['cell']
    for layer in meta['layers']:
        if layer['frame'] not in selected_frames:
            continue
        x, y = layer['world']
        owners = [name for name, (left, top, width, height) in regions.items()
                  if left <= x < left + width and top <= y < top + height]
        if len(owners) != 1:
            raise ValueError(f'Expected one cabin for {layer["name"]}: {owners}')
        key = (*layer['cell'], layer['block'])
        if key in instances:
            raise ValueError(f'Duplicate draw slot: {key}')
        col, row = divmod(layer['frame'] - 1, meta['rows'])
        instances[key] = atlas.crop((col * size, row * size, (col + 1) * size, (row + 1) * size))
        bindings[owners[0]].append(layer)

    east_keys = {(*layer['cell'], layer['block']) for layer in bindings['cabin-east']}
    if not east_keys or not bindings['cabin-west']:
        raise ValueError('Both cabins must have selected roof fragments')
    # Use a conspicuous diagnostic color while retaining native sprite alpha.
    marked = dict(instances)
    for key in east_keys:
        tile = instances[key]
        marker = Image.new('RGBA', tile.size, (166, 35, 82))
        marker.putalpha(tile.getchannel('A'))
        marked[key] = marker

    output.mkdir(parents=True)
    for name, rect in regions.items():
        baseline, _ = scene_region(meta, atlas, foreground, rect)
        cloned, _ = scene_region(meta, atlas, foreground, rect, instance_tiles=instances)
        diagnostic, _ = scene_region(meta, atlas, foreground, rect, instance_tiles=marked)
        if baseline.tobytes() != cloned.tobytes():
            raise ValueError(f'Instance binding changed original pixels: {name}')
        before = np.asarray(baseline)
        after = np.asarray(diagnostic)
        if not np.array_equal(before[:, :, 3], after[:, :, 3]):
            raise ValueError(f'Instance edit changed scene coverage: {name}')
        changed = np.count_nonzero(np.any(before != after, axis=2))
        if bool(changed) != (name == 'cabin-east'):
            raise ValueError(f'Instance edit isolation failed: {name}')
        diagnostic.resize((diagnostic.width // 2, diagnostic.height // 2),
                          Image.Resampling.NEAREST).save(output / f'{name}.png')
        print(f'{name}: {len(bindings[name])} independent draw slots, {changed} diagnostic pixels')
    (output / 'bindings.json').write_text(json.dumps(bindings, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('project', 'atlas', 'foreground', 'selection', 'output'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    preview(args.project, args.atlas, args.foreground, args.selection, args.output)
