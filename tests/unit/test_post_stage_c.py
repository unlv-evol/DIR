from __future__ import annotations

import csv
import hashlib
import json
import shutil
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from developer_intent.post_stage_c import (
    ELIGIBILITY_FIELDS,
    initialize_acquisition_record,
    initialize_eligibility_rows,
    initialize_historical_index,
    reconstructibility,
    resolve_target_identity,
    select_pilot,
    stage_d_eligible,
    temporal_relation_to_tfg,
    validate_target_adjudication,
    validate_eligibility_row,
)


ROOT = Path(__file__).resolve().parents[2]


class PostStageCContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = initialize_eligibility_rows(ROOT)

    def test_initializes_exactly_111_authority_bound_pending_rows(self):
        self.assertEqual(len(self.rows), 111)
        self.assertEqual(len({row["case_id"] for row in self.rows}), 111)
        self.assertTrue(all(tuple(row) == ELIGIBILITY_FIELDS for row in self.rows))
        self.assertTrue(all(row["final_scientific_eligibility"] == "pending_resolution"
                            for row in self.rows))
        self.assertTrue(all(row["historical_state_reconstructible"] == "unresolved"
                            for row in self.rows))
        for row in self.rows:
            validate_eligibility_row(row, root=ROOT)

    def test_only_processability_authorities_enter(self):
        with (ROOT / "cases/manifests/stage_c_post_resolution_authority.csv").open(
                newline="", encoding="utf-8") as stream:
            authority = list(csv.DictReader(stream))
        expected = {row["case_id"] for row in authority
                    if row["eligible_for_post_c_scientific_resolution"] == "true"}
        self.assertEqual({row["case_id"] for row in self.rows}, expected)
        self.assertEqual(len(authority) - len(expected), 11)

    def test_first_generation_criterion_and_authority_hashes(self):
        for row in self.rows:
            self.assertEqual(row["first_generation_boundary_identifiable"], "yes")
            self.assertEqual(row["stage_c_authority_validation_status"], "validated")
            path = ROOT / row["stage_c_authoritative_record"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),
                             row["stage_c_authoritative_record_sha256"])

    def test_temporal_inclusive_timestamp_and_date_uncertainty(self):
        cutoff = {"value": "2024-01-02T03:04:05+00:00", "precision": "timestamp"}
        self.assertEqual(temporal_relation_to_tfg(dict(cutoff), cutoff), "at_or_before")
        self.assertEqual(temporal_relation_to_tfg(
            {"value": "2024-01-02T03:04:06+00:00", "precision": "timestamp"}, cutoff), "after")
        self.assertEqual(temporal_relation_to_tfg(
            {"value": "2024-01-02", "precision": "date"},
            {"value": "2024-01-02", "precision": "date"}), "unresolved")

    def test_reconstructibility_ambiguity_missing_and_current_fetchability(self):
        base = dict(repository_identity_verified=True, focal_pr_identified=True,
                    target_identity_status="established", target_unique=True,
                    immutable_identifier_known=True,
                    historical_availability_status="at_or_before", object_materialized=True,
                    object_tree_validated=True, deterministic_repeat=True,
                    provenance_retained=True, outcome_information_required=False)
        self.assertEqual(reconstructibility(**base), "yes")
        for changed in ({"target_unique": False, "failure_category": "target_ambiguous"},
                        {"immutable_identifier_known": False,
                         "failure_category": "identifier_missing"},
                        {"historical_availability_status": "unresolved"}):
            candidate = dict(base); candidate.update(changed)
            self.assertEqual(reconstructibility(**candidate), "unresolved")
        current_only = dict(base, historical_availability_status="unresolved")
        self.assertEqual(reconstructibility(**current_only), "unresolved")

    def test_infrastructure_failures_remain_unresolved(self):
        base = dict(repository_identity_verified=True, focal_pr_identified=True,
                    target_identity_status="unresolved", target_unique=True,
                    immutable_identifier_known=True,
                    historical_availability_status="unresolved", object_materialized=False,
                    object_tree_validated=False, deterministic_repeat=False,
                    provenance_retained=True, outcome_information_required=False)
        for category in ("transport_failed", "timed_out", "repository_unavailable",
                         "authentication_blocked", "rate_limited", "object_not_found"):
            self.assertEqual(reconstructibility(**base, failure_category=category), "unresolved")

    def test_scientific_no_requires_affirmative_evidence(self):
        base = dict(repository_identity_verified=True, focal_pr_identified=True,
                    target_identity_status="established", target_unique=True,
                    immutable_identifier_known=True,
                    historical_availability_status="after", object_materialized=True,
                    object_tree_validated=True, deterministic_repeat=True,
                    provenance_retained=True, outcome_information_required=False)
        self.assertEqual(reconstructibility(**base, failure_category="temporally_inadmissible"),
                         "unresolved")
        self.assertEqual(reconstructibility(**base, failure_category="temporally_inadmissible",
                                            affirmative_scientific_failure=True), "no")
        with self.assertRaises(ValueError):
            reconstructibility(**base, failure_category="timed_out",
                               affirmative_scientific_failure=True)

    def test_component_absence_does_not_control_core_reconstructibility(self):
        row = self.rows[0]
        acquisition = initialize_acquisition_record(row)
        index = initialize_historical_index(row)
        acquisition["components"]["ci"]["status"] = "not_applicable"
        index["components"]["ci"]["status"] = "not_applicable"
        self.assertEqual(acquisition["historical_state_reconstructible"], "unresolved")
        self.assertEqual(index["components"]["repository"]["status"], "not_assessed")
        result = reconstructibility(
            repository_identity_verified=True, focal_pr_identified=True,
            target_identity_status="established", target_unique=True,
            immutable_identifier_known=True, historical_availability_status="at_or_before",
            object_materialized=True, object_tree_validated=True, deterministic_repeat=True,
            provenance_retained=True, outcome_information_required=False)
        self.assertEqual(result, "yes")

    @staticmethod
    def claim(level: int, sha: str = "a" * 40, **changes):
        claim = {
            "claim_id": f"claim-{level}-{sha[:4]}",
            "evidence_level": {
                1: "level_1_direct_historical_pr_state",
                2: "level_2_derivable_immutable_historical_relationship",
                3: "level_3_contemporaneous_provider",
                4: "level_4_present_day_pr_metadata",
                5: "level_5_present_day_git_object_or_ref",
            }[level],
            "evidence_source_type": "archived_pr_metadata" if level < 4 else "current_provider",
            "evidence_source_identifier": f"source-{level}",
            "evidence_historical_timestamp": "2024-01-01T00:00:00Z",
            "evidence_timestamp_precision": "timestamp",
            "evidence_relation_to_tFG": "at_or_before",
            "retrieval_timestamp": "2026-10-01T00:00:00Z",
            "evidence_hash": "f" * 64,
            "provenance_reference": f"evidence/{level}",
            "asserted_base_sha": sha,
            "evidence_status": "accepted",
            "adequate_provenance": True,
            "cross_validated": False,
        }
        claim.update(changes)
        return claim

    def test_historical_hierarchy_and_current_sources(self):
        direct = resolve_target_identity([self.claim(1)])
        self.assertEqual(direct["status"], "established")
        for claim in (
                self.claim(4), self.claim(5),
                self.claim(1, evidence_relation_to_tFG="unresolved")):
            resolution = resolve_target_identity([claim])
            self.assertEqual(resolution["status"], "unresolved")
            self.assertEqual(resolution["authoritative_target_identifier"], "")

    def test_commit_time_and_materialization_cannot_establish_identity(self):
        timestamp_only = self.claim(5, evidence_source_type="commit_timestamp")
        self.assertEqual(resolve_target_identity([timestamp_only])["status"], "unresolved")
        result = reconstructibility(
            repository_identity_verified=True, focal_pr_identified=True,
            target_identity_status="unresolved", target_unique=True,
            immutable_identifier_known=True, historical_availability_status="at_or_before",
            object_materialized=True, object_tree_validated=True, deterministic_repeat=True,
            provenance_retained=True, outcome_information_required=False)
        self.assertEqual(result, "unresolved")

    def test_stronger_historical_value_beats_different_current_value(self):
        historical = self.claim(1, "a" * 40)
        current = self.claim(4, "b" * 40, evidence_status="supporting_only")
        resolution = resolve_target_identity([historical, current])
        self.assertEqual(resolution["status"], "established")
        self.assertEqual(resolution["authoritative_target_identifier"], "a" * 40)
        self.assertEqual(len(resolution["claims"]), 2)

    def test_comparable_historical_conflict_is_ambiguous(self):
        resolution = resolve_target_identity([self.claim(1, "a" * 40),
                                              self.claim(1, "b" * 40)])
        self.assertEqual(resolution["status"], "ambiguous")
        self.assertEqual(resolution["authoritative_target_identifier"], "")
        self.assertEqual(len(resolution["claims"]), 2)

    def test_yes_requires_historical_identity_and_materialization(self):
        base = dict(repository_identity_verified=True, focal_pr_identified=True,
                    target_identity_status="established", target_unique=True,
                    immutable_identifier_known=True, historical_availability_status="at_or_before",
                    object_materialized=True, object_tree_validated=True,
                    deterministic_repeat=True, provenance_retained=True,
                    outcome_information_required=False)
        self.assertEqual(reconstructibility(**base), "yes")
        for changed in ({"target_identity_status": "unresolved"},
                        {"object_materialized": False}, {"object_tree_validated": False}):
            candidate = dict(base); candidate.update(changed)
            self.assertEqual(reconstructibility(**candidate), "unresolved")

    def test_adjudication_cannot_use_fetchability_or_invent_state(self):
        record = {
            "case_id": "CASE_AB42B2598A84", "candidate_states": ["a" * 40],
            "evidence_references": ["claim-1"],
            "hierarchy_levels": ["level_1_direct_historical_pr_state"],
            "decision": "select", "selected_target_identifier": "a" * 40,
            "rationale": "Direct historical PR state outranks current metadata.",
            "adjudicator_status": "independent", "timestamp": "2026-10-01T00:00:00Z",
            "contract_version": "post-stage-c-reconstruction-v1",
            "decision_basis": "hierarchy_rank",
        }
        validate_target_adjudication(record)
        invalid = dict(record, decision_basis="current_fetchability")
        with self.assertRaises(ValueError):
            validate_target_adjudication(invalid)
        invented = dict(record, selected_target_identifier="b" * 40)
        with self.assertRaises(ValueError):
            validate_target_adjudication(invented)

    def test_pilot_is_deterministic_balanced_and_outcome_fields_are_ignored(self):
        first = select_pilot(ROOT, self.rows)
        second = select_pilot(ROOT, self.rows)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 8)
        self.assertEqual(Counter(row["pa_pn_stratum"] for row in first), {"PA": 4, "PN": 4})
        self.assertTrue(all(row["reconstruction_executed"] == "false" for row in first))
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            (temp / "cases/manifests").mkdir(parents=True)
            for name in ("screened_PA_PN_cases.csv", "stage_b_summary.csv"):
                source = ROOT / "cases/manifests" / name
                with source.open(newline="", encoding="utf-8") as source_stream:
                    rows = list(csv.DictReader(source_stream))
                fields = list(rows[0]) + ["final_diff", "merge_outcome", "expected_eligibility"]
                for item in rows:
                    item.update(final_diff="PROHIBITED", merge_outcome="PROHIBITED",
                                expected_eligibility="PROHIBITED")
                with (temp / "cases/manifests" / name).open("w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
                    writer.writeheader(); writer.writerows(rows)
            self.assertEqual(first, select_pilot(temp, self.rows))

    def test_stage_d_requires_final_eligible_and_resolved_contract(self):
        row = dict(self.rows[0])
        self.assertFalse(stage_d_eligible(row))
        row.update(historical_state_reconstructible="yes", remaining_criteria_status="all_satisfied",
                   final_scientific_eligibility="eligible")
        self.assertTrue(stage_d_eligible(row))
        for key, value in (("historical_state_reconstructible", "unresolved"),
                           ("final_scientific_eligibility", "pending_resolution"),
                           ("first_generation_boundary_identifiable", "unresolved")):
            changed = dict(row); changed[key] = value
            self.assertFalse(stage_d_eligible(changed))
        changed = dict(row); changed["stage_c_authority_validation_status"] = "failed"
        self.assertFalse(stage_d_eligible(changed))

    def test_legacy_dir_tfg_v1_contracts_are_unchanged(self):
        expected = {
            "schemas/frozen_conversation_v1.schema.json": "30419bd5819a8cbdd2e9f4bea9e02fe27b925a3aa2a0a3ce7ffae3b2f5ba3cc0",
            "schemas/repository_evidence_v1.schema.json": "1b9a8a0bc82484571c2fb36a8a1f62e290f5eb9d0b998c4ff17ae7621d425a0e",
            "src/developer_intent/first_generation.py": "6f18dc6479ac13876d0f525702f02554c03d8344ad59912e4c6bab15907ae623",
            "src/developer_intent/temporal_evidence.py": "4735c5c81ab90d6720e748542f66c08fced7755c68f2de2d504c4c3ad58aff65",
        }
        for relative, digest in expected.items():
            self.assertEqual(hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(), digest)
        for name in ("post_stage_c_eligibility_v1.schema.json",
                     "historical_state_acquisition_v1.schema.json",
                     "historical_information_index_v1.schema.json"):
            json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))

    def test_new_schema_fields_match_initialized_contracts(self):
        eligibility_schema = json.loads((ROOT / "schemas/post_stage_c_eligibility_v1.schema.json").read_text())
        self.assertEqual(set(eligibility_schema["required"]), set(ELIGIBILITY_FIELDS))
        self.assertEqual(set(eligibility_schema["properties"]), set(ELIGIBILITY_FIELDS))
        acquisition = initialize_acquisition_record(self.rows[0])
        acquisition_schema = json.loads((ROOT / "schemas/historical_state_acquisition_v1.schema.json").read_text())
        self.assertEqual(set(acquisition), set(acquisition_schema["required"]))
        self.assertEqual(set(acquisition), set(acquisition_schema["properties"]))
        index = initialize_historical_index(self.rows[0])
        index_schema = json.loads((ROOT / "schemas/historical_information_index_v1.schema.json").read_text())
        self.assertEqual(set(index), set(index_schema["required"]))
        self.assertEqual(set(index), set(index_schema["properties"]))


if __name__ == "__main__":
    unittest.main()
