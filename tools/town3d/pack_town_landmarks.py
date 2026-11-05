"""Allocate private draw-slot frames for town landmarks and native variants."""

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

from town_canvas import fragments
from town_states import southern_warp_states


def read(path):
    return json.loads(path.read_text())


def key(layer):
    return (*layer['cell'], layer['piece'], layer['frame'])


def pack(project, plan, previous, native, variants, output):
    meta = read(project / 'project.json')
    size, cols, rows = (meta[k] for k in ('cell', 'columns', 'rows'))
    original_count = cols * rows
    first = original_count + 1
    layers = meta['layers']
    views = read(plan)['views']
    owners = {}
    for view in views:
        region = Path(view['region'])
        left, top, width, height = read(region / 'region.json')['rect']
        selected = set(view['frames'])
        for layer in layers:
            x, y = layer['world']
            if layer['frame'] in selected and left <= x < left + width and top <= y < top + height:
                owners.setdefault(key(layer), set()).add(view['id'])

    cells = {tuple(layer['cell']): layer['piece'] for layer in layers}
    micros = np.frombuffer((native / 'town.min').read_bytes(), dtype='<u2').reshape(-1, 16)
    megas = np.frombuffer((variants / 'town.til').read_bytes(), dtype='<u2').reshape(-1, 4)
    states = southern_warp_states(cells, megas, (native / 'sector3s.dun').read_bytes(),
                                  (native / 'sector1s.dun').read_bytes())
    for state in sorted(variants.glob('*-native-object-map.json')):
        states[state.name.removesuffix('-native-object-map.json')] = {
            (x, z): piece for obj in read(state) for x, z, piece, _ in obj['source_cells']
        }
    state_counts = {}
    for state, layout in sorted(states.items()):
        changed = {pos: piece for pos, piece in layout.items() if piece != cells.get(pos)}
        state_layers = fragments(micros, changed, rows)
        for layer in state_layers:
            owners.setdefault(key(layer), set()).add(state)
        state_counts[state] = len(state_layers)

    atlas = Image.open(previous / 'town-rc2-combined.png').convert('RGBA')
    if atlas.height != rows * size or atlas.width < cols * size or atlas.width % size:
        raise ValueError('Previous atlas does not match town geometry')
    header, *records = (previous / 'town-rc2-combined.bindings').read_text().splitlines()
    if header != 'D1R_TOWN_INSTANCE_V1':
        raise ValueError('Unsupported binding format')
    bindings = {}
    for record in records:
        x, z, piece, original, private = map(int, record.split())
        slot = (x, z, piece, original)
        if slot in bindings or private != first + len(bindings):
            raise ValueError('Expected a sequential, unique set of previous bindings')
        bindings[slot] = private
    previous_count = len(bindings)
    pending = sorted(owners.keys() - bindings.keys())
    count = previous_count + len(pending)
    if count > 4096:
        raise ValueError('The runtime test supports at most 4096 private frames')
    extra = (count + rows - 1) // rows
    result = Image.new('RGBA', ((cols + extra) * size, atlas.height))
    result.paste(atlas)
    for slot in pending:
        original = slot[-1]
        col, row = divmod(original - 1, rows)
        src = (col * size, row * size, (col + 1) * size, (row + 1) * size)
        column, y = divmod(len(bindings), rows)
        result.paste(atlas.crop(src), ((cols + column) * size, y * size))
        bindings[slot] = first + len(bindings)

    output.mkdir(parents=True)
    result.save(output / 'town-rc2-combined.png')
    with (output / 'town-rc2-combined.bindings').open('w', encoding='ascii', newline='\n') as file:
        file.write(header + '\n')
        for slot, private in bindings.items():
            file.write(' '.join(map(str, (*slot, private))) + '\n')
    report = dict(columns=cols + extra, rows=rows, bindings=count, previous=previous_count,
                  state_slots=state_counts, landmarks=sorted({name for group in owners.values() for name in group}),
                  slots=[dict(cell=list(slot[:2]), piece=slot[2], original=slot[3], private=private,
                              regions=sorted(owners.get(slot, ()))) for slot, private in bindings.items()])
    (output / 'landmarks.json').write_text(json.dumps(report, indent=2))
    print(f'Packed {count} private slots across {cols + extra} atlas columns')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('project', 'plan', 'previous', 'native', 'variants', 'output'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    pack(args.project, args.plan, args.previous, args.native, args.variants, args.output)
