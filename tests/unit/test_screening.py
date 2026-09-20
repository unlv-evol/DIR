import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from developer_intent.screening import case_id, screen_rows  # noqa: E402


def source(sid="PA-1", outcome="PA", pr="https://github.com/acme/repo/pull/1",
           conv="https://chatgpt.com/share/b7853f70-84b8-477b-9879-a93a51215f81"):
    return {"Case ID": sid, "Outcome_Class": outcome, "PR_Link": pr,
            "Conversation_Link": conv, "Context": "1", "Specificity": "2",
            "Verification": "0", "PR_Size": "999999", "Adopt_Any": "1",
            "Fraction_Adopted": "100", "Status": "merged"}


def evidence(files=10, lines=300, prompts=10, words=100, commits=11):
    return {
        "pr": {"html_url": "https://github.com/acme/repo/pull/1", "number": 1},
        "files": [{"filename": f"f{i}", "additions": lines if i == 0 else 0,
                   "deletions": 0} for i in range(files)],
        "commits": [{"sha": str(i)} for i in range(commits)],
        "conversation": {
            "url": "https://chatgpt.com/share/b7853f70-84b8-477b-9879-a93a51215f81",
            "start": "2024-01-01", "precision": "date", "complete": True,
            "turns": ([{"role": "user", "text": "word"} for _ in range(prompts)] +
                      [{"role": "assistant", "text": " ".join(["word"] * (words - prompts))}]),
        },
    }


class ScreeningTests(unittest.TestCase):
    def run_with_evidence(self, row=None, facts=None):
        row = row or source()
        facts = facts or evidence()
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, f"{row['Case ID']}.json").write_text(json.dumps(facts))
            return screen_rows([row], Path(directory))[0]

    def test_pa_pn_only_and_stable_ids(self):
        rows = [source("PA-1"), source("PN-1", "PN"), source("NE-1", "NE")]
        first = screen_rows(rows)
        second = screen_rows(list(reversed(rows)))
        self.assertEqual(len(first), 2)
        self.assertEqual({r["case_id"] for r in first}, {r["case_id"] for r in second})
        self.assertEqual(case_id("PA-1"), first[0]["case_id"])

    def test_boundaries_and_commit_preference(self):
        row = self.run_with_evidence()
        self.assertEqual(row["changed_files"], 10)
        self.assertEqual(row["changed_lines"], 300)
        self.assertEqual(row["developer_prompts"], 10)
        self.assertEqual(row["conversation_words"], 100)
        self.assertEqual(row["passes_changed_lines"], "true")
        self.assertEqual(row["commits_preferred"], "false")
        self.assertEqual(row["screening_eligible"], "true")
        self.assertEqual(row["scientific_data_eligible"], "true")
        self.assertEqual(row["pilot_manageability_eligible"], "true")

    def test_pr_size_and_downstream_outcomes_ignored(self):
        a = source()
        b = dict(a, PR_Size="0", Adopt_Any="0", Fraction_Adopted="0", Status="closed")
        self.assertEqual(self.run_with_evidence(a), self.run_with_evidence(b))

    def test_multiple_failures_and_missing(self):
        row = self.run_with_evidence(facts=evidence(files=11, lines=301, prompts=11))
        self.assertEqual(row["screening_eligible"], "false")
        self.assertIn("changed_files_limit", row["exclusion_reason"])
        self.assertIn("changed_lines_limit", row["exclusion_reason"])
        self.assertIn("prompt_count_limit", row["exclusion_reason"])
        self.assertIn("pilot_manageability_exclusion", row["exclusion_reason"])
        self.assertEqual(row["scientific_data_eligible"], "true")
        self.assertEqual(row["pilot_manageability_eligible"], "false")
        missing = screen_rows([source()])[0]
        self.assertEqual(missing["passes_changed_files"], "")
        self.assertEqual(missing["data_completeness_status"], "incomplete")
        self.assertEqual(missing["case_integrity_status"], "unresolved")
        self.assertEqual(missing["scientific_data_eligible"], "false")
        self.assertEqual(missing["pilot_manageability_eligible"], "")

    def test_conversation_word_boundary_and_temporal_precision(self):
        at_limit = self.run_with_evidence(facts=evidence(words=8000))
        over_limit = self.run_with_evidence(facts=evidence(words=8001))
        self.assertEqual(at_limit["passes_conversation_length"], "true")
        self.assertEqual(over_limit["passes_conversation_length"], "false")
        invalid = evidence()
        invalid["conversation"]["start"] = "2024-01-01T12:00:00"
        invalid["conversation"]["precision"] = "timestamp"
        row = self.run_with_evidence(facts=invalid)
        self.assertIn("missing_conversation_start", row["exclusion_reason"])

    def test_duplicates_and_conflict(self):
        duplicate = screen_rows([source(), source("PN-1", "PN")])[1]
        self.assertEqual(duplicate["case_integrity_status"], "duplicate")
        self.assertEqual(duplicate["duplicate_of"], case_id("PA-1"))
        facts = evidence()
        facts["conversation"]["url"] = "https://chatgpt.com/share/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        mismatch = self.run_with_evidence(facts=facts)
        self.assertEqual(mismatch["case_integrity_status"], "conflict")
        self.assertEqual(mismatch["screening_eligible"], "false")

    def test_incomplete_conversation_never_passes(self):
        facts = evidence()
        facts["conversation"]["complete"] = False
        row = self.run_with_evidence(facts=facts)
        self.assertEqual(row["conversation_words"], None)
        self.assertEqual(row["screening_eligible"], "false")

    def test_verified_pr_alias_preserves_both_urls(self):
        facts = evidence()
        canonical = "https://github.com/new-owner/new-repo/pull/1"
        facts["pr"].update(html_url=canonical, canonical_url=canonical,
                           source_url=source()["PR_Link"], redirect_verified=True,
                           repository_id=123,
                           api_final_url="https://api.github.com/repositories/123/pulls/1")
        row = self.run_with_evidence(facts=facts)
        self.assertEqual(row["case_integrity_status"], "ok")
        self.assertEqual(row["pr_url"], source()["PR_Link"])
        self.assertEqual(row["canonical_pr_url"], canonical)
        self.assertEqual(row["pr_redirect_verified"], "true")
        facts["pr"]["repository_id"] = 999
        self.assertEqual(self.run_with_evidence(facts=facts)["case_integrity_status"], "conflict")


if __name__ == "__main__":
    unittest.main()
