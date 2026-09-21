"""Protocol v5 must preserve prior screening results, including offline cache writes."""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline/screening"))
from run import protect_existing_outputs, protect_legacy_paths  # noqa: E402


class ScreeningPathGuardTests(unittest.TestCase):
    def test_existing_v5_outputs_fail_before_retrieval(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            paths = (base / "screened.csv", base / "eligible.csv", base / "summary.md")
            protect_existing_outputs(*paths)
            paths[2].write_text("prior run")
            with self.assertRaises(FileExistsError):
                protect_existing_outputs(*paths)
            with self.assertRaises(ValueError):
                protect_existing_outputs(paths[0], paths[0], paths[2])

    def test_rejects_legacy_outputs_and_cache_for_offline_runs(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            outputs = (base / "screened.csv", base / "eligible.csv", base / "summary.md")
            source = base / "source.csv"
            new_cache = base / "cache"
            protect_legacy_paths(*outputs, new_cache / "evidence", new_cache, source)
            with self.assertRaises(ValueError):
                protect_legacy_paths(ROOT / "cases/manifests/screened_cases.csv",
                                     outputs[1], outputs[2], new_cache / "evidence",
                                     new_cache, source)
            with self.assertRaises(ValueError):
                protect_legacy_paths(*outputs,
                                     ROOT / "data/intermediate/screening/cache/evidence",
                                     new_cache, source)
            with self.assertRaises(ValueError):
                protect_legacy_paths(*outputs, new_cache / "evidence",
                                     ROOT / "data/intermediate/screening/cache", source)
            with self.assertRaises(ValueError):
                protect_legacy_paths(source, outputs[1], outputs[2],
                                     new_cache / "evidence", new_cache, source)


if __name__ == "__main__":
    unittest.main()
