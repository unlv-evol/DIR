"""Offline contracts for the versioned Post-Stage-C development baseline."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path

METHODOLOGY_VERSION = "dir-tfg-v2"
RECONSTRUCTION_CONTRACT_VERSION = "post-stage-c-reconstruction-v2"
ACQUISITION_RECORD_VERSION = "historical-state-acquisition-v2"
BOUNDARY_RECORD_VERSION = "historical-information-boundary-v2"
PILOT_MANIFEST_VERSION = "post-stage-c-reconstruction-pilot-v2"
PILOT_PROCEDURE_VERSION = "post-stage-c-development-baseline-pilot-v2"
TARGET_RULE = "historically_justified_development_repository_baseline_at_tFG"

FROZEN_CASES = (
    "CASE_97AFC2022473", "CASE_F93FFAA22B9B", "CASE_85AD863F8290",
    "CASE_BFB2599E145D", "CASE_CE4BF3CB944D", "CASE_F13F98792012",
    "CASE_F7BED13B8119", "CASE_EE7F13CD9FB7",
)
EVIDENCE_LEVELS = {"B1": 1, "B2": 2, "B3": 3, "B4": 4, "B5": 5}
SUPPORTING_LEVELS = {"B4", "B5"}
INFRASTRUCTURE_FAILURES = {
    "authentication_blocked", "rate_limited", "transport_failed", "timed_out",
    "repository_unavailable", "object_not_found",
}
SHA = __import__("re").compile(r"[0-9a-fA-F]{40,64}\Z")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def _instant(value: str, precision: str) -> date | datetime:
    if precision == "timestamp":
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("Timestamp requires timezone")
        return parsed.astimezone(timezone.utc)
    if precision == "date":
        return date.fromisoformat(value)
    raise ValueError("Temporal precision must be date or timestamp")


def temporal_relation(value: str, precision: str, tfg: str, tfg_precision: str) -> str:
    earlier, cutoff = _instant(value, precision), _instant(tfg, tfg_precision)
    if isinstance(earlier, datetime) and isinstance(cutoff, datetime):
        return "at_or_before" if earlier <= cutoff else "after"
    earlier_day = earlier.date() if isinstance(earlier, datetime) else earlier
    cutoff_day = cutoff.date() if isinstance(cutoff, datetime) else cutoff
    if earlier_day < cutoff_day:
        return "at_or_before"
    if earlier_day > cutoff_day:
        return "after"
    return "unresolved"


def classify_pr_existence(created_at: str, precision: str, tfg: str,
                          tfg_precision: str) -> str:
    relation = temporal_relation(created_at, precision, tfg, tfg_precision)
    return {"at_or_before": "yes", "after": "no", "unresolved": "unresolved"}[relation]


def validate_baseline_claim(claim: dict) -> None:
    required = {
        "claim_id", "evidence_level", "candidate_sha", "source_identifier",
        "historical_source_timestamp", "timestamp_precision", "relation_to_tFG",
        "development_context_linkage", "derivation_rule", "derivation_inputs",
        "immutable_git_relationships", "validation_status", "evidence_hash",
        "provenance_reference", "adequate_provenance", "cross_validated",
        "uses_outcome_information",
    }
    if set(claim) != required or claim["evidence_level"] not in EVIDENCE_LEVELS:
        raise ValueError("Invalid development-baseline evidence claim")
    if claim["candidate_sha"] and not SHA.fullmatch(claim["candidate_sha"]):
        raise ValueError("Invalid candidate SHA")
    if claim["relation_to_tFG"] not in {"at_or_before", "after", "unresolved"}:
        raise ValueError("Invalid temporal relation")
    if claim["development_context_linkage"] not in {"established", "unresolved", "absent"}:
        raise ValueError("Invalid development linkage")
    if claim["validation_status"] not in {"validated", "unresolved", "rejected", "supporting_only"}:
        raise ValueError("Invalid claim validation status")
    for key in ("adequate_provenance", "cross_validated", "uses_outcome_information"):
        if not isinstance(claim[key], bool):
            raise ValueError("Claim flags must be Boolean")


def resolve_repository_boundary(claims: list[dict]) -> dict:
    """Apply B1-B5 without allowing materialization or proximity to establish identity."""
    retained = [dict(claim) for claim in claims]
    qualifying: list[tuple[int, dict]] = []
    for claim in retained:
        validate_baseline_claim(claim)
        level = EVIDENCE_LEVELS[claim["evidence_level"]]
        base = (
            level <= 3 and claim["validation_status"] == "validated"
            and claim["relation_to_tFG"] == "at_or_before"
            and claim["development_context_linkage"] == "established"
            and claim["adequate_provenance"] and not claim["uses_outcome_information"]
            and bool(claim["candidate_sha"])
        )
        if claim["evidence_level"] == "B2":
            base = base and bool(claim["immutable_git_relationships"])
        if claim["evidence_level"] == "B3":
            base = base and claim["cross_validated"]
        if base:
            qualifying.append((level, claim))
    if not qualifying:
        return {"status": "unresolved", "authoritative_R_i_tFG": "",
                "basis": "no_qualifying_development_baseline_claim", "claims": retained}
    strongest = min(level for level, _ in qualifying)
    best = [claim for level, claim in qualifying if level == strongest]
    identifiers = {claim["candidate_sha"].lower() for claim in best}
    if len(identifiers) != 1:
        return {"status": "ambiguous", "authoritative_R_i_tFG": "",
                "basis": "conflicting_comparable_historical_claims", "claims": retained}
    return {"status": "established", "authoritative_R_i_tFG": identifiers.pop(),
            "basis": f"development_baseline_{best[0]['evidence_level']}", "claims": retained}


def materialization_allowed(target_identity_status: str, authoritative_sha: str) -> bool:
    return target_identity_status == "established" and bool(SHA.fullmatch(authoritative_sha))


def reconstructibility_v2(*, target_identity_status: str, development_linkage_status: str,
                          temporal_applicability_status: str, object_validation_status: str,
                          materialization_status: str, tree_validation_status: str,
                          deterministic_repeat: bool, provenance_retained: bool,
                          outcome_information_required: bool, failure_category: str = "",
                          affirmative_scientific_failure: bool = False) -> str:
    if failure_category in INFRASTRUCTURE_FAILURES:
        return "unresolved"
    if affirmative_scientific_failure:
        if failure_category != "scientifically_not_reconstructible":
            raise ValueError("Scientific no requires affirmative scientific evidence")
        return "no"
    satisfied = (
        target_identity_status == "established"
        and development_linkage_status == "established"
        and temporal_applicability_status == "at_or_before"
        and object_validation_status == "validated"
        and materialization_status == "materialized"
        and tree_validation_status == "validated"
        and deterministic_repeat and provenance_retained
        and not outcome_information_required
    )
    return "yes" if satisfied else "unresolved"


def initialize_acquisition_v2(eligibility: dict[str, str], audit: dict[str, str]) -> dict:
    pr_exists = "yes" if audit["pr_created_relative_to_tFG"] == "PR_EXISTED_AT_TFG" else "no"
    pr_status = "available_by_tFG" if pr_exists == "yes" else "unavailable_by_tFG"
    return {
        "record_version": ACQUISITION_RECORD_VERSION,
        "reconstruction_contract_version": RECONSTRUCTION_CONTRACT_VERSION,
        "methodology_version": METHODOLOGY_VERSION,
        "procedure_version": PILOT_PROCEDURE_VERSION,
        "case_id": eligibility["case_id"],
        "repository": eligibility["repository"],
        "tC": {"value": eligibility["tC"], "precision": eligibility["tC_precision"],
               "status": eligibility["tC_status"], "source": eligibility["tC_source"]},
        "tFG": {"value": eligibility["tFG"], "precision": eligibility["tFG_precision"],
                "status": eligibility["tFG_status"], "source": eligibility["tFG_source"]},
        "primary_repository_cutoff": "tFG",
        "pr": {"number": int(eligibility["pr_number"]), "created_at": audit["pr_created_at"],
               "existed_by_tFG": pr_exists, "component_status": pr_status},
        "target_rule": TARGET_RULE,
        "candidate_repository_boundaries": [], "authoritative_R_i_tFG": "",
        "target_identity_status": "unresolved", "development_linkage_status": "unresolved",
        "temporal_applicability_status": "unresolved", "materialization_status": "not_attempted",
        "object_validation_status": "not_attempted", "tree_validation_status": "not_attempted",
        "tree_identity": "", "historical_state_reconstructible": "unresolved",
        "scientific_reason": "development_baseline_not_yet_assessed",
        "operational_reason": "", "evidence_claims": [], "derivation_chain": [],
        "conflicts": [], "human_adjudication_status": "not_required",
        "attempts": [], "executed": False,
    }


def initialize_boundary_v2(acquisition: dict) -> dict:
    return {
        "boundary_record_version": BOUNDARY_RECORD_VERSION,
        "reconstruction_contract_version": RECONSTRUCTION_CONTRACT_VERSION,
        "methodology_version": METHODOLOGY_VERSION,
        "case_id": acquisition["case_id"], "tC": acquisition["tC"], "tFG": acquisition["tFG"],
        "primary_repository_cutoff": "tFG", "repository": acquisition["repository"],
        "pr_existed_by_tFG": acquisition["pr"]["existed_by_tFG"],
        "pr_component_status": acquisition["pr"]["component_status"],
        "authoritative_R_i_tFG": "", "target_identity_status": "unresolved",
        "development_linkage_status": "unresolved", "temporal_applicability_status": "unresolved",
        "materialization_status": "not_attempted", "object_validation_status": "not_attempted",
        "tree_validation_status": "not_attempted", "tree_identity": "",
        "historical_state_reconstructible": "unresolved", "provenance_references": [],
    }


def validate_structured_intent_record(record: dict, frozen_source_ids: set[str]) -> None:
    """Keep Stage J representational: every recovered claim must cite frozen Stage I input."""
    required = {"developer_stated", "project_recovered", "cautious_inference", "unresolved"}
    if set(record) != required:
        raise ValueError("Structured intent record has an invalid section contract")
    for section, items in record.items():
        if not isinstance(items, list):
            raise ValueError("Structured intent sections must be lists")
        for item in items:
            if set(item) != {"text", "source_ids"} or not item["text"]:
                raise ValueError("Structured intent item lacks text or provenance")
            if not set(item["source_ids"]).issubset(frozen_source_ids):
                raise ValueError("Stage J cannot introduce evidence outside frozen inputs")
            if section == "project_recovered" and not item["source_ids"]:
                raise ValueError("Recovered project claims require provenance")


def integrated_implementation_reveal_allowed(*, original_output_frozen: bool,
                                             reconstructed_output_frozen: bool,
                                             l1_fidelity_judgment_frozen: bool) -> bool:
    """Enforce the Stage L reveal boundary independently of effectiveness."""
    return (original_output_frozen and reconstructed_output_frozen
            and l1_fidelity_judgment_frozen)


def pilot_rows(root: Path) -> list[dict[str, str]]:
    prior = {r["case_id"]: r for r in read_csv(root / "cases/manifests/post_stage_c_reconstruction_pilot.csv")}
    audit = {r["case_id"]: r for r in read_csv(root / "cases/manifests/post_stage_c_historical_target_audit.csv")}
    rows = []
    for order, case_id in enumerate(FROZEN_CASES, 1):
        old, observed = prior[case_id], audit[case_id]
        rows.append({"pilot_manifest_version": PILOT_MANIFEST_VERSION,
                     "procedure_version": PILOT_PROCEDURE_VERSION,
                     "selection_order": str(order), "case_id": case_id,
                     "pa_pn_stratum": old["pa_pn_stratum"], "repository": old["repository"],
                     "pr_number": old["pr_number"],
                     "pr_existed_by_tFG": "true" if observed["pr_created_relative_to_tFG"] == "PR_EXISTED_AT_TFG" else "false",
                     "audit_reference": "cases/manifests/post_stage_c_historical_target_audit.csv",
                     "v1_execution_reference": f"cases/reconstruction/{case_id}/historical_state_acquisition_v1.json",
                     "executed": "false"})
    return rows


def hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
