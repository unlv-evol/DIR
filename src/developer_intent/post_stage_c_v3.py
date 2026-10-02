"""Frozen Post-Stage-C v3 B1 -> B2 reconstruction contracts."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from .post_stage_c import file_sha256
from .post_stage_c_v2 import FROZEN_CASES, temporal_relation

CONTRACT = "post-stage-c-reconstruction-v3"
PROCEDURE = "post-stage-c-b1-b2-pilot-v3"
ACQUISITION = "historical-state-acquisition-v3"
BOUNDARY = "historical-information-boundary-v3"
MANIFEST = "post-stage-c-reconstruction-pilot-v3"
FULL_SHA = re.compile(r"(?<![0-9a-fA-F])([0-9a-fA-F]{40})(?![0-9a-fA-F])")
ABBREV_SHA = re.compile(r"(?<![0-9a-fA-F])([0-9a-fA-F]{7,39})(?![0-9a-fA-F])")
REVISION_PREFIX = re.compile(r"\b(?:commit|revision|rev|sha)\s*[:=#]?\s*$", re.I)
BASELINE_WORDS = re.compile(r"\b(?:working from|based on|checked out|checkout|at)\s+(?:commit\s+)?", re.I)
CHANGE_WORDS = re.compile(r"\b(?:contains?|introduces?|implements?)\s+(?:the\s+)?(?:change|fix)|(?:change|fix)\s+in\s+commit\b", re.I)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def extract_b1(stage_c_record: dict) -> dict:
    """Extract only explicit revision identifiers from frozen pre-boundary turns."""
    candidates = []
    for turn in stage_c_record["admissible_prior_turns"]:
        text = turn.get("text", "")
        found = list(FULL_SHA.finditer(text))
        occupied = [m.span(1) for m in found]
        found += [m for m in ABBREV_SHA.finditer(text)
                  if not any(a <= m.start(1) and m.end(1) <= b for a, b in occupied)
                  and REVISION_PREFIX.search(text[max(0, m.start() - 24):m.start()])]
        for match in found:
            identifier = match.group(1).lower()
            before = text[max(0, match.start() - 80):match.start()]
            after = text[match.end():match.end() + 80]
            context = before + identifier + after
            if BASELINE_WORDS.search(before):
                interpretation, ambiguity = "identified_baseline_revision", "none"
            elif CHANGE_WORDS.search(context):
                interpretation, ambiguity = "identified_focal_change_revision", "none"
            else:
                interpretation, ambiguity = "explicit_revision_semantics_unresolved", "meaning_of_revision_unresolved"
            candidates.append({"identifier": identifier,
                               "identifier_type": "full_commit_sha" if len(identifier) == 40 else "abbreviated_commit_sha",
                               "source_turn_or_artifact": turn["turn_id"], "source_role": turn["role"],
                               "exact_evidence": context, "focal_task_linkage": "established",
                               "temporal_admissibility": "admissible_pre_tFG",
                               "ambiguity": ambiguity, "interpretation": interpretation})
    usable = [c for c in candidates if c["ambiguity"] == "none"]
    identifiers = {c["identifier"] for c in usable}
    status = "established" if len(identifiers) == 1 else "ambiguous" if len(identifiers) > 1 else "not_established"
    return {"status": status, "candidates": candidates}


def choose_target(b1: dict, b2: dict) -> dict:
    if b1["status"] != "established":
        return {"status": "unresolved", "candidate": "", "authoritative": "",
                "method": "no_unambiguous_b1_revision"}
    candidate = next(c for c in b1["candidates"] if c["ambiguity"] == "none")
    if candidate["interpretation"] == "identified_baseline_revision":
        return {"status": "established", "candidate": candidate["identifier"],
                "authoritative": candidate["identifier"], "method": "B1_direct_baseline"}
    if (candidate["interpretation"] == "identified_focal_change_revision"
            and b2.get("status") == "validated" and b2.get("starting_revision_source") == "B1"
            and b2.get("relationship_type") == "first_parent"
            and b2.get("relationship_result")):
        return {"status": "established", "candidate": b2["relationship_result"],
                "authoritative": b2["relationship_result"], "method": "B2_first_parent_from_B1_focal_change"}
    return {"status": "unresolved", "candidate": candidate["identifier"],
            "authoritative": "", "method": "B2_required_but_not_validated"}


def b5_cannot_start_b2(b1_status: str, starting_revision_source: str) -> bool:
    return b1_status != "established" and starting_revision_source == "B5"


def initialize_record(eligibility: dict, audit: dict, stage_c: dict) -> dict:
    b1 = extract_b1(stage_c)
    return {"record_version": ACQUISITION, "reconstruction_contract": CONTRACT,
            "procedure_version": PROCEDURE, "case_id": eligibility["case_id"],
            "repository": eligibility["repository"],
            "pr": {"number": int(eligibility["pr_number"]), "identity_role": "case_provenance_only",
                   "created_at": audit["pr_created_at"],
                   "existed_by_tFG": audit["pr_created_relative_to_tFG"] == "PR_EXISTED_AT_TFG"},
            "tC": {"value": eligibility["tC"], "precision": eligibility["tC_precision"], "source": eligibility["tC_source"]},
            "tFG": {"value": eligibility["tFG"], "precision": eligibility["tFG_precision"], "source": eligibility["tFG_source"]},
            "b1": b1,
            "b2": {"status": "not_attempted", "required": any(c["interpretation"] == "identified_focal_change_revision" and c["ambiguity"] == "none" for c in b1["candidates"]),
                   "starting_revision": "", "starting_revision_source": "B1", "relationship_type": "",
                   "relationship_result": "", "derivation": [], "derivation_validated": False},
            "b3": {"status": "not_used_v3"}, "b4": {"status": "not_used_v3"},
            "b5_support": [], "patchprompt_archive_repository_state_used": False,
            "candidate_R_i_tFG": "", "authoritative_R_i_tFG": "",
            "target_identity_status": "unresolved", "derivation_method": "", "conflicts": [],
            "materialization_status": "not_attempted", "object_validation": "not_attempted",
            "tree_validation": "not_attempted", "tree_identity": "",
            "historical_state_reconstructible": "unresolved",
            "scientific_reason": "no_usable_B1_evidence" if b1["status"] == "not_established" else "B1_requires_resolution",
            "infrastructure_reason": "", "human_adjudication_required": b1["status"] == "ambiguous",
            "executed": False}


def validate_acquisition(record: dict, schema_root: Path) -> None:
    schema = json.loads((schema_root / "historical_state_acquisition_v3.schema.json").read_text())
    if set(record) != set(schema["required"]):
        raise ValueError("V3 acquisition top-level contract mismatch")
    if record["record_version"] != ACQUISITION or record["reconstruction_contract"] != CONTRACT:
        raise ValueError("V3 acquisition version mismatch")
    if record["b3"] != {"status": "not_used_v3"} or record["b4"] != {"status": "not_used_v3"}:
        raise ValueError("B3/B4 cannot be enabled inside v3")
    if record["patchprompt_archive_repository_state_used"] is not False:
        raise ValueError("PatchPrompt repository-state evidence is prohibited in v3")
    if record["b2"]["starting_revision_source"] != "B1":
        raise ValueError("B2 must start from B1")
    if record["historical_state_reconstructible"] == "yes" and not (
            record["target_identity_status"] == "established"
            and record["materialization_status"] == "materialized"
            and record["object_validation"] == "validated"
            and record["tree_validation"] == "validated"):
        raise ValueError("Reconstructible yes lacks the complete validated chain")


def validate_boundary(record: dict, schema_root: Path) -> None:
    schema = json.loads((schema_root / "historical_information_boundary_v3.schema.json").read_text())
    if set(record) != set(schema["required"]):
        raise ValueError("V3 boundary top-level contract mismatch")
    if (record["boundary_record_version"] != BOUNDARY
            or record["reconstruction_contract"] != CONTRACT
            or record["b3_status"] != "not_used_v3"
            or record["b4_status"] != "not_used_v3"
            or record["patchprompt_archive_repository_state_used"] is not False):
        raise ValueError("V3 boundary invariant mismatch")


def pilot_rows(root: Path) -> list[dict[str, str]]:
    v2 = read_csv(root / "cases/manifests/post_stage_c_reconstruction_pilot_v2.csv")
    eligibility = {r["case_id"]: r for r in read_csv(root / "cases/manifests/post_stage_c_eligibility.csv")}
    rows = []
    for order, case_id in enumerate(FROZEN_CASES, 1):
        prior, source = next(r for r in v2 if r["case_id"] == case_id), eligibility[case_id]
        rows.append({"pilot_manifest_version": MANIFEST, "procedure_version": PROCEDURE,
                     "selection_order": str(order), "case_id": case_id,
                     "pa_pn_stratum": prior["pa_pn_stratum"], "repository": source["repository"],
                     "pr_number": source["pr_number"], "stage_c_authoritative_record": source["stage_c_authoritative_record"],
                     "planned_b1_source": "authoritative_stage_c_admissible_prior_turns",
                     "planned_b2_behavior": "conditional_on_established_B1",
                     "permitted_b5_support": "identity_routing_materialization_validation_only",
                     "patchprompt_archive_repository_state_input": "disabled", "executed": "false"})
    return rows


def validate_inputs(root: Path) -> list[dict[str, str]]:
    expected = pilot_rows(root)
    rows = read_csv(root / "cases/manifests/post_stage_c_reconstruction_pilot_v3.csv")
    if len(rows) != len(expected):
        raise ValueError("V3 pilot manifest row count mismatch")
    for row, planned in zip(rows, expected):
        for field in planned:
            if field != "executed" and row.get(field) != planned[field]:
                raise ValueError(f"V3 pilot manifest mismatch: {field}")
        if row.get("executed") not in {"true", "false"}:
            raise ValueError("V3 pilot execution state is invalid")
    eligibility = {r["case_id"]: r for r in read_csv(root / "cases/manifests/post_stage_c_eligibility.csv")}
    for row in rows:
        source = eligibility[row["case_id"]]; record = root / source["stage_c_authoritative_record"]
        if file_sha256(record) != source["stage_c_authoritative_record_sha256"]:
            raise ValueError("Stage C authority hash mismatch")
    return rows
