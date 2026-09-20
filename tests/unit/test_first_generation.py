"""Offline first-generation and temporal-boundary regression tests."""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from developer_intent.first_generation import draft_record, freeze_record
from developer_intent.screening_chatgpt import parse_share
from developer_intent.temporal_evidence import (availability, case_evidence_conclusion,
                                                evidence_record, partition_record)


def conversation(first_time=1704067200, response_time=1704153600):
    messages = [
        {"role": "user", "create_time": first_time, "content": {"parts": ["initial context"]}},
        {"role": "assistant", "content": {"parts": ["acknowledged"]}},
        {"role": "user", "content": {"parts": ["implement feature"]}},
        {"role": "assistant", "recipient": "browser", "content": {"content_type": "code", "text": "search"}},
        {"role": "tool", "content": {"content_type": "result", "text": "result"}},
        {"role": "assistant", "create_time": response_time, "content": {"parts": ["generated artifact"]}},
        {"role": "user", "content": {"parts": ["later request"]}},
    ]
    return parse_share(json.dumps({"messages": messages}).encode())


def artifact():
    return [{"artifact_id": "A1", "family_id": "F1", "response_event_index": 5,
             "generation_order": 1}]


def validated(record):
    item_ids = [item["item_id"] for field in ("context_supplied", "specificity_supplied",
                                              "verification_supplied") for item in record[field]]
    checks = [{"item_id": item_id, "supported": True,
               "category_assignment_correct": True, "provenance_correct": True,
               "future_information_leakage": False} for item_id in item_ids]
    judgment = {"validator_id": "reviewer-1", "boundary_correct": True, "target_prompt_correct": True,
                "item_supported": True, "category_assignment_correct": True,
                "provenance_correct": True, "future_information_leakage": False,
                "items": checks}
    return freeze_record(record, [judgment, dict(judgment, validator_id="reviewer-2")])


class FirstGenerationTests(unittest.TestCase):
    def test_family_target_prior_turns_and_supplied_provenance(self):
        parsed = conversation()
        item = {"item_id": "C1", "category": "Context", "text": "initial context",
                "source_turn_id": "turn_000000"}
        draft = draft_record("CASE_X", parsed, artifact(), [item])
        self.assertEqual(draft["first_snippet_family_id"], "F1")
        self.assertEqual(draft["first_generation_response_id"], "turn_000005")
        self.assertEqual(draft["target_prompt_id"], "turn_000002")
        self.assertEqual(draft["allowed_prior_turn_ids"], ["turn_000000", "turn_000001"])
        self.assertEqual(draft["context_supplied"], [item])
        self.assertEqual(draft["first_generation_cutoff"]["value"], "2024-01-02T00:00:00+00:00")
        self.assertEqual(draft["conversation_start_time"]["value"], "2024-01-01T00:00:00+00:00")
        self.assertEqual(len(parsed["tool_trace"]), 2)
        with self.assertRaises(ValueError):
            draft_record("CASE_X", parsed, artifact(), [{"item_id": "C1", "category": "Context", "text": "future",
                                                         "source_turn_id": "turn_000006"}])
        with self.assertRaises(ValueError):
            draft_record("CASE_X", parsed, artifact(), [{"item_id": "C1", "category": "Context", "text": "generated",
                                                         "source_turn_id": "turn_000005"}])

    def test_unresolved_tfg_keeps_tc_and_cannot_freeze(self):
        draft = draft_record("CASE_X", conversation(), [])
        self.assertTrue(draft["conversation_start_time"]["value"])
        self.assertEqual(draft["first_generation_cutoff"]["status"], "unresolved")
        self.assertEqual(draft["primary_repository_cutoff"], "tFG")
        with self.assertRaises(ValueError):
            validated(draft)
        no_response_time = draft_record("CASE_X", conversation(response_time=None), artifact())
        self.assertEqual(no_response_time["first_generation_response_id"], "turn_000005")
        self.assertEqual(no_response_time["first_generation_cutoff"]["status"], "unresolved")
        self.assertEqual(no_response_time["conversation_start_time"], draft["conversation_start_time"])

    def test_date_precision_is_independent_for_both_anchors(self):
        date_c = draft_record("CASE_X", conversation(first_time="2024-01-01"), artifact())
        self.assertEqual(date_c["conversation_start_time"]["precision"], "date")
        self.assertEqual(date_c["first_generation_cutoff"]["precision"], "timestamp")
        both_dates = draft_record("CASE_X", conversation(first_time="2024-01-01",
                                                          response_time="2024-01-02"), artifact())
        self.assertEqual(both_dates["conversation_start_time"]["precision"], "date")
        self.assertEqual(both_dates["first_generation_cutoff"]["precision"], "date")
        self.assertEqual(both_dates["conversation_start_time"]["value"], "2024-01-01")

    def test_validation_and_versioned_freeze(self):
        draft = draft_record("CASE_X", conversation(), artifact())
        frozen = validated(draft)
        self.assertEqual(frozen["record_status"], "frozen")
        self.assertEqual(frozen["methodology_version"], "dir-tfg-v1")
        self.assertEqual(draft["record_status"], "draft")
        bad = dict(frozen)
        bad["methodology_version"] = "old-tc-v1"
        with self.assertRaises(ValueError):
            freeze_record(bad, frozen["validation_judgments"])
        with_item = draft_record("CASE_X", conversation(), artifact(), [
            {"item_id": "C1", "category": "Context", "text": "initial context",
             "source_turn_id": "turn_000000"}])
        with self.assertRaises(ValueError):
            freeze_record(with_item, frozen["validation_judgments"])
        self.assertEqual(validated(with_item)["record_status"], "frozen")

    def test_evidence_before_between_after_and_uncertain(self):
        frozen = validated(draft_record("CASE_X", conversation(), artifact()))
        def record(value, precision="timestamp", relevant=True, adds=True):
            return evidence_record(frozen, evidence_id="E1", artifact_id="src/a.py",
                                   historical_version="sha", evidence_time={"value": value,
                                   "precision": precision}, dimension="Context", bounded_fact="fact",
                                   task_relevant=relevant, adds_beyond_frozen_conversation=adds,
                                   retrieval_cue="a.py", retrieval_cue_turn_id="turn_000002",
                                   retrieval_operation="open",
                                   retrieval_path="prompt -> file", provenance={"source": "commit"})
        before = record("2023-12-31T00:00:00+00:00")
        between = record("2024-01-01T12:00:00+00:00")
        after = record("2024-01-03T00:00:00+00:00")
        self.assertEqual((before["available_by_tC"], before["available_by_tFG"]), ("YES", "YES"))
        self.assertEqual((between["available_by_tC"], between["available_by_tFG"]), ("NO", "YES"))
        self.assertEqual((after["available_by_tC"], after["available_by_tFG"]), ("NO", "NO"))
        safe = partition_record(frozen, between)
        self.assertEqual(safe["partition"], "SAFE")
        self.assertEqual(safe["conversation_start_time"], frozen["conversation_start_time"])
        self.assertEqual(safe["primary_repository_cutoff"], "tFG")
        self.assertEqual(partition_record(frozen, after)["partition"], "SEALED")
        redundant = record("2024-01-01T12:00:00+00:00", adds=False)
        self.assertFalse(redundant["adds_beyond_frozen_conversation"])
        self.assertEqual(partition_record(frozen, redundant)["partition"], "SAFE")
        no_useful = record("2024-01-01T12:00:00+00:00", relevant=False)
        self.assertEqual(partition_record(frozen, no_useful)["partition"], "SEALED")
        self.assertEqual(case_evidence_conclusion(frozen, [], review_complete=False), "unresolved")
        self.assertEqual(case_evidence_conclusion(frozen, [no_useful], review_complete=True),
                         "no_useful_additional_repository_evidence_found")
        self.assertEqual(case_evidence_conclusion(frozen, [between], review_complete=True),
                         "additional_evidence_found")
        outcome = dict(between, outcome_revealing=True)
        self.assertEqual(partition_record(frozen, outcome)["partition"], "SEALED")
        with self.assertRaises(ValueError):
            partition_record(frozen, {"case_id": "CASE_X", "methodology_version": "old-tc-v1",
                                      "primary_repository_cutoff": "tC"})
        self.assertEqual(availability({"value": "2024-01-01", "precision": "date"},
                                      frozen["conversation_start_time"]), "UNCERTAIN")
        self.assertEqual(availability({"value": "", "precision": ""},
                                      frozen["first_generation_cutoff"]), "UNAVAILABLE")

    def test_schema_files_are_valid_json_and_versioned(self):
        root = Path(__file__).resolve().parents[2]
        for name in ("frozen_conversation_v1.schema.json", "repository_evidence_v1.schema.json"):
            schema = json.loads((root / "schemas" / name).read_text())
            self.assertEqual(schema["properties"]["methodology_version"]["const"], "dir-tfg-v1")
            self.assertEqual(schema["properties"]["primary_repository_cutoff"]["const"], "tFG")


if __name__ == "__main__":
    unittest.main()
