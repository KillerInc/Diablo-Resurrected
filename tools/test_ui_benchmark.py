import unittest
from ui_benchmark import window, thread_window


class BenchmarkWindowTest(unittest.TestCase):
    def test_excludes_inventory_open_and_warmup(self):
        rows = [{'mode': 'HD', 'seconds': str(i)} for i in range(5, 51)]
        chosen, start, end = window(rows, 15, 20)
        self.assertEqual((start, end), (20, 40))
        self.assertEqual([int(r['seconds']) for r in chosen], list(range(21, 41)))

    def test_rejects_short_replay(self):
        with self.assertRaises(AssertionError):
            window([{'mode': 'HD', 'seconds': '10'}], 15, 20)

    def test_aggregates_cpu_work_over_full_window_and_orders_async_results(self):
        records = [{'active_ms': '20000', 'thread_cpu_total_ns': '16000000000'},
                   {'active_ms': '0', 'thread_cpu_total_ns': '1000000000'}]
        result = thread_window(records)
        self.assertEqual(result['cpu_work_fraction'], .75)
        self.assertEqual(result['wall_minus_cpu_ms'], 5000)


if __name__ == '__main__': unittest.main()
