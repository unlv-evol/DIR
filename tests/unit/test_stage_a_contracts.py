"""Stable Protocol v5 Stage A v8 contracts."""

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from developer_intent.screening import (  # noqa: E402
    FIELDS, METHODOLOGY_VERSION, read_source, screen_rows, write_manifest)
from developer_intent.stage_a_contracts import (  # noqa: E402
    SCHEMA_DIR, parse_mapping_row, parse_screening_row,
    validate_correspondence_review, validate_csv, validate_stage_a_outputs)

SMOKE = ROOT / "data/intermediate/screening"


def raw_row():
    source = {"Case ID": "PA-1", "Outcome_Class": "PA",
              "PR_Link": "https://github.com/acme/repo/pull/1",
              "Conversation_Link": "https://chatgpt.com/share/b7853f70-84b8-477b-9879-a93a51215f81",
              "Context": "1", "Specificity": "2", "Verification": "0"}
    facts = {"pr": {"html_url": source["PR_Link"], "number": 1, "base_sha": "a" * 40},
             "files": [], "conversation": {"url": source["Conversation_Link"],
             "start": "2024-01-01", "precision": "date", "complete": True,
             "turns": [{"role": "user", "text": "task"}]},
             "history_access": {"judgment": "yes", "mechanism": "git_fetch_commit_object",
             "repository": "acme/repo", "object": "a" * 40,
             "status": "commit_object_retrieved", "source": "PR base_sha", "reason": ""},
             "processability": {"source": "fixture", "conversation_available": "yes",
             "first_generation_boundary_identifiable": "yes",
             "project_history_accessible": "yes", "historical_state_reconstructible": "yes"}}
    from developer_intent.screening import case_id
    facts["correspondence_review"] = {
        "case_id": case_id("PA-1"), "pr_url": source["PR_Link"],
        "conversation_url": source["Conversation_Link"], "judgment": "yes",
        "source": "restricted_stage_a_manual_review", "reviewer": "reviewer-1",
        "timestamp": "2026-09-22T00:00:00Z", "version": "review-v1",
        "evidence_ref": "packet:PA-1", "rationale": "same development task"}
    with tempfile.TemporaryDirectory() as directory:
        Path(directory, "PA-1.json").write_text(json.dumps(facts))
        row = screen_rows([source], Path(directory))[0]
        path = Path(directory, "row.csv")
        write_manifest([row], path)
        with path.open(newline="", encoding="utf-8") as stream:
            return next(csv.DictReader(stream))


class StageAContractTests(unittest.TestCase):
    def test_schema_covers_exact_producer_contract(self):
        schema = json.loads((SCHEMA_DIR / "dir_screening_v9.schema.json").read_text())
        self.assertEqual(len(FIELDS), 64)
        self.assertEqual(list(schema["properties"]), list(FIELDS))
        self.assertEqual(schema["required"], list(FIELDS))
        self.assertTrue(all(prop["description"] and prop["x-stage-owner"]
                            for prop in schema["properties"].values()))
        parsed = parse_screening_row(raw_row())
        self.assertEqual(parsed["methodology_version"], METHODOLOGY_VERSION)
        self.assertTrue(parsed["eligible"])
        self.assertEqual(parsed["source_linkage_status"], "established")
        self.assertEqual(parsed["pr_conversation_match"], "yes")

    def test_invalid_values_and_retired_fields_fail(self):
        baseline = raw_row()
        for changes in (
            {"screening_schema_version": "dir-screening-v8"},
            {"eligibility_status": "maybe"},
            {"first_generation_boundary_identifiable": "possibly"},
            {"pr_conversation_match": "maybe"},
            {"project_history_accessible": "maybe"},
            {"pr_redirect_verified": "maybe"},
            {"changed_files": "7.5"},
            {"conversation_start": "2024-01-08T11:48:08"},
            {"project_history_access_object": "not-a-sha"},
            {"prompt_identifier_signal": "detected"},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                parse_screening_row({**baseline, **changes})

    def test_producer_pending_without_acquired_evidence_validates(self):
        source = next(row for row in read_source(
            ROOT / "data/raw/final_analysis_dataset_from_patchprompt_study.csv")
            if row["Case ID"] == "PA-1")
        row = screen_rows([source])[0]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "screened.csv"
            write_manifest([row], path)
            parsed = validate_csv(path, "screening")
        self.assertEqual(parsed[0]["eligibility_status"], "pending_resolution")
        self.assertIsNone(parsed[0]["conversation_start"])

    def test_pending_with_only_deferred_reasons_is_ready_and_valid(self):
        baseline = raw_row()
        deferred = {
            **baseline,
            "first_generation_boundary_identifiable": "unresolved",
            "historical_state_reconstructible": "unresolved",
            "eligible": "",
            "eligibility_status": "pending_resolution",
            "pending_reason": ("first_generation_boundary_identifiable_unresolved;"
                               "historical_state_reconstructible_unresolved"),
            "stage_b_readiness_status": "ready_for_stage_b",
            "stage_b_readiness_reason": "pending_only_stage_c_tfg_deferred",
        }
        parsed = parse_screening_row(deferred)
        self.assertIsNone(parsed["eligible"])
        self.assertEqual(parsed["historical_state_reconstructible"], "unresolved")

    def test_scientific_status_reason_and_probe_invariants(self):
        baseline = raw_row()
        for changes in (
            {"pending_reason": "unrelated_reason"},
            {"eligibility_status": "excluded", "eligible": "false", "pending_reason": ""},
            {"project_history_access_mechanism": ""},
            {"project_history_access_object": ""},
            {"project_history_access_status": "not_attempted"},
            {"stage_b_readiness_status": "blocked"},
            {"conversation_turn_pattern": "multiple_developer_prompts"},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                parse_screening_row({**baseline, **changes})

    def test_stage_a_correspondence_requires_valid_provenance(self):
        baseline = raw_row()
        for changes in ({"pr_conversation_match": "yes", "pr_conversation_match_source": ""},
                        {"pr_conversation_match": "no", "pr_conversation_match_reason": ""},
                        {"pr_conversation_match": "yes",
                         "pr_conversation_match_source": "source_index_pair_only"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                parse_screening_row({**baseline, **changes})

    def test_mapping_schema_and_restricted_output(self):
        schema = json.loads((SCHEMA_DIR / "dir_case_mapping_v1.schema.json").read_text())
        self.assertEqual(len(schema["required"]), 7)
        rows = validate_csv(SMOKE / "smoke_1_case_mapping.csv", "mapping")
        self.assertEqual(rows[0]["mapping_schema_version"], "dir-case-mapping-v1")
        with (SMOKE / "smoke_1_case_mapping.csv").open(newline="", encoding="utf-8") as stream:
            raw = next(csv.DictReader(stream))
        for changes in ({"mapping_schema_version": "other"},
                        {"Outcome_Class": "NE"}, {"conversation_id": "wrong"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                parse_mapping_row({**raw, **changes})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "eligible.csv"
            path.write_text(",".join(FIELDS) + "\n")
            self.assertEqual(validate_csv(path, "screening"), [])
            path.write_text("case_id,other\n")
            with self.assertRaises(ValueError):
                validate_csv(path, "screening")

    def test_review_schema_accepts_unresolved_and_rejects_missing_provenance(self):
        schema = json.loads((SCHEMA_DIR / "correspondence_review_v1.schema.json").read_text())
        self.assertEqual(schema["$id"], "correspondence_review_v1.schema.json")
        self.assertEqual(schema["x-schema-version"], "dir-correspondence-review-v1")
        source = next(row for row in read_source(
            ROOT / "data/raw/final_analysis_dataset_from_patchprompt_study.csv")
            if row["Case ID"] == "PA-1")
        from developer_intent.screening import case_id
        review = {"case_id": case_id(source["Case ID"]), "pr_url": source["PR_Link"],
                  "conversation_url": source["Conversation_Link"], "judgment": "yes",
                  "source": "independent_administrative_review", "reviewer": "reviewer-1",
                  "timestamp": "2026-09-21T00:00:00Z", "version": "review-v1",
                  "evidence_ref": "research-ledger:1", "rationale": "independent task match"}
        self.assertEqual(validate_correspondence_review(review, source)["judgment"], "yes")
        self.assertEqual(validate_correspondence_review(
            {**review, "judgment": "unresolved"}, source)["judgment"], "unresolved")
        for changes in ({"reviewer": ""}, {"judgment": "maybe"},
                        {"source": "source_index_pair_only"},
                        {"timestamp": "2026-09-21"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate_correspondence_review({**review, **changes}, source)


if __name__ == "__main__":
    unittest.main()
