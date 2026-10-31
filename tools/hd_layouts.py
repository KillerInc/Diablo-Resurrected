"""Consolidated HD layout metadata. Runtime consumes HD/layouts.csv only.

Offline render outputs may still carry .layout files; collect them into the
single table before installation. No PNG data is read or uploaded by this tool.
"""
from pathlib import Path
import argparse
import csv
import io
import math
import os


def key(path):
    path = str(path)
    if not path or path.startswith('/') or len(path.encode('utf-8')) > 1024:
        raise ValueError('Invalid relative layout path')
    if any(c in path for c in ('\\', ':')) or any(ord(c) < 32 for c in path):
        raise ValueError('Use a safe HD-relative path with forward slashes')
    if any(p in ('', '.', '..') for p in path.split('/')):
        raise ValueError('Invalid layout path segment')
    return path.translate(str.maketrans('ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'))


def validate_layout(value):
    if not value or len(value.encode('utf-8')) > 256 or any(ord(c) < 32 and c != '\t' for c in value):
        raise ValueError('Invalid layout metadata')
    fields = value.split()
    if fields and fields[0] == 'D1R_SHEET_V1':
        if len(fields) != 4:
            raise ValueError('Expected density and two anchors')
        density, x, y = map(int, fields[1:])
        if density not in (1, 2, 4, 8, 16) or min(x, y) < 0:
            raise ValueError('Invalid density or anchor')
    else:
        if len(fields) != 4 or not all(math.isfinite(float(v)) for v in fields):
            raise ValueError('Expected four finite image layout numbers')
        if min(map(float, fields[:2])) <= 0:
            raise ValueError('Image dimensions must be positive')
    return value


def read_table(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        reader = csv.reader(f, strict=True)
        header = next(reader, None)
        if header != ['path', 'layout']:
            raise ValueError('Expected path,layout CSV header')
        rows = {}
        for row in reader:
            if not row:
                continue
            if len(row) != 2:
                raise ValueError('Expected two CSV fields')
            name = key(row[0])
            if name in rows:
                raise ValueError('Duplicate layout path: ' + name)
            rows[name] = validate_layout(row[1])
    return rows


def table_bytes(rows):
    stream = io.StringIO(newline='')
    writer = csv.writer(stream, lineterminator='\n')
    writer.writerow(['path', 'layout'])
    seen = set()
    for path, value in sorted(rows.items()):
        name = key(path)
        if name in seen:
            raise ValueError('Duplicate layout path: ' + name)
        seen.add(name)
        writer.writerow([name, validate_layout(value)])
    return stream.getvalue().encode('utf-8')


def write_table(path, rows):
    path = Path(path)
    data = table_bytes(rows)
    temporary = path.with_name(path.name + '.tmp')
    try:
        temporary.write_bytes(data)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def collect(hd):
    hd = Path(hd).resolve()
    rows = {}
    for sidecar in sorted(hd.rglob('*.layout')):
        # These are offline inputs, never a runtime fallback.
        image = sidecar.with_suffix('')
        if not image.is_file():
            raise ValueError('Layout has no corresponding image: ' + str(sidecar))
        image.resolve().relative_to(hd)
        name = key(image.relative_to(hd).as_posix())
        if name in rows:
            raise ValueError('Duplicate layout path: ' + name)
        rows[name] = validate_layout(sidecar.read_text(encoding='utf-8-sig').strip())
    return rows


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('hd', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    rows = collect(args.hd)
    if not rows:
        parser.error('No offline sidecars found; existing CSV was not changed')
    write_table(args.output, rows)
    assert read_table(args.output) == rows
    print('Collected', len(rows), 'unchanged layouts into', args.output)
