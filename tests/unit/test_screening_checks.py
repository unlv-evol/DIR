"""Offline administrative linkage and history-access checks."""

import sys
import unittest
from pathlib import Path
from subprocess import CompletedProcess, TimeoutExpired

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from developer_intent.screening import case_id, screen_rows  # noqa: E402
from developer_intent.screening_checks import correspondence, history_access  # noqa: E402

PR = "https://github.com/acme/repo/pull/1"
SHARE = "https://chatgpt.com/share/b7853f70-84b8-477b-9879-a93a51215f81"
SOURCE = {"Case ID": "PA-1", "PR_Link": PR, "Conversation_Link": SHARE,
          "Outcome_Class": "PA", "Context": "0", "Specificity": "0", "Verification": "0"}


def review(judgment="yes", **changes):
    record = {"case_id": case_id("PA-1"), "pr_url": PR, "conversation_url": SHARE,
              "judgment": judgment, "source": "independent_administrative_review",
              "reviewer": "reviewer-1", "timestamp": "2026-09-21T00:00:00Z",
              "version": "review-v1", "evidence_ref": "source-ledger:123",
              "rationale": "task correspondence checked independently"}
    return {**record, **changes}


def facts():
    return {"pr": {"html_url": PR, "number": 1, "base_sha": "a" * 40},
            "conversation": {"url": SHARE, "start": "2024-01-01",
                             "precision": "date", "complete": True,
                             "turns": [{"role": "user", "text": "task"}]}}


class CorrespondenceTests(unittest.TestCase):
    def test_pair_and_outcome_alone_are_unresolved(self):
        self.assertEqual(correspondence(facts(), SOURCE, case_id("PA-1"))["judgment"],
                         "unresolved")
        self.assertEqual(correspondence(facts(), {**SOURCE, "Outcome_Class": "PN"},
                                        case_id("PA-1"))["judgment"], "unresolved")

    def test_stage_a_correspondence_controls_scientific_disposition(self):
        for judgment, status, readiness in (("yes", "pending_resolution", "blocked"),
                                            ("no", "excluded", "blocked"),
                                            ("unresolved", "pending_resolution", "blocked")):
            item = facts()
            item["correspondence_review"] = review(judgment)
            with self.subTest(judgment=judgment):
                from tempfile import TemporaryDirectory
                import json
                with TemporaryDirectory() as directory:
                    Path(directory, "PA-1.json").write_text(json.dumps(item))
                    row = screen_rows([SOURCE], Path(directory))[0]
                self.assertEqual(row["pr_conversation_match"], judgment)
                self.assertEqual(row["eligibility_status"], status)
                self.assertEqual(row["stage_b_readiness_status"], readiness)
                self.assertEqual(row["case_integrity_status"], "ok")
                if judgment == "no":
                    self.assertIn("pr_conversation_match_failed", row["exclusion_reason"])
                elif judgment == "unresolved":
                    self.assertIn("pr_conversation_match_unresolved", row["pending_reason"])

    def test_unsupported_or_wrong_identity_cannot_be_positive(self):
        for changed in ({"source": "source_index_pair_only"},
                        {"source": "text_similarity_only"},
                        {"source": "final_diff"},
                        {"source": "integrated_implementation"},
                        {"conversation_url": "https://chatgpt.com/share/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"}):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                correspondence({"correspondence_review": review(**changed)},
                               SOURCE, case_id("PA-1"))


class HistoryTests(unittest.TestCase):
    def probe(self, failure=None):
        calls = []
        def run(args, **kwargs):
            calls.append(args)
            if failure == "timeout" and "fetch" in args:
                raise TimeoutExpired(args, 90)
            if "fetch" in args:
                return CompletedProcess(args, 1 if failure else 0, b"",
                                        (failure or "").encode())
            if "cat-file" in args:
                return CompletedProcess(args, 0, b"commit\n", b"")
            return CompletedProcess(args, 0, b"", b"")
        result = history_access({"html_url": PR, "base_sha": "a" * 40}, PR, run=run)
        return result, calls

    def test_known_commit_retrieved(self):
        result, calls = self.probe()
        self.assertEqual(result["judgment"], "yes")
        self.assertEqual(result["status"], "commit_object_retrieved")
        self.assertTrue(any("cat-file" in args for args in calls))
        self.assertFalse(any("show" in args or "diff" in args for args in calls))

    def test_demonstrated_inaccessible_and_inconclusive(self):
        self.assertEqual(self.probe("fatal: repository not found")[0]["judgment"], "no")
        network = self.probe("temporary network error")[0]
        self.assertEqual(network["judgment"], "unresolved")
        self.assertEqual(network["status"], "fetch_failed")
        timeout = self.probe("timeout")[0]
        self.assertEqual(timeout["judgment"], "unresolved")
        self.assertEqual(timeout["status"], "fetch_timeout")
        self.assertEqual(timeout["reason"], "commit_fetch_timed_out")

    def test_pr_api_and_history_access_do_not_prove_historical_state(self):
        self.assertEqual(history_access({"html_url": PR}, PR)["judgment"], "unresolved")
        item = facts()
        item["pr_retrieval_status"] = "retrieved_authenticated"
        item["history_access"] = self.probe()[0]
        from tempfile import TemporaryDirectory
        import json
        with TemporaryDirectory() as directory:
            Path(directory, "PA-1.json").write_text(json.dumps(item))
            row = screen_rows([SOURCE], Path(directory))[0]
        self.assertEqual(row["project_history_accessible"], "yes")
        self.assertEqual(row["historical_state_reconstructible"], "unresolved")
        self.assertEqual(row["eligibility_status"], "pending_resolution")


if __name__ == "__main__":
    unittest.main()
