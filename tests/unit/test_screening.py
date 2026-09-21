"""Protocol v5 Stage A eligibility and legacy-output separation tests."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from developer_intent.screening import (  # noqa: E402
    METHODOLOGY_VERSION, SCREENING_SCHEMA_VERSION, case_id, screen_rows,
    screening_summary, write_manifest,
)


def source(sid="PA-1", outcome="PA", pr="https://github.com/acme/repo/pull/1",
           conv="https://chatgpt.com/share/b7853f70-84b8-477b-9879-a93a51215f81"):
    return {"Case ID": sid, "Outcome_Class": outcome, "PR_Link": pr,
            "Conversation_Link": conv, "Context": "1", "Specificity": "2",
            "Verification": "0", "PR_Size": "999999", "Adopt_Any": "1",
            "Fraction_Adopted": "100", "Status": "merged"}


def evidence(files=10, lines=300, prompts=10, words=100, commits=11,
             reviewed=True):
    facts = {
        "pr": {"html_url": "https://github.com/acme/repo/pull/1", "number": 1,
               "commits": commits},
        "files": [{"filename": f"f{i}", "additions": lines if i == 0 else 0,
                   "deletions": 0} for i in range(files)],
        "conversation": {
            "url": "https://chatgpt.com/share/b7853f70-84b8-477b-9879-a93a51215f81",
            "start": "2024-01-01", "precision": "date", "complete": True,
            "turns": ([{"role": "user", "text": "word"} for _ in range(prompts)] +
                      [{"role": "assistant", "text": " ".join(["word"] * (words - prompts))}]),
        },
    }
    if reviewed:
        facts["processability"] = {
            "source": "independent fixture review",
            "conversation_available": "yes",
            "first_generation_boundary_identifiable": "yes",
            "pr_conversation_match": "yes",
            "project_history_accessible": "yes",
            "historical_state_reconstructible": "yes",
        }
    return facts


class ScreeningTests(unittest.TestCase):
    def run_with_evidence(self, row=None, facts=None):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "PA-1.json").write_text(json.dumps(facts or evidence()))
            return screen_rows([row or source()], Path(directory))[0]

    def test_population_and_stable_ids(self):
        rows = [source("PA-1"), source("PN-1", "PN"), source("NE-1", "NE"),
                source("CL-1", "CL")]
        first = screen_rows(rows)
        second = screen_rows(list(reversed(rows)))
        self.assertEqual(len(first), 2)
        self.assertEqual({r["case_id"] for r in first}, {r["case_id"] for r in second})
        self.assertEqual(case_id("PA-1"), first[0]["case_id"])

    def test_large_measures_are_descriptive_only(self):
        row = self.run_with_evidence(facts=evidence(files=11, lines=301, prompts=11,
                                                    words=8001, commits=12))
        self.assertEqual(row["changed_files"], 11)
        self.assertEqual(row["changed_lines"], 301)
        self.assertEqual(row["developer_prompts"], 11)
        self.assertEqual(row["conversation_words"], 8001)
        self.assertEqual(row["pr_commits"], 12)
        self.assertEqual(row["eligible"], "true")
        self.assertEqual(row["exclusion_reason"], "")
        self.assertNotIn("pilot_manageability_eligible", row)

    def test_outcome_and_pr_size_do_not_change_eligibility(self):
        a = source()
        b = dict(a, PR_Size="0", Adopt_Any="0", Fraction_Adopted="0", Status="closed")
        self.assertEqual(self.run_with_evidence(a), self.run_with_evidence(b))

    def test_unreviewed_processability_is_pending_not_excluded(self):
        row = self.run_with_evidence(facts=evidence(reviewed=False))
        self.assertEqual(row["eligibility_status"], "pending_resolution")
        self.assertEqual(row["eligible"], "")
        self.assertIn("first_generation_boundary_identifiable_unresolved", row["pending_reason"])
        self.assertIn("historical_state_reconstructible_unresolved", row["pending_reason"])
        self.assertEqual(row["exclusion_reason"], "")

    def test_concrete_integrity_temporal_and_history_failures(self):
        mismatch = evidence()
        mismatch["conversation"]["url"] = "https://chatgpt.com/share/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        self.assertIn("source_identity_conflict", self.run_with_evidence(facts=mismatch)["exclusion_reason"])
        no_time = evidence()
        no_time["conversation"]["start"] = ""
        self.assertIn("unusable_temporal_anchor", self.run_with_evidence(facts=no_time)["exclusion_reason"])
        no_history = evidence()
        no_history["processability"]["project_history_accessible"] = "no"
        self.assertIn("project_history_accessible_failed",
                      self.run_with_evidence(facts=no_history)["exclusion_reason"])
        duplicate = screen_rows([source(), source("PN-1", "PN")])[1]
        self.assertEqual(duplicate["duplicate_status"], "duplicate")
        self.assertEqual(duplicate["eligibility_status"], "excluded")

    def test_unrecoverable_conversation_and_boundary_failure(self):
        facts = evidence()
        facts["conversation"]["complete"] = False
        facts["processability"]["conversation_available"] = "no"
        row = self.run_with_evidence(facts=facts)
        self.assertIn("conversation_available_failed", row["exclusion_reason"])
        facts = evidence()
        facts["processability"]["first_generation_boundary_identifiable"] = "no"
        row = self.run_with_evidence(facts=facts)
        self.assertIn("first_generation_boundary_identifiable_failed", row["exclusion_reason"])

    def test_positive_review_does_not_replace_incomplete_conversation(self):
        facts = evidence()
        facts["conversation"]["complete"] = False
        row = self.run_with_evidence(facts=facts)
        self.assertEqual(row["conversation_available"], "unresolved")
        self.assertEqual(row["eligibility_status"], "pending_resolution")
        self.assertNotEqual(row["eligible"], "true")

    def test_date_precision_and_distinct_new_output_version(self):
        row = self.run_with_evidence()
        self.assertEqual(row["temporal_precision"], "date")
        self.assertEqual(row["methodology_version"], METHODOLOGY_VERSION)
        self.assertEqual(row["screening_schema_version"], SCREENING_SCHEMA_VERSION)
        self.assertNotIn("first_generation_cutoff", row)
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory, "stage_a.csv")
            write_manifest([row], target)
            self.assertIn("dir-screening-v4", target.read_text())
        summary = screening_summary([source()], [row])
        self.assertIn("| PA | 1 | 1 | 0 | 0 |", summary)

    def test_verified_pr_alias(self):
        facts = evidence()
        canonical = "https://github.com/new-owner/new-repo/pull/1"
        facts["pr"].update(html_url=canonical, canonical_url=canonical,
                           source_url=source()["PR_Link"], redirect_verified=True,
                           repository_id=123,
                           api_final_url="https://api.github.com/repositories/123/pulls/1")
        row = self.run_with_evidence(facts=facts)
        self.assertEqual(row["case_integrity_status"], "ok")
        self.assertEqual(row["canonical_pr_url"], canonical)


if __name__ == "__main__":
    unittest.main()
