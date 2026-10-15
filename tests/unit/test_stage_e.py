import copy
import json
import tempfile
import unittest
from pathlib import Path

from developer_intent.stage_e import (
    CLOSURE,
    MANIFEST,
    RECORDS,
    _write_immutable,
    build_frozen_record,
    canonical_bytes,
    eligible_population,
    freeze,
    sha256,
    stage_d_closure,
    validate_frozen_record,
    verify,
)
from developer_intent.stage_d import MANIFEST as STAGE_D_SAMPLE, read_csv

ROOT = Path(__file__).resolve().parents[2]


class StageETests(unittest.TestCase):
    def test_stage_d_closure_gate_passes_explicit_criteria(self):
        closure = stage_d_closure(ROOT)
        self.assertEqual(closure["closure_status"], "passed")
        self.assertTrue(closure["stage_e_authorized"])
        self.assertEqual(len(closure["criteria"]), 8)
        self.assertTrue(all(item["status"] == "pass" for item in closure["criteria"]))
        self.assertEqual(closure["unresolved_issues"], [])

    def test_population_is_only_eligible_processable_cases(self):
        population = eligible_population(ROOT)
        self.assertEqual(len(population), 111)
        self.assertEqual(len({row["case_id"] for row in population}), 111)
        self.assertTrue(all(row["final_scientific_eligibility"] == "eligible"
                            and row["stage_c_processability_status"] == "processable"
                            and row["remaining_criteria_status"] == "all_satisfied"
                            for row in population))

    def test_record_completeness_temporal_boundary_and_provenance(self):
        row = eligible_population(ROOT)[0]
        sampled = {item["case_id"] for item in read_csv(ROOT / STAGE_D_SAMPLE)}
        record = build_frozen_record(ROOT, row, sampled, set(), sha256(ROOT / CLOSURE))
        validate_frozen_record(ROOT, record)
        self.assertEqual(record["record_status"], "frozen")
        self.assertEqual(record["primary_repository_cutoff"], "tFG")
        self.assertTrue(record["temporal"]["conversation_start_time"]["value"])
        self.assertTrue(record["temporal"]["first_generation_cutoff"]["value"])
        boundary = record["conversation_evidence"]["first_generation"]["identification"]["response_event_index"]
        self.assertTrue(all(turn["event_index"] < boundary
                            for turn in record["conversation_evidence"]["admissible_pre_tfg_turns"]))
        self.assertEqual(record["identity"]["pr_conversation_correspondence"], "yes")

    def test_invalid_boundary_span_and_source_hash_are_rejected(self):
        row = eligible_population(ROOT)[0]
        record = build_frozen_record(ROOT, row, set(), set(), sha256(ROOT / CLOSURE))
        leaked = copy.deepcopy(record)
        leaked["conversation_evidence"]["admissible_pre_tfg_turns"][0]["event_index"] = (
            leaked["conversation_evidence"]["first_generation"]["identification"]["response_event_index"])
        with self.assertRaisesRegex(ValueError, "post-boundary"):
            validate_frozen_record(ROOT, leaked)
        bad_span = copy.deepcopy(record)
        first_category = next(items for items in bad_span["csv_extraction"].values() if items)
        first_category[0]["evidence_spans"] = ["text that is absent from every cited turn"]
        with self.assertRaisesRegex(ValueError, "evidence span"):
            validate_frozen_record(ROOT, bad_span)
        bad_hash = copy.deepcopy(record)
        bad_hash["scientific_provenance"]["source_references"]["stage_c_record"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "source hash"):
            validate_frozen_record(ROOT, bad_hash)

    def test_immutable_write_is_idempotent_and_rejects_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "record.json"
            payload = canonical_bytes({"case_id": "CASE_TEST"})
            _write_immutable(path, payload)
            _write_immutable(path, payload)
            with self.assertRaises(FileExistsError):
                _write_immutable(path, canonical_bytes({"case_id": "CASE_CHANGED"}))

    def test_corpus_freeze_is_deterministic_and_independently_verifiable(self):
        first = freeze(ROOT)
        before = {path: sha256(path) for path in sorted((ROOT / RECORDS).glob("*.json"))}
        manifest_hash = sha256(ROOT / MANIFEST)
        second = freeze(ROOT)
        after = {path: sha256(path) for path in sorted((ROOT / RECORDS).glob("*.json"))}
        self.assertEqual(first, second)
        self.assertEqual(before, after)
        self.assertEqual(len(before), 111)
        self.assertEqual(manifest_hash, sha256(ROOT / MANIFEST))
        self.assertEqual(verify(ROOT)["records"], 111)


if __name__ == "__main__":
    unittest.main()
