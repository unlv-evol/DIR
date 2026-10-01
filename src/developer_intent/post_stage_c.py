"""Offline Post-Stage-C historical reconstruction and eligibility contracts."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

from .stage_c import canonical_hash, resolve_first_generation, validate_model_view, validate_stage_c_record

METHODOLOGY_VERSION = "dir-tfg-v2"
RECONSTRUCTION_CONTRACT_VERSION = "post-stage-c-reconstruction-v1"
ELIGIBILITY_CONTRACT_VERSION = "post-stage-c-eligibility-v1"
MANIFEST_SCHEMA_VERSION = "post-stage-c-eligibility-manifest-v1"
ATTEMPT_RECORD_VERSION = "historical-state-acquisition-v1"
HISTORICAL_INDEX_VERSION = "historical-information-index-v1"
PILOT_MANIFEST_VERSION = "post-stage-c-reconstruction-pilot-v1"
PILOT_SELECTION_VERSION = "post-stage-c-pilot-selection-v1"

TARGET_RULE = "historically_evidenced_focal_pr_base_state_at_tFG"
TARGET_TYPE = "git_commit"
SHA = re.compile(r"[0-9a-fA-F]{40,64}\Z")
EVIDENCE_LEVELS = {
    "level_1_direct_historical_pr_state": 1,
    "level_2_derivable_immutable_historical_relationship": 2,
    "level_3_contemporaneous_provider": 3,
    "level_4_present_day_pr_metadata": 4,
    "level_5_present_day_git_object_or_ref": 5,
}
TARGET_EVIDENCE_STATUSES = {"accepted", "rejected", "unresolved", "supporting_only"}
COMPONENT_STATUSES = {"not_assessed", "available", "unavailable", "unresolved", "not_applicable"}
SCIENTIFIC_VALUES = {"yes", "no", "unresolved"}
FAILURE_CATEGORIES = {
    "", "target_ambiguous", "identifier_missing", "temporal_relation_unresolved",
    "temporally_inadmissible", "object_not_found", "repository_unavailable",
    "authentication_blocked", "rate_limited", "transport_failed", "timed_out",
    "validation_failed", "scientifically_not_reconstructible",
}
INFRASTRUCTURE_FAILURES = {
    "object_not_found", "repository_unavailable", "authentication_blocked", "rate_limited",
    "transport_failed", "timed_out",
}

ELIGIBILITY_FIELDS = (
    "manifest_schema_version", "reconstruction_contract_version",
    "eligibility_contract_version", "methodology_version", "case_id",
    "stage_c_processability_status", "stage_c_authoritative_record",
    "stage_c_authoritative_record_sha256", "stage_c_authority_validation_status",
    "tC", "tC_precision", "tC_status", "tC_source",
    "tFG", "tFG_precision", "tFG_status", "tFG_source", "primary_repository_cutoff",
    "first_generation_boundary_identifiable", "first_generation_boundary_basis",
    "repository", "canonical_repository_url", "pr_number", "source_linkage_reference",
    "reconstruction_target_rule", "reconstruction_target_type", "candidate_target_identifier",
    "authoritative_target_identifier", "target_identity_status", "target_identity_basis",
    "historical_availability_status", "historical_availability_basis",
    "historical_state_reconstructible", "repository_component_status", "pr_component_status",
    "issue_component_status", "ci_component_status", "discussion_component_status",
    "reconstruction_status", "reconstruction_attempt_id", "reconstruction_evidence_ref",
    "reconstruction_log_ref", "failure_category", "failure_reason", "retry_disposition",
    "remaining_criteria_status", "final_scientific_eligibility", "exclusion_reason",
    "adjudication_required", "notes",
)

PILOT_FIELDS = (
    "pilot_manifest_version", "selection_algorithm_version", "selection_order", "case_id",
    "pa_pn_stratum", "repository", "pr_number", "pr_commits", "tFG_tC_interval_seconds",
    "pr_redirect_verified", "stage_b_source_origin", "stage_a_git_access_behavior",
    "selection_rationale", "reconstruction_executed",
)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def write_csv(path: Path, fields: Iterable[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=tuple(fields), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _instant(value: str, precision: str) -> date | datetime | None:
    if not value:
        return None
    if precision == "date":
        return date.fromisoformat(value)
    if precision == "timestamp":
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("Timestamp requires an explicit timezone")
        return parsed.astimezone(timezone.utc)
    raise ValueError("Temporal precision must be date or timestamp")


def temporal_relation_to_tfg(evidence: dict, tfg: dict) -> str:
    """Classify historical time under dir-tfg-v2's inclusive <= tFG rule."""
    earlier = _instant(str(evidence.get("value", "")), str(evidence.get("precision", "")))
    cutoff = _instant(str(tfg.get("value", "")), str(tfg.get("precision", "")))
    if earlier is None or cutoff is None:
        return "unavailable"
    if isinstance(earlier, datetime) and isinstance(cutoff, datetime):
        return "at_or_before" if earlier <= cutoff else "after"
    earlier_day = earlier.date() if isinstance(earlier, datetime) else earlier
    cutoff_day = cutoff.date() if isinstance(cutoff, datetime) else cutoff
    if earlier_day < cutoff_day:
        return "at_or_before"
    if earlier_day > cutoff_day:
        return "after"
    return "unresolved"


def first_generation_criterion(record: dict, package: dict) -> tuple[str, str]:
    """Resolve the boundary criterion only from a validated authoritative record."""
    validate_model_view(package, record.get("case_id", ""))
    validate_stage_c_record(record)
    status = record.get("status", {})
    fg = record.get("first_generation", {})
    tfg = record.get("temporal", {}).get("tFG", {})
    selection = {
        "status": fg.get("status", ""), "family_label": fg.get("family_label", ""),
        "artifact_ids": fg.get("artifact_refs", []),
        "response_turn_id": fg.get("response_turn_id", ""),
        "target_prompt_id": fg.get("target_prompt_id", ""),
        "candidate_artifact_ids": fg.get("candidate_artifact_ids", []),
        "rationale": fg.get("rationale", ""), "ambiguity_reason": fg.get("ambiguity_reason", ""),
    }
    expected_fg, expected_prefix, expected_tfg = resolve_first_generation(package, selection)
    complete = (
        status == {"stage_c_status": "complete", "parser_status": "parsed",
                   "validation_status": "validated", "failure_reason": ""}
        and fg == expected_fg and record.get("admissible_prior_turns") == expected_prefix
        and tfg == expected_tfg and fg.get("status") == "complete"
        and bool(fg.get("family_id")) and bool(fg.get("artifact_refs"))
        and bool(fg.get("response_turn_id")) and bool(fg.get("target_prompt_id"))
        and fg.get("boundary") == f"exclusive_before:{fg.get('response_turn_id')}"
        and tfg.get("status") in {"exact", "derivable"}
        and tfg.get("precision") in {"date", "timestamp"}
        and bool(tfg.get("value")) and bool(tfg.get("source"))
    )
    if not complete:
        return "unresolved", "authoritative_stage_c_boundary_contract_not_satisfied"
    return "yes", "validated_authoritative_stage_c_family_response_target_boundary_and_tFG"


def reconstructibility(*, repository_identity_verified: bool, focal_pr_identified: bool,
                       target_identity_status: str, target_unique: bool,
                       immutable_identifier_known: bool,
                       historical_availability_status: str, object_materialized: bool,
                       object_tree_validated: bool, deterministic_repeat: bool,
                       provenance_retained: bool, outcome_information_required: bool,
                       failure_category: str = "", affirmative_scientific_failure: bool = False) -> str:
    """Return the scientific criterion without converting infrastructure failure to `no`."""
    if failure_category not in FAILURE_CATEGORIES:
        raise ValueError("Unsupported reconstruction failure category")
    if affirmative_scientific_failure:
        if failure_category not in {"temporally_inadmissible", "scientifically_not_reconstructible"}:
            raise ValueError("Scientific no requires an affirmative scientific failure category")
        return "no"
    if failure_category in INFRASTRUCTURE_FAILURES:
        return "unresolved"
    satisfied = (
        repository_identity_verified and focal_pr_identified and target_unique
        and target_identity_status == "established"
        and immutable_identifier_known and historical_availability_status == "at_or_before"
        and object_materialized and object_tree_validated and deterministic_repeat
        and provenance_retained and not outcome_information_required
    )
    return "yes" if satisfied else "unresolved"


def validate_target_identity_claim(claim: dict) -> None:
    """Validate one retained target-identity claim without treating retrieval as identity proof."""
    required = {
        "claim_id", "evidence_level", "evidence_source_type", "evidence_source_identifier",
        "evidence_historical_timestamp", "evidence_timestamp_precision",
        "evidence_relation_to_tFG", "retrieval_timestamp", "evidence_hash",
        "provenance_reference", "asserted_base_sha", "evidence_status",
        "adequate_provenance", "cross_validated",
    }
    if set(claim) != required:
        raise ValueError("Target-identity claim has an invalid field contract")
    if claim["evidence_level"] not in EVIDENCE_LEVELS:
        raise ValueError("Unsupported target-identity evidence level")
    if claim["evidence_status"] not in TARGET_EVIDENCE_STATUSES:
        raise ValueError("Unsupported target-identity evidence status")
    if claim["evidence_timestamp_precision"] not in {"date", "timestamp", "unavailable"}:
        raise ValueError("Unsupported target-identity timestamp precision")
    if claim["evidence_relation_to_tFG"] not in {
            "at_or_before", "after", "unresolved", "unavailable"}:
        raise ValueError("Unsupported target-identity temporal relation")
    sha = claim["asserted_base_sha"]
    if sha and not SHA.fullmatch(sha):
        raise ValueError("Target-identity claim has an invalid base SHA")
    if not isinstance(claim["adequate_provenance"], bool) or not isinstance(
            claim["cross_validated"], bool):
        raise ValueError("Target-identity claim flags must be Boolean")


def resolve_target_identity(claims: list[dict]) -> dict:
    """Apply the frozen hierarchy while retaining every claim and disagreement."""
    retained = [dict(claim) for claim in claims]
    for claim in retained:
        validate_target_identity_claim(claim)
    qualifying = []
    for claim in retained:
        level = EVIDENCE_LEVELS[claim["evidence_level"]]
        establishes = (
            claim["evidence_status"] == "accepted"
            and claim["evidence_relation_to_tFG"] == "at_or_before"
            and bool(claim["evidence_historical_timestamp"])
            and claim["evidence_timestamp_precision"] in {"date", "timestamp"}
            and claim["adequate_provenance"]
            and bool(claim["asserted_base_sha"])
            and (level <= 2 or (level == 3 and claim["cross_validated"]))
        )
        if establishes:
            qualifying.append((level, claim))
    if not qualifying:
        return {"status": "unresolved", "authoritative_target_identifier": "",
                "basis": "no_historically_qualifying_target_identity_claim", "claims": retained}
    strongest = min(level for level, _ in qualifying)
    strongest_claims = [claim for level, claim in qualifying if level == strongest]
    identifiers = {claim["asserted_base_sha"].lower() for claim in strongest_claims}
    if len(identifiers) != 1:
        return {"status": "ambiguous", "authoritative_target_identifier": "",
                "basis": "conflicting_comparably_authoritative_historical_claims",
                "claims": retained}
    identifier = identifiers.pop()
    return {"status": "established", "authoritative_target_identifier": identifier,
            "basis": f"historical_evidence_hierarchy_level_{strongest}", "claims": retained}


def validate_target_adjudication(record: dict) -> None:
    """Enforce the allowed human role without permitting invented or outcome-based identity."""
    required = {"case_id", "candidate_states", "evidence_references", "hierarchy_levels",
                "decision", "selected_target_identifier", "rationale", "adjudicator_status",
                "timestamp", "contract_version", "decision_basis"}
    if set(record) != required:
        raise ValueError("Target adjudication has an invalid field contract")
    if record["contract_version"] != RECONSTRUCTION_CONTRACT_VERSION:
        raise ValueError("Target adjudication contract version mismatch")
    if record["decision"] not in {"select", "ambiguous", "unresolved"}:
        raise ValueError("Unsupported target adjudication decision")
    if record["adjudicator_status"] not in {"independent", "reconciled"}:
        raise ValueError("Unsupported adjudicator status")
    if record["decision_basis"] not in {
            "hierarchy_rank", "provenance_quality", "deterministic_derivation"}:
        raise ValueError("Adjudication basis cannot use fetchability, outcomes, or implementation")
    if record["decision"] == "select":
        selected = record["selected_target_identifier"].lower()
        candidates = {value.lower() for value in record["candidate_states"]}
        if not SHA.fullmatch(selected) or selected not in candidates:
            raise ValueError("Adjudication cannot invent a target identifier")
        if not record["evidence_references"] or not record["hierarchy_levels"]:
            raise ValueError("Target selection requires retained evidence and hierarchy levels")
    elif record["selected_target_identifier"]:
        raise ValueError("Non-selection adjudication cannot carry a selected target")


def stage_d_eligible(row: dict) -> bool:
    return (
        row.get("stage_c_processability_status") == "processable"
        and bool(row.get("stage_c_authoritative_record"))
        and row.get("stage_c_authority_validation_status") == "validated"
        and row.get("first_generation_boundary_identifiable") == "yes"
        and row.get("historical_state_reconstructible") == "yes"
        and row.get("remaining_criteria_status") == "all_satisfied"
        and row.get("final_scientific_eligibility") == "eligible"
    )


def _canonical_repository(screened: dict) -> str:
    path = urlparse(screened.get("canonical_pr_url", "")).path.strip("/").split("/")
    repository = "/".join(path[:2]) if len(path) >= 2 else screened["repository"]
    return f"https://github.com/{repository}"


def initialize_eligibility_rows(root: Path) -> list[dict[str, str]]:
    authority_rows = read_csv(root / "cases/manifests/stage_c_post_resolution_authority.csv")
    screened_rows = {r["case_id"]: r for r in read_csv(root / "cases/manifests/screened_PA_PN_cases.csv")}
    selected = [r for r in authority_rows if r["eligible_for_post_c_scientific_resolution"] == "true"]
    if len(authority_rows) != 122 or len({r["case_id"] for r in authority_rows}) != 122:
        raise ValueError("Stage C authority must contain 122 unique cases")
    if len(selected) != 111 or len({r["case_id"] for r in selected}) != 111:
        raise ValueError("Post-C initialization requires exactly 111 unique processable cases")
    rows = []
    for authority in selected:
        case_id = authority["case_id"]
        screened = screened_rows[case_id]
        record_path = root / authority["authoritative_record_path"]
        record = json.loads(record_path.read_text(encoding="utf-8"))
        package_path = root / record["input"]["stage_b_model_view_ref"]
        package = json.loads(package_path.read_text(encoding="utf-8"))
        if canonical_hash(package) != record["input"]["sha256"]:
            raise ValueError(f"Stage C input hash mismatch for {case_id}")
        boundary, boundary_basis = first_generation_criterion(record, package)
        if boundary != "yes":
            raise ValueError(f"Authoritative boundary did not resolve for {case_id}")
        tc, tfg = record["temporal"]["tC"], record["temporal"]["tFG"]
        row = {
            "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
            "reconstruction_contract_version": RECONSTRUCTION_CONTRACT_VERSION,
            "eligibility_contract_version": ELIGIBILITY_CONTRACT_VERSION,
            "methodology_version": METHODOLOGY_VERSION, "case_id": case_id,
            "stage_c_processability_status": "processable",
            "stage_c_authoritative_record": authority["authoritative_record_path"],
            "stage_c_authoritative_record_sha256": file_sha256(record_path),
            "stage_c_authority_validation_status": "validated",
            "tC": tc["value"], "tC_precision": tc["precision"], "tC_status": tc["status"],
            "tC_source": tc["source"], "tFG": tfg["value"],
            "tFG_precision": tfg["precision"], "tFG_status": tfg["status"],
            "tFG_source": tfg["source"], "primary_repository_cutoff": "tFG",
            "first_generation_boundary_identifiable": boundary,
            "first_generation_boundary_basis": boundary_basis,
            "repository": screened["repository"],
            "canonical_repository_url": _canonical_repository(screened),
            "pr_number": screened["pr_number"],
            "source_linkage_reference": f"cases/manifests/screened_PA_PN_cases.csv#{case_id}",
            "reconstruction_target_rule": TARGET_RULE, "reconstruction_target_type": TARGET_TYPE,
            "candidate_target_identifier": screened["project_history_access_object"],
            "authoritative_target_identifier": "", "target_identity_status": "candidate_only",
            "target_identity_basis": "stage_a_pr_base_sha_access_probe_not_historically_authoritative",
            "historical_availability_status": "not_assessed", "historical_availability_basis": "",
            "historical_state_reconstructible": "unresolved",
            "repository_component_status": "not_assessed", "pr_component_status": "not_assessed",
            "issue_component_status": "not_assessed", "ci_component_status": "not_assessed",
            "discussion_component_status": "not_assessed", "reconstruction_status": "not_attempted",
            "reconstruction_attempt_id": "", "reconstruction_evidence_ref": "",
            "reconstruction_log_ref": "", "failure_category": "", "failure_reason": "",
            "retry_disposition": "not_applicable", "remaining_criteria_status":
            "historical_state_reconstructible_unresolved",
            "final_scientific_eligibility": "pending_resolution", "exclusion_reason": "",
            "adjudication_required": "false",
            "notes": "Initialized offline; no repository acquisition or final eligibility decision performed.",
        }
        validate_eligibility_row(row, root=root)
        rows.append(row)
    return rows


def validate_eligibility_row(row: dict[str, str], *, root: Path | None = None) -> None:
    if tuple(row) != ELIGIBILITY_FIELDS:
        raise ValueError("Post-C eligibility row has an invalid field contract")
    if (row["manifest_schema_version"] != MANIFEST_SCHEMA_VERSION
            or row["reconstruction_contract_version"] != RECONSTRUCTION_CONTRACT_VERSION
            or row["eligibility_contract_version"] != ELIGIBILITY_CONTRACT_VERSION
            or row["methodology_version"] != METHODOLOGY_VERSION):
        raise ValueError("Post-C contract version mismatch")
    if row["stage_c_processability_status"] != "processable":
        raise ValueError("Only Stage C processable cases enter Post-C eligibility")
    if row["stage_c_authority_validation_status"] != "validated":
        raise ValueError("Post-C eligibility requires a validated Stage C authority")
    if row["first_generation_boundary_identifiable"] not in SCIENTIFIC_VALUES:
        raise ValueError("Invalid first-generation criterion")
    if row["target_identity_status"] not in {
            "candidate_only", "established", "ambiguous", "unresolved"}:
        raise ValueError("Invalid target-identity status")
    if row["historical_state_reconstructible"] not in SCIENTIFIC_VALUES:
        raise ValueError("Invalid historical-state criterion")
    if any(row[field] not in COMPONENT_STATUSES for field in (
            "repository_component_status", "pr_component_status", "issue_component_status",
            "ci_component_status", "discussion_component_status")):
        raise ValueError("Invalid H_i(tFG) component status")
    if row["failure_category"] not in FAILURE_CATEGORIES:
        raise ValueError("Invalid failure category")
    if row["primary_repository_cutoff"] != "tFG" or row["reconstruction_target_rule"] != TARGET_RULE:
        raise ValueError("Post-C temporal or reconstruction target policy mismatch")
    if row["final_scientific_eligibility"] not in {"eligible", "excluded", "pending_resolution"}:
        raise ValueError("Invalid final eligibility status")
    if row["adjudication_required"] not in {"true", "false"}:
        raise ValueError("Invalid adjudication flag")
    if root is not None:
        path = root / row["stage_c_authoritative_record"]
        if not path.is_file() or file_sha256(path) != row["stage_c_authoritative_record_sha256"]:
            raise ValueError("Stage C authority path/hash mismatch")


def initialize_acquisition_record(eligibility: dict[str, str]) -> dict:
    """Create an unexecuted acquisition record; no operation or result is fabricated."""
    return {
        "attempt_record_version": ATTEMPT_RECORD_VERSION,
        "reconstruction_contract_version": RECONSTRUCTION_CONTRACT_VERSION,
        "eligibility_contract_version": ELIGIBILITY_CONTRACT_VERSION,
        "methodology_version": METHODOLOGY_VERSION,
        "case_id": eligibility["case_id"],
        "repository": {"identity": eligibility["repository"],
                       "canonical_url": eligibility["canonical_repository_url"]},
        "pull_request": {"number": int(eligibility["pr_number"]),
                         "source_linkage_reference": eligibility["source_linkage_reference"]},
        "stage_c_authority": {"path": eligibility["stage_c_authoritative_record"],
                              "sha256": eligibility["stage_c_authoritative_record_sha256"]},
        "temporal": {
            "tC": {"value": eligibility["tC"], "precision": eligibility["tC_precision"],
                   "status": eligibility["tC_status"], "source": eligibility["tC_source"]},
            "tFG": {"value": eligibility["tFG"], "precision": eligibility["tFG_precision"],
                    "status": eligibility["tFG_status"], "source": eligibility["tFG_source"]},
            "primary_repository_cutoff": "tFG", "comparison_rule": "historical_timestamp_lte_tFG",
        },
        "target_selection": {
            "rule": TARGET_RULE, "type": TARGET_TYPE,
            "candidate_identifiers": ([eligibility["candidate_target_identifier"]]
                                      if eligibility["candidate_target_identifier"] else []),
            "authoritative_identifier": "", "identity_status": "candidate_only",
            "identity_basis": eligibility["target_identity_basis"],
            "historical_identity_evidence": [], "temporal_evidence": [],
            "adjudication": None,
        },
        "attempts": [],
        "object_validation": {"object_sha": "", "object_type": "", "parent_shas": [],
                              "tree_sha": "", "relationships_validated": False,
                              "deterministic_repeat_validated": False,
                              "materialized_state_identifier": ""},
        "components": {name: {"status": "not_assessed", "evidence_refs": []}
                       for name in ("repository", "pr", "issue", "ci", "discussion")},
        "reconstruction_status": "not_attempted", "failure_category": "",
        "failure_reason": "", "retry_disposition": "not_applicable",
        "historical_state_reconstructible": "unresolved",
        "scientific_basis": "", "notes": "No acquisition attempted.",
    }


def initialize_historical_index(eligibility: dict[str, str]) -> dict:
    return {
        "historical_index_version": HISTORICAL_INDEX_VERSION,
        "reconstruction_contract_version": RECONSTRUCTION_CONTRACT_VERSION,
        "methodology_version": METHODOLOGY_VERSION,
        "case_id": eligibility["case_id"],
        "tFG": {"value": eligibility["tFG"], "precision": eligibility["tFG_precision"],
                "status": eligibility["tFG_status"], "source": eligibility["tFG_source"]},
        "primary_repository_cutoff": "tFG",
        "target_identity_claims": [],
        "components": {name: {"status": "not_assessed", "items": []}
                       for name in ("repository", "pr", "issue", "ci", "discussion")},
    }


def _interval_seconds(t_c: str, t_fg: str) -> int:
    start = datetime.fromisoformat(t_c.replace("Z", "+00:00"))
    end = datetime.fromisoformat(t_fg.replace("Z", "+00:00"))
    return max(0, int((end - start).total_seconds()))


def _commit_bucket(value: int) -> str:
    return "low" if value <= 2 else "medium" if value <= 10 else "high"


def select_pilot(root: Path, eligibility_rows: list[dict[str, str]], *, size: int = 8) -> list[dict[str, str]]:
    """Select an offline PA/PN-balanced diversity pilot from allowlisted metadata."""
    if size != 8:
        raise ValueError("The frozen v1 pilot size is eight")
    screened = {r["case_id"]: r for r in read_csv(root / "cases/manifests/screened_PA_PN_cases.csv")}
    stage_b = {r["case_id"]: r for r in read_csv(root / "cases/manifests/stage_b_summary.csv")}
    selected_rows = []
    for stratum in ("PA", "PN"):
        candidates = []
        for eligibility in eligibility_rows:
            source = screened[eligibility["case_id"]]
            if source["Outcome_Class"] != stratum:
                continue
            commits = int(source["pr_commits"] or 0)
            interval = _interval_seconds(eligibility["tC"], eligibility["tFG"])
            features = {
                "commit_bucket": _commit_bucket(commits),
                "interval_bucket": "short" if interval <= 60 else "medium" if interval <= 600 else "long",
                "redirect": source["pr_redirect_verified"],
                "source_origin": stage_b[eligibility["case_id"]]["source_origin"],
                "git_access": source["project_history_access_status"],
            }
            tie = hashlib.sha256((PILOT_SELECTION_VERSION + ":" + eligibility["case_id"]).encode()).hexdigest()
            candidates.append((eligibility, source, stage_b[eligibility["case_id"]], commits,
                               interval, features, tie))
        chosen = []
        covered: set[tuple[str, str]] = set()
        while len(chosen) < size // 2:
            remaining = [c for c in candidates if c not in chosen]
            if not remaining:
                raise ValueError(f"Insufficient {stratum} cases for pilot")
            def score(candidate):
                features = candidate[5]
                gain = sum((key, value) not in covered for key, value in features.items())
                return (-gain, candidate[6])
            pick = sorted(remaining, key=score)[0]
            chosen.append(pick)
            covered.update(pick[5].items())
        selected_rows.extend((stratum, item) for item in chosen)
    result = []
    for order, (stratum, item) in enumerate(selected_rows, 1):
        eligibility, source, stage, commits, interval, features, _ = item
        rationale = ";".join(f"{key}={features[key]}" for key in sorted(features))
        result.append({
            "pilot_manifest_version": PILOT_MANIFEST_VERSION,
            "selection_algorithm_version": PILOT_SELECTION_VERSION,
            "selection_order": str(order), "case_id": eligibility["case_id"],
            "pa_pn_stratum": stratum, "repository": eligibility["repository"],
            "pr_number": eligibility["pr_number"], "pr_commits": str(commits),
            "tFG_tC_interval_seconds": str(interval),
            "pr_redirect_verified": source["pr_redirect_verified"],
            "stage_b_source_origin": stage["source_origin"],
            "stage_a_git_access_behavior": source["project_history_access_status"],
            "selection_rationale": rationale, "reconstruction_executed": "false",
        })
    return result
