import csv
import json
from pathlib import Path
import tempfile
import unittest
from validate_performance import validate


class PerformanceValidationTest(unittest.TestCase):
    def fixture(self, root):
        (root/'validation.json').write_text(json.dumps({'class_png_count': 1, 'preload': {'bytes': 1024}, 'checks': {}}))
        for name in ['gameplay-a', 'gameplay-b', 'ui']:
            (root/(name+'.log')).write_text('Performance overlay: on\nPerformance overlay: off\n')
            fields = 'mode frames avg_ms p95_ms max_ms over33 over50 pinned sheet_bytes draw_cpu_ms compose_cpu_ms present_cpu_ms hits misses decodes failures evictions decode_ms'.split()
            with (root/(name+'-performance.csv')).open('w', newline='') as file:
                file.write('# synthetic metrics only\n')
                writer = csv.DictWriter(file, fieldnames=fields); writer.writeheader()
                for mode in (['HD', 'Classic'] if name == 'ui' else ['HD', 'HD']):
                    row = dict.fromkeys(fields, 0)
                    row.update(mode=mode, frames=60, avg_ms=16, p95_ms=17, max_ms=20, pinned=1, sheet_bytes=1024)
                    writer.writerow(row)

    def test_accepts_consistent_metrics(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); self.fixture(root)
            result=validate(root)
            self.assertEqual(result['ui']['modes'], ['Classic', 'HD'])
            self.assertTrue(json.loads((root/'validation.json').read_text())['checks']['performance_monitor'])

    def test_rejects_lost_pinned_cache(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); self.fixture(root)
            file=root/'ui-performance.csv'; text=file.read_text().replace('1,1024', '0,1024'); file.write_text(text)
            with self.assertRaises(AssertionError): validate(root)
            self.assertNotIn('performance_monitor', json.loads((root/'validation.json').read_text())['checks'])


if __name__ == '__main__': unittest.main()
