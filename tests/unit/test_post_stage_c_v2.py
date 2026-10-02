from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import unittest
from pathlib import Path

from developer_intent.post_stage_c_v2 import (
    FROZEN_CASES, classify_pr_existence, initialize_acquisition_v2,
    initialize_boundary_v2, materialization_allowed, pilot_rows,
    reconstructibility_v2, resolve_repository_boundary, temporal_relation,
    validate_structured_intent_record, integrated_implementation_reveal_allowed,
    read_csv,
)

ROOT = Path(__file__).resolve().parents[2]


def claim(level="B1", sha="a" * 40, **changes):
    value = {"claim_id": f"{level}-{sha[:4]}", "evidence_level": level,
             "candidate_sha": sha, "source_identifier": "historical-source",
             "historical_source_timestamp": "2024-01-01T00:00:00Z",
             "timestamp_precision": "timestamp", "relation_to_tFG": "at_or_before",
             "development_context_linkage": "established", "derivation_rule": "direct",
             "derivation_inputs": ["historical-source"], "immutable_git_relationships": [],
             "validation_status": "validated", "evidence_hash": "f" * 64,
             "provenance_reference": "evidence/source", "adequate_provenance": True,
             "cross_validated": True, "uses_outcome_information": False}
    value.update(changes); return value


class PostStageCV2Tests(unittest.TestCase):
    def test_pr_after_tfg_is_unavailable_but_not_reconstruction_failure(self):
        eligibility = next(r for r in read_csv(ROOT / "cases/manifests/post_stage_c_eligibility.csv")
                           if r["case_id"] == "CASE_85AD863F8290")
        audit = next(r for r in read_csv(ROOT / "cases/manifests/post_stage_c_historical_target_audit.csv")
                     if r["case_id"] == eligibility["case_id"])
        record = initialize_acquisition_v2(eligibility, audit)
        self.assertEqual(record["pr"]["existed_by_tFG"], "no")
        self.assertEqual(record["pr"]["component_status"], "unavailable_by_tFG")
        self.assertEqual(record["historical_state_reconstructible"], "unresolved")

    def test_pr_before_tfg_may_contribute(self):
        self.assertEqual(classify_pr_existence("2024-01-01T00:00:00Z", "timestamp",
                                              "2024-01-02T00:00:00Z", "timestamp"), "yes")
        self.assertEqual(resolve_repository_boundary([claim("B3")])["status"], "established")

    def test_b4_b5_and_shortcuts_cannot_establish_authority(self):
        for level, source in (("B4", "archived_commit_list"), ("B5", "current_pr_base")):
            result = resolve_repository_boundary([claim(level, source_identifier=source)])
            self.assertEqual(result["status"], "unresolved")
        for shortcut in ("latest_before_tfg", "current_default_branch", "commit_timestamp_only"):
            self.assertEqual(resolve_repository_boundary(
                [claim("B5", source_identifier=shortcut)])["status"], "unresolved")

    def test_stronger_history_outranks_current_and_conflicts_fail_closed(self):
        result = resolve_repository_boundary([claim("B1", "a" * 40), claim("B5", "b" * 40)])
        self.assertEqual(result["authoritative_R_i_tFG"], "a" * 40)
        conflict = resolve_repository_boundary([claim("B1", "a" * 40), claim("B1", "b" * 40)])
        self.assertEqual(conflict["status"], "ambiguous")

    def test_b2_requires_historically_linked_immutable_derivation(self):
        unresolved = resolve_repository_boundary([claim("B2")])
        self.assertEqual(unresolved["status"], "unresolved")
        resolved = resolve_repository_boundary([claim(
            "B2", derivation_rule="first_parent_of_historically_linked_focal_revision",
            immutable_git_relationships=["child a -> parent b"])])
        self.assertEqual(resolved["status"], "established")

    def test_materialization_follows_identity_and_fetchability_cannot_select(self):
        self.assertFalse(materialization_allowed("unresolved", "a" * 40))
        self.assertTrue(materialization_allowed("established", "a" * 40))

    def test_temporal_and_infrastructure_rules(self):
        self.assertEqual(temporal_relation("2024-01-02", "date", "2024-01-02", "date"), "unresolved")
        self.assertEqual(temporal_relation("2024-01-02T00:00:00Z", "timestamp",
                                           "2024-01-02T00:00:00Z", "timestamp"), "at_or_before")
        base = dict(target_identity_status="unresolved", development_linkage_status="unresolved",
                    temporal_applicability_status="unresolved", object_validation_status="not_attempted",
                    materialization_status="not_attempted", tree_validation_status="not_attempted",
                    deterministic_repeat=False, provenance_retained=True,
                    outcome_information_required=False)
        for failure in ("timed_out", "authentication_blocked", "rate_limited", "transport_failed"):
            self.assertEqual(reconstructibility_v2(**base, failure_category=failure), "unresolved")

    def test_stage_f_boundary_record_cannot_silently_replace_r(self):
        eligibility = read_csv(ROOT / "cases/manifests/post_stage_c_eligibility.csv")[0]
        audit = next(r for r in read_csv(ROOT / "cases/manifests/post_stage_c_historical_target_audit.csv")
                     if r["case_id"] == eligibility["case_id"])
        boundary = initialize_boundary_v2(initialize_acquisition_v2(eligibility, audit))
        self.assertEqual(boundary["authoritative_R_i_tFG"], "")
        self.assertEqual(boundary["primary_repository_cutoff"], "tFG")

    def test_v1_pilot_hashes_and_v2_plan(self):
        rows = pilot_rows(ROOT)
        self.assertEqual(tuple(r["case_id"] for r in rows), FROZEN_CASES)
        self.assertTrue(all(r["executed"] == "false" for r in rows))
        self.assertEqual([r["pa_pn_stratum"] for r in rows], ["PA"] * 4 + ["PN"] * 4)
        for case_id in FROZEN_CASES:
            self.assertTrue((ROOT / f"cases/reconstruction/{case_id}/historical_state_acquisition_v1.json").is_file())
            self.assertTrue((ROOT / f"data/derived/historical_information/{case_id}/historical_information_index_v1.json").is_file())

    def test_check_and_dry_run_are_zero_network_plan_operations(self):
        for option in ("--check-config", "--dry-run"):
            result = subprocess.run(["python3", "-B", "pipeline/post_stage_c/run_pilot_v2.py", option],
                                    cwd=ROOT, check=True, capture_output=True, text=True)
            self.assertIn("post-stage-c-reconstruction-v2", result.stdout)

    def test_stage_j_uses_only_frozen_inputs(self):
        record = {"developer_stated": [{"text": "goal", "source_ids": ["turn-1"]}],
                  "project_recovered": [{"text": "constraint", "source_ids": ["eng-1"]}],
                  "cautious_inference": [], "unresolved": []}
        validate_structured_intent_record(record, {"turn-1", "eng-1"})
        record["project_recovered"][0]["source_ids"] = ["new-repository-query"]
        with self.assertRaises(ValueError):
            validate_structured_intent_record(record, {"turn-1", "eng-1"})

    def test_stage_l_reveal_requires_outputs_and_l1_frozen(self):
        self.assertFalse(integrated_implementation_reveal_allowed(
            original_output_frozen=True, reconstructed_output_frozen=True,
            l1_fidelity_judgment_frozen=False))
        self.assertTrue(integrated_implementation_reveal_allowed(
            original_output_frozen=True, reconstructed_output_frozen=True,
            l1_fidelity_judgment_frozen=True))


if __name__ == "__main__":
    unittest.main()
