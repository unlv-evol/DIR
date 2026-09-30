"""Verified source-linkage correction overlay tests."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from developer_intent.screening import case_id  # noqa: E402
from developer_intent.source_corrections import (  # noqa: E402
    CORRECTION_SCHEMA_VERSION, apply_source_corrections)


class SourceCorrectionTests(unittest.TestCase):
    def test_verified_overlay_preserves_source_and_case_identity(self):
        source = {"Case ID": "PA-1", "Outcome_Class": "PA",
                  "PR_Link": "https://github.com/acme/repo/pull/1",
                  "Conversation_Link": "https://chatgpt.com/share/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"}
        correction = {
            "schema_version": CORRECTION_SCHEMA_VERSION,
            "case_id": case_id("PA-1"), "source_case_id": "PA-1",
            "pr_url": source["PR_Link"],
            "original_conversation_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "original_conversation_url": source["Conversation_Link"],
            "corrected_conversation_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "corrected_conversation_url": "https://chatgpt.com/share/bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "reason": "Verified source index correction", "status": "verified",
            "reviewer": "reviewer-1", "timestamp": "2026-09-29T00:00:00Z",
            "version": "correction-v1", "evidence_ref": "packet#sha256=abc",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / f"{correction['case_id']}.json"
            path.write_text(json.dumps(correction))
            corrected = apply_source_corrections([source], Path(directory))
        self.assertEqual(source["Conversation_Link"],
                         "https://chatgpt.com/share/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        self.assertEqual(corrected[0]["Conversation_Link"],
                         correction["corrected_conversation_url"])
        self.assertEqual(case_id(corrected[0]["Case ID"]), correction["case_id"])

    def test_unverified_or_identity_mismatched_correction_fails(self):
        source = {"Case ID": "PA-1", "Outcome_Class": "PA",
                  "PR_Link": "https://github.com/acme/repo/pull/1",
                  "Conversation_Link": "https://chatgpt.com/share/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"}
        correction = {
            "schema_version": CORRECTION_SCHEMA_VERSION,
            "case_id": case_id("PA-1"), "source_case_id": "PA-1", "pr_url": source["PR_Link"],
            "original_conversation_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "original_conversation_url": source["Conversation_Link"],
            "corrected_conversation_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "corrected_conversation_url": "https://chatgpt.com/share/cccccccc-cccc-cccc-cccc-cccccccccccc",
            "reason": "Mismatch", "status": "verified", "reviewer": "reviewer-1",
            "timestamp": "2026-09-29T00:00:00Z", "version": "correction-v1",
            "evidence_ref": "packet#sha256=abc",
        }
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, f"{correction['case_id']}.json").write_text(json.dumps(correction))
            with self.assertRaisesRegex(ValueError, "identity is invalid"):
                apply_source_corrections([source], Path(directory))


if __name__ == "__main__":
    unittest.main()
