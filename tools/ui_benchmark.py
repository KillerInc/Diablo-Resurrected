"""Prepare private fixed-scene replays and analyze a separate steady window."""
import argparse
import csv
import io
import json
import math
from pathlib import Path
import shutil
import statistics
import struct


def prepare(source, destination, ticks=12000):
    source, destination = Path(source), Path(destination)
    assert ticks >= 3000 and not destination.exists()
    header = (source / 'demo_7.dmo').read_bytes()[:32]
    assert len(header) == 32 and header[0] == 3
    destination.mkdir(parents=True)
    for file in source.iterdir():
        if file.is_file() and (file.suffix.lower() == '.sv' or file.name == 'diablo.ini'):
            shutil.copy2(file, destination / file.name)
    assert (destination / 'diablo.ini').exists()
    key = struct.pack('<BBIH', 13, 0, ord('i'), 0) + struct.pack('<BBIH', 14, 0, ord('i'), 0)
    (destination / 'demo_7.dmo').write_bytes(header + bytes((0, 0)) * 200 + key + bytes((0, 0)) * (ticks - 200) + bytes((8, 0)))


def read_csv(path):
    return list(csv.DictReader(io.StringIO('\n'.join(line for line in Path(path).read_text(encoding='utf-8-sig').splitlines() if not line.startswith('#')))))


def window(rows, warmup, duration):
    hd = [r for r in rows if r['mode'] == 'HD']
    assert hd
    # One-second interval records: require complete intervals after warm-up.
    start = float(hd[0]['seconds']) + warmup
    end = start + duration
    assert float(hd[-1]['seconds']) >= end, 'Replay is too short for the requested steady window'
    chosen = [r for r in hd if start + 1 <= float(r['seconds']) <= end]
    assert len(chosen) >= duration - 2
    return chosen, start, end


def thread_window(records):
    # Individual Windows CPU-time reads are quantized. Difference the endpoints
    # of the full window instead of assigning each accounting tick to a stage.
    records = sorted(records, key=lambda r: float(r['active_ms']))
    first, last = records[0], records[-1]
    wall = float(last['active_ms']) - float(first['active_ms'])
    work = (int(last['thread_cpu_total_ns']) - int(first['thread_cpu_total_ns'])) / 1e6
    assert wall > 0 and work >= 0
    return {'wall_ms': wall, 'cpu_work_ms': work, 'wall_minus_cpu_ms': wall - work, 'cpu_work_fraction': work / wall}


def analyze(root, case, warmup=15, duration=20):
    root = Path(root)
    rows, start, end = window(read_csv(root / (case + '-performance.csv')), warmup, duration)
    frames = sum(int(r['frames']) for r in rows)
    weighted = lambda field: sum(float(r[field]) * int(r['frames']) for r in rows) / frames
    assert all(int(r['decodes']) == int(r['failures']) == int(r['sheet_bytes']) == 0 for r in rows)
    assert len({r['gpu_page_uploads'] for r in rows}) == 1, 'Warm window includes a GPU page upload'
    result = {'case': case, 'window_seconds': [start, end], 'intervals': len(rows), 'frames': frames,
              'fps': 1000 / weighted('avg_ms'), 'avg_ms': weighted('avg_ms'),
              'draw_cpu_ms': weighted('draw_cpu_ms'), 'present_cpu_ms': weighted('present_cpu_ms'),
              'warm_page_uploads': 0, 'cpu_sprite_decodes': 0,
              'private_bytes': max(int(r['private_bytes']) for r in rows)}
    stage_path = root / (case + '-stages.csv')
    if stage_path.exists():
        stages = read_csv(stage_path)
        result['cpu_stages'] = {}
        for stage in sorted({r['stage'] for r in stages}):
            selected = [r for r in stages if r['stage'] == stage and start + 1 <= float(r['seconds']) <= end]
            count = sum(int(r['frames']) for r in selected)
            result['cpu_stages'][stage] = {field: sum(float(r[field]) for r in selected) / count for field in ('total_cpu_ms', 'thread_cycles')}
    gpu_path = root / (case + '-gpu.csv')
    if gpu_path.exists():
        records = sorted([r for r in read_csv(gpu_path) if r['mode'] == 'HD' and (warmup + 1) * 1000 <= float(r['active_ms']) <= (warmup + 1 + duration) * 1000], key=lambda r: float(r['active_ms']))
        gpu = [float(r['gpu_elapsed_ms']) for r in records]
        if records and 'thread_cpu_total_ns' in records[0]:
            result['main_thread_window'] = thread_window(records)

        assert gpu and all(math.isfinite(x) and x >= 0 for x in gpu)
        gpu.sort()
        result['hardware_gpu'] = {'samples': len(gpu), 'mean_ms': statistics.mean(gpu), 'median_ms': statistics.median(gpu), 'p95_ms': gpu[min(len(gpu) - 1, math.ceil(len(gpu) * .95) - 1)]}
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    a = sub.add_parser('prepare'); a.add_argument('source', type=Path); a.add_argument('destination', type=Path); a.add_argument('--ticks', type=int, default=12000)
    a = sub.add_parser('analyze'); a.add_argument('root', type=Path); a.add_argument('cases', nargs='+'); a.add_argument('--warmup', type=int, default=15); a.add_argument('--duration', type=int, default=20)
    args = p.parse_args()
    if args.command == 'prepare': prepare(args.source, args.destination, args.ticks)
    else: print(json.dumps([analyze(args.root, name, args.warmup, args.duration) for name in args.cases], indent=2))
