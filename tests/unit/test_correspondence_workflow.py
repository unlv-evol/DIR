"""Offline Stage A manual correspondence CSV workflow tests."""

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from developer_intent.correspondence_workflow import (  # noqa: E402
    MANUAL_FIELDS, REVIEW_CSV_FIELDS, import_review_csv, review_rows, write_review_csv)
from developer_intent.screening import case_id, screen_rows  # noqa: E402
from developer_intent.stage_a_contracts import validate_correspondence_review  # noqa: E402

PR = "https://github.com/acme/repo/pull/1"
SHARE = "https://chatgpt.com/share/b7853f70-84b8-477b-9879-a93a51215f81"


def source(outcome="PA"):
    return {"Case ID": "PA-1", "Outcome_Class": outcome, "PR_Link": PR,
            "Conversation_Link": SHARE, "Context": "1", "Specificity": "2",
            "Verification": "0"}


def evidence(review=None):
    facts = {
        "pr": {"html_url": PR, "number": 1, "base_sha": "a" * 40},
        "files": [],
        "conversation": {"url": SHARE, "start": "2024-01-01", "precision": "date",
                         "complete": True, "turns": [{"role": "user", "text": "task"}]},
        "history_access": {"judgment": "yes", "mechanism": "git_fetch_commit_object",
                           "repository": "acme/repo", "object": "a" * 40,
                           "status": "commit_object_retrieved", "source": "PR base_sha",
                           "reason": ""},
        "processability": {"source": "synthetic fixture", "conversation_available": "yes",
                           "first_generation_boundary_identifiable": "yes",
                           "project_history_accessible": "yes",
                           "historical_state_reconstructible": "yes"},
    }
    if review:
        facts["correspondence_review"] = review
    return facts


def completed(row, judgment="yes"):
    result = dict(row)
    values = {
        "pr_conversation_match": judgment,
        "pr_conversation_match_source": "restricted_stage_a_manual_review",
        "pr_conversation_match_reviewer": "reviewer-1",
        "pr_conversation_match_timestamp": "2026-09-22T00:00:00Z",
        "pr_conversation_match_version": "review-v1",
        "pr_conversation_match_evidence_ref": result["permitted_evidence_ref"],
        "pr_conversation_match_reason": "synthetic same-task judgment",
    }
    result.update(values)
    return result


class CorrespondenceWorkflowTests(unittest.TestCase):
    def automated(self, directory):
        Path(directory, "PA-1.json").write_text(json.dumps(evidence()))
        return screen_rows([source()], Path(directory))

    def write_rows(self, path, rows):
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=REVIEW_CSV_FIELDS,
                                    lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)

    def test_export_is_restricted_deterministic_and_blank(self):
        with tempfile.TemporaryDirectory() as directory:
            rows = review_rows(self.automated(directory))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["case_id"], case_id("PA-1"))
            self.assertEqual(rows[0]["source_linkage_status"], "established")
            self.assertTrue(all(rows[0][field] == "" for field in MANUAL_FIELDS))
            prohibited = {"Outcome_Class", "source_case_id", "C_score", "S_score", "V_score", "final_diff",
                          "integrated_implementation", "conversation_text", "pr_title", "pr_body"}
            self.assertFalse(prohibited & set(REVIEW_CSV_FIELDS))
            path = Path(directory, "review.csv")
            write_review_csv(rows, path)
            write_review_csv(rows, path)
            with path.open(newline="", encoding="utf-8") as stream:
                self.assertEqual(next(csv.DictReader(stream)), rows[0])

    def test_import_yes_no_unresolved_and_final_disposition(self):
        for judgment, expected in (("yes", "eligible"), ("no", "excluded"),
                                   ("unresolved", "pending_resolution")):
            with self.subTest(judgment=judgment), tempfile.TemporaryDirectory() as directory:
                screened = self.automated(directory)
                row = completed(review_rows(screened)[0], judgment)
                csv_path = Path(directory, "review.csv")
                self.write_rows(csv_path, [row])
                review_dir = Path(directory, "reviews")
                counts = import_review_csv(csv_path, screened, [source()], review_dir)
                self.assertEqual(counts["imported"], 1)
                canonical = json.loads((review_dir / f"{case_id('PA-1')}.json").read_text())
                self.assertEqual(validate_correspondence_review(canonical, source())["judgment"],
                                 judgment)
                Path(directory, "PA-1.json").write_text(json.dumps(evidence(canonical)))
                final = screen_rows([source()], Path(directory))[0]
                self.assertEqual(final["eligibility_status"], expected)
                self.assertEqual(final["stage_b_readiness_status"],
                                 "ready_for_stage_b" if expected == "eligible" else "blocked")
                self.assertEqual(import_review_csv(csv_path, screened, [source()], review_dir),
                                 {"imported": 0, "unchanged": 1, "skipped_blank": 0})

    def test_blank_is_skipped_and_invalid_or_mismatched_rows_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            screened = self.automated(directory)
            base = review_rows(screened)[0]
            path = Path(directory, "review.csv")
            self.write_rows(path, [base])
            result = import_review_csv(path, screened, [source()], Path(directory, "reviews"))
            self.assertEqual(result["skipped_blank"], 1)
            self.assertFalse(any(Path(directory, "reviews").glob("*.json")))
            for changed in ({"pr_conversation_match": "maybe"},
                            {"case_id": "CASE_000000000000"},
                            {"pr_url": "https://github.com/wrong/repo/pull/1"}):
                self.write_rows(path, [{**completed(base), **changed}])
                with self.assertRaises(ValueError):
                    import_review_csv(path, screened, [source()], Path(directory, "reviews"))

    def test_duplicate_rows_and_provenance_omission_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            screened = self.automated(directory)
            row = completed(review_rows(screened)[0])
            path = Path(directory, "review.csv")
            self.write_rows(path, [row, row])
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                import_review_csv(path, screened, [source()], Path(directory, "reviews"))
            row["pr_conversation_match_reviewer"] = ""
            self.write_rows(path, [row])
            with self.assertRaisesRegex(ValueError, "provenance"):
                import_review_csv(path, screened, [source()], Path(directory, "reviews"))


if __name__ == "__main__":
    unittest.main()
