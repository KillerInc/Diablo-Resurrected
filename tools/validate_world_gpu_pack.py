"""Validate new BC7 world sheets and preserve an already validated base pack."""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path
from PIL import Image, ImageChops, ImageStat
from gpu_index import read_index
from install_layout_table import sha
from validate_gpu_pack import dds


def validate(pack, hd, base_proof, proof_names):
    Image.MAX_IMAGE_PIXELS = None
    base = json.loads(base_proof.read_text())
    old_records = read_index(hd / 'sprites.gpus')
    records = read_index(pack / 'HD/sprites.gpus')
    proof = {}
    for name in proof_names:
        part = json.loads((pack / name).read_text())
        assert not set(part) & set(proof)
        proof.update(part)
    assert set(records) == set(old_records) | set(proof)
    assert not set(old_records) & set(proof)
    for name, record in old_records.items():
        assert records[name] == record, name
    assert sha(hd / 'layouts.csv') == base['layout_sha256']
    assert (pack / 'HD/layouts.csv').read_bytes() == (hd / 'layouts.csv').read_bytes()
    files = dict(base['files'])
    files['sprites.gpus'] = sha(pack / 'HD/sprites.gpus')
    sources = dict(base['source_png_hashes'])
    for name, digest in base['files'].items():
        assert sha(hd / name) == digest, name
    for name, digest in sources.items():
        assert sha(hd / name) == digest, name
    pages, total = base['pages'], base['texture_bytes']
    qualities = {}
    names = sorted(proof)
    sample = set(names[::max(1, len(names) // 24)]) | {names[-1]}
    for number, rel in enumerate(names, 1):
        item = proof[rel]
        assert sha(hd / rel) == item['source_sha256'], rel
        sources[rel] = item['source_sha256']
        lines = records[rel]
        magic, density, columns, rows, width, height, count = lines[0].split()
        density, columns, rows, width, height, count = map(int, (density, columns, rows, width, height, count))
        assert magic == 'D1R_GPU_SHEET_V1' and density == 4
        assert (columns, rows) == (item['columns'], item['rows'])
        assert len(lines) == 1 + count + columns * rows
        dimensions, decoded = [], None
        for page_index, line in enumerate(lines[1:1 + count]):
            name, w, h = line.split()
            w, h = int(w), int(h)
            assert Path(name).name == name and w % 4 == h % 4 == 0
            path = (pack / 'HD' / rel).parent / name
            data = path.read_bytes()
            assert struct.unpack('<II', data[:8]) == (w, h) and len(data) == w * h + 8
            files[path.relative_to(pack / 'HD').as_posix()] = hashlib.sha256(data).hexdigest().upper()
            dimensions.append((w, h))
            image = dds(data[8:], w, h)  # Decode every real BC7 page.
            if page_index == 0:
                decoded = image
            pages += 1
            total += w * h
        frames = [tuple(map(int, line.split())) for line in lines[1 + count:]]
        assert frames == list(map(tuple, item['frames']))
        for page, x, y, w, h, cx, cy in frames:
            assert 0 <= page < count and min(x, y, w, h, cx, cy) >= 0
            pw, ph = dimensions[page]
            assert x + w <= pw and y + h <= ph and cx + w <= width * 4 and cy + h <= height * 4
        if rel in sample:
            selected = next((i for i, f in enumerate(frames) if f[0] == 0 and f[3] and f[4]), None)
            if selected is not None:
                page, x, y, w, h, cx, cy = frames[selected]
                column, row = divmod(selected, rows)
                with Image.open(hd / rel) as source:
                    cw, ch = source.width // columns, source.height // rows
                    reference = source.crop((column * cw, row * ch, (column + 1) * cw, (row + 1) * ch))
                    reference = reference.resize((width * 4, height * 4), Image.Resampling.NEAREST).convert('RGBA').crop((cx, cy, cx + w, cy + h))
                difference = ImageChops.difference(reference, decoded.crop((x, y, x + w, y + h)))
                visible = reference.getchannel('A').point(lambda alpha: 255 if alpha > 16 else 0)
                rgb = math.sqrt(sum(v * v for v in ImageStat.Stat(difference.convert('RGB'), visible).rms) / 3)
                alpha = ImageStat.Stat(difference).rms[3]
                assert rgb < 20 and alpha < 20, (rel, rgb, alpha)
                qualities[rel] = {'rgb_rmse': rgb, 'alpha_rmse': alpha}
        if number % 50 == 0:
            print(f'Validated {number}/{len(proof)} new sheets', flush=True)
    assert total == base['texture_bytes'] + sum(item['gpu_bytes'] for item in proof.values())
    result = dict(sheets=len(records), pages=pages, texture_bytes=total, density=4,
                  files=files, source_png_hashes=sources, layout_sha256=base['layout_sha256'],
                  preserved_base_sheets=len(old_records), new_sheets=len(proof), quality_samples=qualities,
                  all_pages_decoded=True, original_records_unchanged=True)
    (pack / 'validated-gpu-pack.json').write_text(json.dumps(result, indent=2))
    print(f'PASS: {len(records)} compiled sheets, {pages} decoded BC7 pages, {total / 2**30:.3f} GiB; {len(qualities)} quality samples')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('pack', 'hd', 'base_proof'):
        parser.add_argument(name, type=Path)
    parser.add_argument('--proofs', nargs='+', required=True)
    args = parser.parse_args()
    validate(args.pack, args.hd, args.base_proof, args.proofs)
