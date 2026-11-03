from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from benchmark import run_benchmark


class BenchmarkTests(unittest.TestCase):
    def test_same_results_for_both_formats(self):
        with TemporaryDirectory() as directory:
            output = Path(directory)
            report = run_benchmark(output, rows=1000, repetitions=1)
            self.assertEqual(len(report["results"]), 3)
            self.assertTrue(all(row["results_match"] for row in report["results"]))
            self.assertTrue((output / "events.parquet").exists())
            self.assertTrue((output / "RESULTS.md").exists())
            self.assertGreater(report["csv_bytes"], 0)

    def test_validation(self):
        with TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                run_benchmark(Path(directory), rows=-5, repetitions=1)


if __name__ == "__main__":
    unittest.main()
