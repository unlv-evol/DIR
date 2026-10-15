"""Stage D closure and immutable Stage E conversation-record freeze."""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from .stage_d import MANIFEST as STAGE_D_SAMPLE
from .stage_d import STAGE_C_AUTHORITY, read_csv
from .stage_d_analysis import (CATEGORICAL_FIELDS, OUTPUT_DIR as STAGE_D_ANALYSIS,
                               REVIEWER_A, REVIEWER_B, calculate_agreement,
                               sha256, validate_reviews)
from .stage_c import validate_stage_c_record

ELIGIBILITY = Path("cases/manifests/post_stage_c_eligibility.csv")
OUTPUT = Path("cases/stage_e")
RECORDS = OUTPUT / "frozen_records"
MANIFEST = OUTPUT / "stage_e_manifest.json"
SUMMARY = OUTPUT / "stage_e_summary.md"
CLOSURE = STAGE_D_ANALYSIS / "stage_d_closure.json"
SCHEMA = Path("schemas/stage_e_frozen_record_v1.schema.json")
RECORD_VERSION = "stage-e-frozen-conversation-v1"
MANIFEST_VERSION = "stage-e-freeze-manifest-v1"
EXPECTED_SAMPLE_HASH = "75c7c022471f91fd004690a9a31f4c39dabe13e0ae4279ae39bdb382d73b8630"
EXPECTED_AUTHORITY_HASH = "03682e1d5071e5e0cf5219fd647cf7311ee581feb44f07d13e0c863c95a171cb"


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False,
                       separators=(",", ":")) + "\n").encode("utf-8")


def canonical_hash(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _write_immutable(path: Path, content: bytes) -> None:
    if path.exists():
        if path.read_bytes() != content:
            raise FileExistsError(f"immutable Stage E artifact differs: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _criterion(identifier: str, passed: bool, evidence: Any) -> dict[str, Any]:
    return {"criterion": identifier, "status": "pass" if passed else "fail",
            "evidence": evidence}


def stage_d_closure(root: Path) -> dict[str, Any]:
    rows_a, rows_b = validate_reviews(root)
    agreement, _, disagreements = calculate_agreement(rows_a, rows_b)
    sampled = sorted(read_csv(root / STAGE_D_SAMPLE), key=lambda row: int(row["reviewer_order"]))
    disagreement_cases = sorted({row["case_id"] for row in disagreements})
    findings = (root / STAGE_D_ANALYSIS / "adjudication_findings.md").read_text()
    decisions = (root / STAGE_D_ANALYSIS / "adjudication_decisions.md").read_text()
    agreement_csv = root / STAGE_D_ANALYSIS / "inter_reviewer_agreement.csv"
    disagreement_csv = root / STAGE_D_ANALYSIS / "reviewer_disagreements.csv"
    source_hashes = {
        str(REVIEWER_A): sha256(root / REVIEWER_A),
        str(REVIEWER_B): sha256(root / REVIEWER_B),
        str(STAGE_D_SAMPLE): sha256(root / STAGE_D_SAMPLE),
        str(STAGE_C_AUTHORITY): sha256(root / STAGE_C_AUTHORITY),
        str(agreement_csv.relative_to(root)): sha256(agreement_csv),
        str(disagreement_csv.relative_to(root)): sha256(disagreement_csv),
        str((root / STAGE_D_ANALYSIS / "adjudication_findings.md").relative_to(root)):
            sha256(root / STAGE_D_ANALYSIS / "adjudication_findings.md"),
        str((root / STAGE_D_ANALYSIS / "adjudication_decisions.md").relative_to(root)):
            sha256(root / STAGE_D_ANALYSIS / "adjudication_decisions.md"),
    }
    total_pairs = sum(int(row["paired_judgments"]) for row in agreement)
    total_agreements = sum(int(row["agreements"]) for row in agreement)
    criteria = [
        _criterion("independent_workbooks_intact", len(rows_a) == len(rows_b) == 33,
                   {"reviewer_a_sha256": source_hashes[str(REVIEWER_A)],
                    "reviewer_b_sha256": source_hashes[str(REVIEWER_B)]}),
        _criterion("sample_matches_frozen_manifest",
                   [row["case_id"] for row in rows_a] == [row["case_id"] for row in sampled],
                   {"cases": len(sampled), "sampling_manifest_sha256": source_hashes[str(STAGE_D_SAMPLE)]}),
        _criterion("agreement_reproduced",
                   (total_agreements, total_pairs, len(disagreements)) == (289, 297, 8),
                   {"agreements": total_agreements, "paired_judgments": total_pairs,
                    "disagreements": len(disagreements), "disagreement_cases": disagreement_cases}),
        _criterion("all_disagreement_cases_adjudicated",
                   all(case_id in findings for case_id in disagreement_cases),
                   {"required_cases": disagreement_cases}),
        _criterion("findings_and_decisions_separate",
                   bool(findings.strip()) and bool(decisions.strip()),
                   {"findings_path": "cases/stage_d/analysis/adjudication_findings.md",
                    "decisions_path": "cases/stage_d/analysis/adjudication_decisions.md"}),
        _criterion("conversation_state_policy_retained",
                   "Developer and assistant turns before `tFG` remain admissible" in decisions,
                   {"policy": "pre-tFG conversation-state evidence"}),
        _criterion("no_stage_c_correction_required",
                   "Preserve all authoritative Stage C extraction records" in decisions,
                   {"stage_c_authority_sha256": source_hashes[str(STAGE_C_AUTHORITY)]}),
        _criterion("no_unresolved_systematic_defect",
                   all(phrase in decisions for phrase in (
                       "Retain the conversation-state C/S/V methodology",
                       "require no Stage C modification",
                       "Preserve both original reviewer records")),
                   {"basis": "adjudication decisions retain the method, require no Stage C "
                             "change, and preserve independent-review integrity"}),
    ]
    failed = [item["criterion"] for item in criteria if item["status"] != "pass"]
    return {
        "closure_version": "stage-d-closure-v1", "methodology_version": "dir-tfg-v2",
        "closure_status": "passed" if not failed else "failed",
        "criteria": criteria, "unresolved_issues": failed,
        "source_hashes": source_hashes,
        "stage_e_authorized": not failed,
    }


def write_stage_d_closure(root: Path) -> dict[str, Any]:
    closure = stage_d_closure(root)
    path = root / CLOSURE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(closure))
    return closure


def eligible_population(root: Path) -> list[dict[str, str]]:
    rows = [row for row in read_csv(root / ELIGIBILITY)
            if row["final_scientific_eligibility"] == "eligible"]
    if len(rows) != 111 or len({row["case_id"] for row in rows}) != 111:
        raise ValueError("Stage E requires exactly 111 unique eligible cases")
    if any(row["remaining_criteria_status"] != "all_satisfied"
           or row["stage_c_processability_status"] != "processable"
           or row["historical_state_reconstructible"] != "yes" for row in rows):
        raise ValueError("eligible population contains unresolved or unprocessable cases")
    return sorted(rows, key=lambda row: row["case_id"])


def _file_ref(root: Path, path: Path) -> dict[str, str]:
    return {"path": str(path), "sha256": sha256(root / path)}


def build_frozen_record(root: Path, eligibility: dict[str, str], sampled: set[str],
                        adjudicated: set[str], closure_hash: str) -> dict[str, Any]:
    case_id = eligibility["case_id"]
    stage_c_path = Path(eligibility["stage_c_authoritative_record"])
    stage_c = json.loads((root / stage_c_path).read_text())
    validate_stage_c_record(stage_c)
    model_path = Path(stage_c["input"]["stage_b_model_view_ref"])
    model = json.loads((root / model_path).read_text())
    normalized_path = Path(f"cases/conversations/{case_id}/normalized_conversation.json")
    normalized = json.loads((root / normalized_path).read_text())
    linkage_path = Path(f"cases/manifests/linkage/{case_id}.json")
    linkage = json.loads((root / linkage_path).read_text())
    correspondence_path = Path(linkage["correspondence_review_ref"])
    correspondence = json.loads((root / correspondence_path).read_text())
    fg = stage_c["first_generation"]
    turns = {turn["turn_id"]: turn for turn in model["visible_turns"]}
    target = turns[fg["target_prompt_id"]]
    response = turns[fg["response_turn_id"]]
    candidates = {item["candidate_id"]: item
                  for item in model["generated_technical_content_candidates"]}
    artifacts = [candidates[artifact_id] for artifact_id in fg["artifact_refs"]]
    categories = {}
    for category in ("context", "specificity", "verification"):
        categories[category] = [{
            "item_id": item["id"], "category": item["category"],
            "normalized_text": item["text"], "source_turn_ids": item["source_turns"],
            "source_roles": item["source_roles"], "evidence_spans": item["evidence"],
        } for item in stage_c[f"{category}_supplied"]]
    human_status = ("sampled_and_adjudicated" if case_id in adjudicated else
                    "sampled_and_human_validated" if case_id in sampled else "not_sampled")
    record = {
        "schema_version": RECORD_VERSION, "methodology_version": "dir-tfg-v2",
        "record_status": "frozen", "primary_repository_cutoff": "tFG",
        "identity": {
            "case_id": case_id, "outcome_class": linkage["Outcome_Class"],
            "repository": eligibility["repository"], "conversation_id": linkage["conversation_id"],
            "conversation_url": linkage["conversation_url"], "pr_number": int(linkage["pr_number"]),
            "pr_url": linkage["canonical_pr_url"],
            "pr_conversation_correspondence": correspondence.get(
                "judgment", linkage["pr_conversation_match"]),
        },
        "temporal": {
            "conversation_start_time": stage_c["temporal"]["tC"],
            "first_generation_cutoff": stage_c["temporal"]["tFG"],
            "original_timestamp_representation": {
                "target_prompt_create_time": target.get("create_time"),
                "first_generation_response_create_time": response.get("create_time")},
            "timezone": "UTC for normalized ISO anchors; source epoch values preserved",
        },
        "conversation_evidence": {
            "target_developer_prompt": target,
            "admissible_pre_tfg_turns": stage_c["admissible_prior_turns"],
            "first_generation_response": response,
            "first_generation": {"identification": fg, "artifacts": artifacts},
        },
        "csv_extraction": categories,
        "scientific_provenance": {
            "eligibility": {"decision": "eligible", "manifest_row": eligibility},
            "processability": {
                "stage_c": eligibility["stage_c_processability_status"],
                "historical_state_reconstructible": eligibility["historical_state_reconstructible"],
                "reconstruction_status": eligibility["reconstruction_status"],
                "selected_repository_state": eligibility["authoritative_target_identifier"],
                "reconstruction_evidence_ref": eligibility["reconstruction_evidence_ref"],
                "reconstruction_log_ref": eligibility["reconstruction_log_ref"],
            },
            "stage_c": {"schema_version": stage_c["schema_version"],
                        "extraction_version": stage_c["extraction_version"],
                        "model_provenance": stage_c["model_provenance"],
                        "record_derivation": stage_c["record_derivation"]},
            "stage_d": {"procedure_validation_status": "validated_and_closed",
                        "case_human_validation_status": human_status,
                        "closure_ref": str(CLOSURE), "closure_sha256": closure_hash},
            "source_references": {
                "eligibility_manifest": _file_ref(root, ELIGIBILITY),
                "stage_c_authority": _file_ref(root, STAGE_C_AUTHORITY),
                "stage_c_record": _file_ref(root, stage_c_path),
                "stage_c_model_view": _file_ref(root, model_path),
                "normalized_conversation": _file_ref(root, normalized_path),
                "linkage": _file_ref(root, linkage_path),
                "correspondence_review": _file_ref(root, correspondence_path),
                "source_archive_sha256": normalized["source_archive_sha256"],
                "source_conversation_sha256": normalized["source_conversation_sha256"],
            },
        },
    }
    validate_frozen_record(root, record)
    return record


def validate_frozen_record(root: Path, record: dict[str, Any]) -> None:
    if record.get("schema_version") != RECORD_VERSION or record.get("record_status") != "frozen":
        raise ValueError("invalid Stage E record contract or status")
    case_id = record.get("identity", {}).get("case_id")
    if not case_id or record["scientific_provenance"]["eligibility"]["decision"] != "eligible":
        raise ValueError("missing identity or unresolved eligibility")
    if record["identity"].get("pr_conversation_correspondence") != "yes":
        raise ValueError("verified PR-conversation correspondence is required")
    temporal = record["temporal"]
    if not temporal["conversation_start_time"].get("value") or not temporal["first_generation_cutoff"].get("value"):
        raise ValueError("tC and authoritative tFG are required independently")
    evidence = record["conversation_evidence"]
    fg = evidence["first_generation"]["identification"]
    if fg.get("status") != "complete" or not fg.get("artifact_refs"):
        raise ValueError("first-generation identification is incomplete")
    prior = evidence["admissible_pre_tfg_turns"]
    indexes = [turn["event_index"] for turn in prior]
    if indexes != sorted(indexes) or len(indexes) != len(set(indexes)):
        raise ValueError("pre-tFG conversation ordering is invalid")
    boundary = fg["response_event_index"]
    if any(turn["event_index"] >= boundary for turn in prior):
        raise ValueError("post-boundary turn entered frozen pre-tFG evidence")
    turn_map = {turn["turn_id"]: turn for turn in prior}
    for category, items in record["csv_extraction"].items():
        for item in items:
            if item["category"] != category or len(item["source_turn_ids"]) != len(item["source_roles"]):
                raise ValueError("C/S/V category or positional provenance is invalid")
            cited = []
            for turn_id, role in zip(item["source_turn_ids"], item["source_roles"]):
                turn = turn_map.get(turn_id)
                if turn is None or turn["role"] != role:
                    raise ValueError("C/S/V source turn or role is invalid")
                cited.append(turn["text"])
            if any(not any(span in text for text in cited) for span in item["evidence_spans"]):
                raise ValueError("C/S/V evidence span does not match cited source content")
    refs = record["scientific_provenance"]["source_references"]
    for name, ref in refs.items():
        if isinstance(ref, dict) and {"path", "sha256"}.issubset(ref):
            if sha256(root / ref["path"]) != ref["sha256"]:
                raise ValueError(f"source hash mismatch: {name}")


def _summary(entries: list[dict[str, Any]], closure_hash: str) -> str:
    strata = Counter(entry["outcome_class"] for entry in entries)
    statuses = Counter(entry["case_human_validation_status"] for entry in entries)
    return f"""# Stage E authoritative conversation-record freeze

Stage D closure passed all eight explicit criteria. Its machine-readable record is `cases/stage_d/analysis/stage_d_closure.json` with SHA-256 `{closure_hash}`.

Stage E froze {len(entries)} scientifically eligible and processable cases: {strata['PA']} PA and {strata['PN']} PN. No case was rejected or blocked. All {len(entries)} records preserve `tC` and authoritative `tFG` independently, use `tFG` as the primary repository cutoff, and retain the authoritative Stage C extraction without regeneration or scoring.

Human-validation status remains scoped correctly: {statuses['sampled_and_human_validated']} sampled cases were independently reviewed, {statuses['sampled_and_adjudicated']} sampled disagreement cases were subsequently adjudicated, and {statuses['not_sampled']} cases were not sampled. Procedure validation does not imply individual review of the unsampled cases.

The records contain the existing Post-C selected repository-state references needed by Stage F to construct `H_i(tFG)`. Stage F has not been executed.

Verification is read-only:

```text
python3 -B pipeline/stage_e/run.py --verify
```
"""


def freeze(root: Path) -> dict[str, Any]:
    closure = write_stage_d_closure(root)
    if closure["closure_status"] != "passed":
        raise RuntimeError(f"Stage D closure failed: {closure['unresolved_issues']}")
    closure_hash = sha256(root / CLOSURE)
    population = eligible_population(root)
    sample_ids = {row["case_id"] for row in read_csv(root / STAGE_D_SAMPLE)}
    adjudicated = set(closure["criteria"][2]["evidence"]["disagreement_cases"])
    entries = []
    for row in population:
        record = build_frozen_record(root, row, sample_ids, adjudicated, closure_hash)
        path = RECORDS / f"{row['case_id']}.json"
        payload = canonical_bytes(record)
        _write_immutable(root / path, payload)
        entries.append({"case_id": row["case_id"], "outcome_class": record["identity"]["outcome_class"],
                        "record_path": str(path), "record_sha256": hashlib.sha256(payload).hexdigest(),
                        "schema_version": RECORD_VERSION,
                        "case_human_validation_status": record["scientific_provenance"]["stage_d"]["case_human_validation_status"],
                        "tC_present": True, "tFG_present": True,
                        "stage_f_repository_state_ref": row["reconstruction_log_ref"]})
    manifest = {
        "manifest_version": MANIFEST_VERSION, "methodology_version": "dir-tfg-v2",
        "completion_status": "complete", "record_count": len(entries),
        "population": dict(Counter(entry["outcome_class"] for entry in entries)),
        "schema_ref": _file_ref(root, SCHEMA), "stage_d_closure_ref": str(CLOSURE),
        "stage_d_closure_sha256": closure_hash,
        "upstream": {"eligibility": _file_ref(root, ELIGIBILITY),
                     "stage_c_authority": _file_ref(root, STAGE_C_AUTHORITY),
                     "stage_d_sampling_manifest": _file_ref(root, STAGE_D_SAMPLE)},
        "records": entries,
        "stage_f_readiness": {"status": "ready", "ready_cases": len(entries),
                              "tC_complete": len(entries), "tFG_complete": len(entries),
                              "execution_started": False},
    }
    _write_immutable(root / MANIFEST, canonical_bytes(manifest))
    _write_immutable(root / SUMMARY, _summary(entries, closure_hash).encode("utf-8"))
    return verify(root)


def verify(root: Path) -> dict[str, Any]:
    closure = stage_d_closure(root)
    if closure["closure_status"] != "passed":
        raise ValueError("Stage D closure no longer passes")
    manifest = json.loads((root / MANIFEST).read_text())
    if manifest.get("manifest_version") != MANIFEST_VERSION or manifest.get("completion_status") != "complete":
        raise ValueError("invalid or incomplete Stage E manifest")
    if sha256(root / CLOSURE) != manifest["stage_d_closure_sha256"]:
        raise ValueError("Stage D closure hash mismatch")
    population = eligible_population(root)
    if [entry["case_id"] for entry in manifest["records"]] != [row["case_id"] for row in population]:
        raise ValueError("Stage E manifest population differs from eligibility authority")
    seen = set()
    strata = Counter()
    human = Counter()
    for entry in manifest["records"]:
        if entry["case_id"] in seen:
            raise ValueError("duplicate Stage E case ID")
        seen.add(entry["case_id"])
        path = root / entry["record_path"]
        if sha256(path) != entry["record_sha256"]:
            raise ValueError(f"frozen record hash mismatch: {entry['case_id']}")
        record = json.loads(path.read_text())
        validate_frozen_record(root, record)
        strata[record["identity"]["outcome_class"]] += 1
        human[record["scientific_provenance"]["stage_d"]["case_human_validation_status"]] += 1
    if strata != {"PA": 68, "PN": 43} or len(seen) != 111:
        raise ValueError("Stage E population count mismatch")
    return {"status": "verified", "records": len(seen), "PA": strata["PA"], "PN": strata["PN"],
            "tC_complete": 111, "tFG_complete": 111,
            "human_validation_statuses": dict(sorted(human.items())),
            "stage_f_ready": True, "stage_f_started": False}
