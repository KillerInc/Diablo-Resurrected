"""Check performance CSV output and overlay hotkeys from isolated game replays."""
import argparse
import csv
import io
import json
from pathlib import Path


def validate(root):
    root = Path(root)
    proof_path = root / 'validation.json'
    proof = json.loads(proof_path.read_text())
    results = {}
    for name in ['gameplay-a', 'gameplay-b', 'ui']:
        text = (root / (name + '-performance.csv')).read_text()
        rows = list(csv.DictReader(io.StringIO('\n'.join(line for line in text.splitlines() if not line.startswith('#')))))
        assert len(rows) >= 2, name
        assert all(None not in row for row in rows), name
        for row in rows:
            assert int(row['frames']) > 0
            assert float(row['max_ms']) >= float(row['avg_ms']) > 0
            assert 0 < float(row['p95_ms']) <= float(row['max_ms'])
            assert int(row['over50']) <= int(row['over33']) <= int(row['frames'])
            assert int(row['pinned']) == proof['class_png_count']
            assert int(row['sheet_bytes']) >= proof['preload']['bytes']
            assert all(float(row[field]) >= 0 for field in ['draw_cpu_ms', 'compose_cpu_ms', 'present_cpu_ms', 'hits', 'misses', 'decodes', 'failures', 'evictions', 'decode_ms'])
        log = (root / (name + '.log')).read_text(errors='replace')
        assert 'Performance overlay: on' in log
        if name == 'ui':
            assert 'Performance overlay: off' in log
            assert {row['mode'] for row in rows} == {'Classic', 'HD'}
        results[name] = {'rows': len(rows), 'modes': sorted({row['mode'] for row in rows}), 'pinned': proof['class_png_count']}
    proof['performance_monitor'] = results
    proof['checks']['performance_monitor'] = True
    proof_path.write_text(json.dumps(proof, indent=2))
    print('PASS: performance CSV values, pinned cache, F11 on/off and HD/Classic modes', results)
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    validate(parser.parse_args().root)
