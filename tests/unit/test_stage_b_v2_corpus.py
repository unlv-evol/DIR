"""Corpus migration report invariants without materializing research outputs."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from developer_intent.stage_b_v2_corpus import validate_report  # noqa: E402


class StageBV2CorpusTests(unittest.TestCase):
    def report(self):
        return {"report_version": "stage-b-v1-v2-migration-report-v1",
                "implementation_commit": "092d30027b31c19b4b6a5bacbceab174a4025af6",
                "corpus": {"case_count": 122, "valid_v2_files": 122},
                "legacy_mapping": {"total_v1_candidates": 290,
                                   "exact_legacy_mappings": 290,
                                   "v1_candidate_missing": 0},
                "case_records": [{} for _ in range(122)],
                "representation_impact_counts": {"candidate_universe_unchanged": 122}}

    def test_valid_report(self):
        validate_report(self.report())

    def test_report_fails_closed_on_mapping_or_population(self):
        for field, value in (("valid_v2_files", 121), ("case_count", 121)):
            report = self.report(); report["corpus"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_report(report)
        report = self.report(); report["legacy_mapping"]["exact_legacy_mappings"] = 289
        with self.assertRaises(ValueError):
            validate_report(report)


if __name__ == "__main__":
    unittest.main()
