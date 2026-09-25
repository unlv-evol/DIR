"""Restricted case mapping stays deterministic and outside Stage C input."""

import csv
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from developer_intent.case_mapping import (MAPPING_FIELDS, MAPPING_SCHEMA_VERSION,  # noqa: E402
                                           case_mapping_rows, write_case_mapping)
from developer_intent.conversation_package import PACKAGE_KEYS  # noqa: E402
from developer_intent.screening import FIELDS, SCREENING_SCHEMA_VERSION, screen_rows  # noqa: E402


def source(case, outcome, pr, share):
    return {"Case ID": case, "Outcome_Class": outcome, "PR_Link": pr,
            "Conversation_Link": share, "Context": "1", "Specificity": "0",
            "Verification": "2"}


class CaseMappingTests(unittest.TestCase):
    def setUp(self):
        self.source = [
            source("PA-1", "PA", "https://github.com/acme/repo/pull/1",
                   "https://chatgpt.com/share/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            source("PN-1", "PN", "https://github.com/acme/repo/pull/2",
                   "https://chatgpt.com/share/bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
        ]

    def test_word_required_fields_and_complementary_fields_remain(self):
        required = {"case_id", "pr_url", "conversation_url", "Outcome_Class",
                    "conversation_available", "temporal_anchor_available",
                    "first_generation_boundary_identifiable", "pr_conversation_match",
                    "duplicate_status", "project_history_accessible", "eligible",
                    "eligibility_status", "exclusion_reason"}
        complementary = {"screening_schema_version", "methodology_version", "source_case_id",
                         "temporal_precision", "conversation_temporal_status",
                         "conversation_retrieval_status", "conversation_parsing_status",
                         "pending_reason", "processability_source", "changed_files",
                         "pr_commits", "stage_b_readiness_status", "stage_b_readiness_reason"}
        self.assertTrue(required <= set(FIELDS))
        self.assertTrue(complementary <= set(FIELDS))
        self.assertEqual(SCREENING_SCHEMA_VERSION, "dir-screening-v9")

    def test_mapping_is_deterministic_restricted_and_source_checked(self):
        screened = screen_rows(self.source)
        first = case_mapping_rows(self.source, screened)
        second = case_mapping_rows(list(reversed(self.source)), list(reversed(screened)))
        self.assertEqual(first, second)
        self.assertEqual(len(first), 2)
        self.assertEqual(set(first[0]), set(MAPPING_FIELDS))
        self.assertEqual(first[0]["mapping_schema_version"], MAPPING_SCHEMA_VERSION)
        self.assertTrue({"case_id", "pr_url", "Outcome_Class"} <= set(first[0]))
        self.assertFalse({"pr_url", "Outcome_Class", "source_case_id", "conversation_url"}
                         & PACKAGE_KEYS)
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "case_mapping.csv"
            write_case_mapping(first, target)
            with target.open(newline="", encoding="utf-8") as stream:
                self.assertEqual(list(csv.DictReader(stream)), first)
            with self.assertRaises(FileExistsError):
                write_case_mapping(first, target)
        with self.assertRaisesRegex(ValueError, "differs"):
            case_mapping_rows(self.source, [{**screened[0], "pr_url": "https://github.com/wrong/repo/pull/1"}])
        with self.assertRaisesRegex(ValueError, "differs"):
            case_mapping_rows(self.source, [{**screened[0], "conversation_id": "wrong"}])

    def test_stage_g_protocol_does_not_promote_analytic_field_to_gate(self):
        protocol = (ROOT / "protocols/experiment_protocol.md").read_text(encoding="utf-8")
        self.assertIn("two complementary activities within one stage", protocol)
        self.assertIn("Stage D", protocol)
        self.assertIn("approximately 30% PA/PN-stratified validation sample", protocol)
        self.assertNotIn("Stage D separately requires semantic PR/conversation", protocol)
        self.assertIn("candidate additional evidence must concern the target programming task", protocol)
        self.assertIn("add information beyond the frozen conversation", protocol)
        self.assertIn("contribute Context, Specificity, Verification", protocol)
        self.assertIn("Temporal availability by `tFG` is a separate mandatory", protocol)
        self.assertIn("neither is an extra eligibility gate", protocol)


if __name__ == "__main__":
    unittest.main()
