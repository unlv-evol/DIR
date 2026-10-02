"""Live, resumable execution for the frozen Post-C v3 B1/B2 pilot."""

from __future__ import annotations

import csv
import json
import time
from pathlib import Path
from typing import Callable

from .post_stage_c import file_sha256
from .post_stage_c_live import atomic_json, utc_now
from .post_stage_c_v2_live import git_materialize, git_parent_probe
from .post_stage_c_v3 import (BOUNDARY, CONTRACT, FROZEN_CASES, choose_target,
                              initialize_record, read_csv, validate_acquisition,
                              validate_boundary)

PILOT = Path("cases/manifests/post_stage_c_reconstruction_pilot_v3.csv")
ELIGIBILITY = Path("cases/manifests/post_stage_c_eligibility.csv")
AUDIT = Path("cases/manifests/post_stage_c_historical_target_audit.csv")


def output_paths(case_id: str) -> dict[str, Path]:
    return {
        "acquisition": Path(f"cases/reconstruction/{case_id}/historical_state_acquisition_v3.json"),
        "boundary": Path(f"data/derived/historical_information/{case_id}/historical_information_boundary_v3.json"),
    }


def preflight(root: Path) -> tuple[list[dict[str, str]], dict[str, dict[str, str]], dict[str, dict[str, str]]]:
    rows = read_csv(root / PILOT)
    eligibility = {r["case_id"]: r for r in read_csv(root / ELIGIBILITY)}
    audit = {r["case_id"]: r for r in read_csv(root / AUDIT)}
    if tuple(r["case_id"] for r in rows) != FROZEN_CASES:
        raise ValueError("V3 pilot population or order mismatch")
    for row in rows:
        case_id = row["case_id"]
        source = eligibility[case_id]
        stage_c = root / source["stage_c_authoritative_record"]
        if file_sha256(stage_c) != source["stage_c_authoritative_record_sha256"]:
            raise ValueError(f"Stage C authority hash mismatch: {case_id}")
        paths = output_paths(case_id)
        exists = [bool((root / path).exists()) for path in paths.values()]
        if row["executed"] == "true" and not all(exists):
            raise ValueError(f"Executed v3 row lacks persisted outputs: {case_id}")
        if row["executed"] == "false" and any(exists):
            raise ValueError(f"Unexecuted v3 row has partial outputs: {case_id}")
    return rows, eligibility, audit


def _atomic_csv(path: Path, rows: list[dict[str, str]]) -> None:
    temporary = path.with_suffix(".csv.tmp")
    with temporary.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)
    temporary.replace(path)


def _retry(operation: Callable, repository: str, sha: str, config: dict,
           sleep: Callable[[float], None]) -> tuple[dict, list[dict]]:
    attempts = []
    for number in range(1, config["transport_retries"] + 2):
        result = operation(repository, sha, timeout=config["timeout"])
        attempts.append({"attempt_number": number, **result})
        if result.get("status") not in {"transport_failed", "timed_out", "rate_limited"}:
            return result, attempts
        if number <= config["transport_retries"]:
            sleep(min(2 ** (number - 1), 4))
    return result, attempts


def execute_case(root: Path, eligibility: dict[str, str], audit: dict[str, str], config: dict,
                 *, relationship_probe: Callable = git_parent_probe,
                 materializer: Callable = git_materialize,
                 abbreviation_resolver: Callable | None = None,
                 sleep: Callable[[float], None] = time.sleep) -> dict:
    """Execute B1 -> optional B2 -> materialization; never query PR/archive state."""
    stage_c_path = root / eligibility["stage_c_authoritative_record"]
    stage_c = json.loads(stage_c_path.read_text(encoding="utf-8"))
    record = initialize_record(eligibility, audit, stage_c)
    repository = eligibility["repository"]
    attempts: list[dict] = []
    usable = [c for c in record["b1"]["candidates"] if c["ambiguity"] == "none"]
    if record["b1"]["status"] == "established":
        candidate = usable[0]
        revision = candidate["identifier"]
        if candidate["identifier_type"] == "abbreviated_commit_sha":
            if abbreviation_resolver is None:
                record["b1"]["status"] = "not_established"
                candidate["ambiguity"] = "abbreviation_not_deterministically_resolved"
            else:
                resolved = abbreviation_resolver(repository, revision, timeout=config["timeout"])
                attempts.append({"operation": "resolve_B1_abbreviation", **resolved})
                if resolved.get("status") == "validated" and len(resolved.get("full_sha", "")) == 40:
                    revision = resolved["full_sha"].lower()
                    candidate["identifier"] = revision
                    candidate["identifier_type"] = "full_commit_sha"
                else:
                    record["b1"]["status"] = "not_established"
                    candidate["ambiguity"] = "abbreviation_not_deterministically_resolved"
        if record["b1"]["status"] == "established" and candidate["interpretation"] == "identified_focal_change_revision":
            relation, relation_attempts = _retry(relationship_probe, repository, revision, config, sleep)
            attempts.extend({"operation": "B2_git_relationship", **a} for a in relation_attempts)
            relation_valid = (relation.get("status") == "validated"
                              and relation.get("requested_sha") == revision
                              and len(relation.get("parent_sha", "")) == 40)
            record["b2"].update(status="validated" if relation_valid else "unresolved",
                                starting_revision=revision, relationship_type="first_parent",
                                relationship_result=relation.get("parent_sha", ""),
                                derivation=[f"first_parent({revision})"],
                                derivation_validated=relation_valid)
    target = choose_target(record["b1"], record["b2"])
    record.update(candidate_R_i_tFG=target["candidate"], authoritative_R_i_tFG=target["authoritative"],
                  target_identity_status=target["status"], derivation_method=target["method"])
    if target["status"] == "established" and len(target["authoritative"]) == 40:
        material, material_attempts = _retry(materializer, repository, target["authoritative"], config, sleep)
        attempts.extend({"operation": "B5_target_materialization", **a} for a in material_attempts)
        record["b5_support"].append({"source": "current_git_remote", "purpose": "target_materialization_and_validation",
                                     "observation_time": utc_now(), "supporting_only": True})
        material_valid = (material.get("status") == "validated"
                          and material.get("object_type") == "commit"
                          and len(material.get("tree_sha", "")) == 40
                          and material.get("deterministic_repeat") is True)
        if material_valid:
            record.update(materialization_status="materialized", object_validation="validated",
                          tree_validation="validated", tree_identity=material.get("tree_sha", ""),
                          historical_state_reconstructible="yes", scientific_reason="B1_B2_target_and_materialization_validated")
        else:
            record.update(materialization_status="unresolved", object_validation="unresolved",
                          tree_validation="unresolved", infrastructure_reason=material.get("status", "unresolved"),
                          scientific_reason="target_established_materialization_unresolved")
    else:
        record["scientific_reason"] = ("no_usable_B1_evidence" if record["b1"]["status"] == "not_established"
                                       else "B1_or_B2_unresolved")
    record["executed"] = True
    boundary = {"boundary_record_version": BOUNDARY, "reconstruction_contract": CONTRACT,
                "case_id": record["case_id"], "tFG": record["tFG"], "repository": repository,
                "pr_existed_by_tFG": record["pr"]["existed_by_tFG"],
                "authoritative_R_i_tFG": record["authoritative_R_i_tFG"],
                "target_identity_status": record["target_identity_status"], "b1_status": record["b1"]["status"],
                "b2_status": record["b2"]["status"], "b3_status": "not_used_v3", "b4_status": "not_used_v3",
                "patchprompt_archive_repository_state_used": False,
                "materialization_status": record["materialization_status"], "object_validation": record["object_validation"],
                "tree_validation": record["tree_validation"], "tree_identity": record["tree_identity"],
                "historical_state_reconstructible": record["historical_state_reconstructible"],
                "provenance_references": [eligibility["stage_c_authoritative_record"]]}
    paths = output_paths(record["case_id"])
    schema_root = root / "schemas"
    if not schema_root.is_dir():
        schema_root = Path(__file__).resolve().parents[2] / "schemas"
    validate_acquisition(record, schema_root); validate_boundary(boundary, schema_root)
    atomic_json(root / paths["acquisition"], record); atomic_json(root / paths["boundary"], boundary)
    return {"record": record, "boundary": boundary, "attempts": attempts, "paths": paths}


def run_pilot(root: Path, config: dict, **dependencies) -> list[dict]:
    rows, eligibility, audit = preflight(root); results = []
    for row in rows:
        if row["executed"] == "true": continue
        results.append(execute_case(root, eligibility[row["case_id"]], audit[row["case_id"]], config, **dependencies))
        row["executed"] = "true"; _atomic_csv(root / PILOT, rows)
    return results
