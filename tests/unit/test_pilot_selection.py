import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from developer_intent.pilot_selection import (  # noqa: E402
    SELECTION_FIELDS, pilot_selection_summary, read_pilot_manifest,
    validate_pilot_manifest,
)
from developer_intent.screening_secondary import SECONDARY_FIELDS  # noqa: E402


def rows():
    screened = []
    selected = []
    for case_id, eligible, score in (("A", "true", "0"), ("B", "true", "2"),
                                     ("C", "false", "1")):
        source = {"case_id": case_id, "source_case_id": case_id,
                  "screening_eligible": eligible, "C_score": score,
                  "S_score": "1", "V_score": "0", "developer_prompts": "1",
                  "changed_files": "2", "changed_lines": "20", "conversation_words": "100",
                  "pr_commits": "3", "Outcome_Class": "PA"}
        source.update({field: "not_assessed" for field in SECONDARY_FIELDS})
        source["conversation_turn_pattern"] = "single_developer_prompt"
        source["prompt_url_signal"] = "not_detected_by_rule"
        screened.append(source)
        if eligible == "true":
            selected.append({key: source[key] for key in SELECTION_FIELDS if key in source})
            selected[-1].update(study_role="pilot_development",
                                selection_characteristics="single developer prompt",
                                selection_rationale="observed prompt and C/S/V variation")
    return screened, selected


class PilotSelectionTests(unittest.TestCase):
    def test_validated_summary_and_outcome_independence(self):
        screened, selected = rows()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "pilot.csv")
            with path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=SELECTION_FIELDS)
                writer.writeheader()
                writer.writerows(selected)
            self.assertEqual(read_pilot_manifest(path), selected)
            summary = pilot_selection_summary(screened, selected, path)
            self.assertIn("Selected pilot/development cases: 2 of 2", summary)
            screened[0]["Outcome_Class"] = "PN"
            self.assertEqual(summary, pilot_selection_summary(screened, selected, path))

    def test_rejects_ineligible_duplicate_and_stale_selection(self):
        screened, selected = rows()
        invalid = dict(selected[0], case_id="C", source_case_id="C")
        with self.assertRaisesRegex(ValueError, "not confirmed eligible"):
            validate_pilot_manifest(screened, [invalid])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            validate_pilot_manifest(screened, [selected[0], selected[0]])
        invalid = dict(selected[0], changed_lines="19")
        with self.assertRaisesRegex(ValueError, "stale changed_lines"):
            validate_pilot_manifest(screened, [invalid])
        invalid = dict(selected[0], prompt_url_signal="detected")
        with self.assertRaisesRegex(ValueError, "stale prompt_url_signal"):
            validate_pilot_manifest(screened, [invalid])

    def test_in_memory_numeric_screening_measures_match_csv_values(self):
        screened, selected = rows()
        for field in ("developer_prompts", "changed_files", "changed_lines",
                      "conversation_words", "pr_commits"):
            for row in screened:
                row[field] = int(row[field])
        validate_pilot_manifest(screened, selected)


if __name__ == "__main__":
    unittest.main()
