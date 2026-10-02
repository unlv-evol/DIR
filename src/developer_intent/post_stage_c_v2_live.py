"""Live acquisition adapter for the frozen Post-Stage-C v2 pilot."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

from .post_stage_c import file_sha256
from .post_stage_c_live import atomic_json, load_live_config, provider_get, utc_now
from .post_stage_c_v2 import (
    FROZEN_CASES, PILOT_MANIFEST_VERSION, classify_pr_existence,
    initialize_acquisition_v2, initialize_boundary_v2, materialization_allowed,
    read_csv, reconstructibility_v2, resolve_repository_boundary,
    temporal_relation, validate_baseline_claim,
)

PILOT_PATH = Path("cases/manifests/post_stage_c_reconstruction_pilot_v2.csv")
ELIGIBILITY_PATH = Path("cases/manifests/post_stage_c_eligibility.csv")
AUDIT_PATH = Path("cases/manifests/post_stage_c_historical_target_audit.csv")
AUTHORITY_PATH = Path("cases/manifests/stage_c_post_resolution_authority.csv")


def safe_config_report(config: dict) -> dict:
    return {"contract": "post-stage-c-reconstruction-v2",
            "acquisition_record": "historical-state-acquisition-v2",
            "boundary_record": "historical-information-boundary-v2",
            "transport_retries": config["transport_retries"],
            "github_token": "configured" if config["github_token"] else "not_configured",
            "execution_mode": "sequential", "outcome_inputs_enabled": False,
            "network_during_check_or_dry_run": False}


def output_paths(case_id: str) -> dict[str, str]:
    return {
        "acquisition": f"cases/reconstruction/{case_id}/historical_state_acquisition_v2.json",
        "boundary": f"data/derived/historical_information/{case_id}/historical_information_boundary_v2.json",
    }


def _repository_slug(eligibility: dict[str, str]) -> str:
    parts = urlparse(eligibility["canonical_repository_url"]).path.strip("/").split("/")
    if len(parts) != 2:
        raise ValueError("Canonical repository identity is invalid")
    return "/".join(parts)


def preflight(root: Path) -> tuple[list[dict[str, str]], dict[str, dict[str, str]],
                                   dict[str, dict[str, str]]]:
    pilot = read_csv(root / PILOT_PATH)
    eligibility = {r["case_id"]: r for r in read_csv(root / ELIGIBILITY_PATH)}
    audit = {r["case_id"]: r for r in read_csv(root / AUDIT_PATH)}
    authority = {r["case_id"]: r for r in read_csv(root / AUTHORITY_PATH)}
    if len(pilot) != 8 or tuple(r["case_id"] for r in pilot) != FROZEN_CASES:
        raise ValueError("Frozen v2 pilot population or order mismatch")
    if any(r["pilot_manifest_version"] != PILOT_MANIFEST_VERSION for r in pilot):
        raise ValueError("Frozen v2 pilot version mismatch")
    for row in pilot:
        case_id = row["case_id"]
        if case_id not in eligibility or case_id not in audit or case_id not in authority:
            raise ValueError(f"Missing authoritative pilot input: {case_id}")
        source, auth = eligibility[case_id], authority[case_id]
        if auth["stage_c_processability_status"] != "processable":
            raise ValueError(f"Stage C authority is not processable: {case_id}")
        record = root / source["stage_c_authoritative_record"]
        if not record.is_file() or file_sha256(record) != source["stage_c_authoritative_record_sha256"]:
            raise ValueError(f"Stage C authority hash mismatch: {case_id}")
        if not source["source_linkage_reference"]:
            raise ValueError(f"Approved case linkage missing: {case_id}")
        paths = output_paths(case_id)
        if row["executed"] == "true" and not all((root / p).is_file() for p in paths.values()):
            raise ValueError(f"Executed row lacks persisted v2 result: {case_id}")
        if row["executed"] == "false" and any((root / p).exists() for p in paths.values()):
            raise ValueError(f"Unexecuted row has unsafe partial result: {case_id}")
    return pilot, eligibility, audit


def _snapshot_time(name: str) -> str:
    stem = Path(name).stem.split("_pr_sharings")[0]
    for pattern in ("%Y%m%d_%H%M%S", "%m_%d_%Y_manual"):
        try:
            return datetime.strptime(stem, pattern).replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            pass
    return ""


def _same_instant(left: str, right: str) -> bool:
    try:
        a = datetime.fromisoformat(left.replace("Z", "+00:00")).astimezone(timezone.utc)
        b = datetime.fromisoformat(right.replace("Z", "+00:00")).astimezone(timezone.utc)
        return a == b
    except (ValueError, AttributeError):
        return False


def _claim(case_id: str, level: str, sha: str, source: str, timestamp: str,
           relation: str, linkage: str, status: str, *, rule: str,
           inputs: list[str], relationships: list[str] | None = None,
           cross_validated: bool = False) -> dict:
    claim = {"claim_id": f"{case_id}-{level}-{len(inputs)}-{sha[:12]}",
             "evidence_level": level, "candidate_sha": sha,
             "source_identifier": source, "historical_source_timestamp": timestamp,
             "timestamp_precision": "timestamp" if timestamp else "unavailable",
             "relation_to_tFG": relation, "development_context_linkage": linkage,
             "derivation_rule": rule, "derivation_inputs": inputs,
             "immutable_git_relationships": relationships or [],
             "validation_status": status,
             "evidence_hash": hashlib.sha256((source + timestamp + sha).encode()).hexdigest(),
             "provenance_reference": source, "adequate_provenance": bool(source),
             "cross_validated": cross_validated, "uses_outcome_information": False}
    validate_baseline_claim(claim)
    return claim


def archived_claims(root: Path, case_id: str, audit: dict[str, str]) -> list[dict]:
    if audit["archived_commit_shas_found"] != "yes":
        return []
    snapshot = audit["earliest_archived_snapshot"]
    timestamp = _snapshot_time(snapshot)
    relation = (temporal_relation(timestamp, "timestamp", audit["tFG"], "timestamp")
                if timestamp else "unresolved")
    sources = audit["archived_commit_sha_sources"] or snapshot
    claims = []
    for sha in filter(None, audit["archived_commit_shas"].split(";")):
        claims.append(_claim(case_id, "B4", sha, sources, timestamp, relation,
                             "established" if audit["pr_created_relative_to_tFG"] == "PR_EXISTED_AT_TFG" else "unresolved",
                             "unresolved", rule="archived_pr_commit_membership_lead",
                             inputs=[snapshot, sha]))
    return claims


def current_metadata_claim(case_id: str, source_url: str, sha: str,
                           retrieved_at: str, evidence_ref: str) -> dict:
    return _claim(case_id, "B5", sha, source_url, retrieved_at, "after", "unresolved",
                  "supporting_only", rule="current_pr_base_supporting_only",
                  inputs=[evidence_ref, sha])


def git_parent_probe(repository: str, focal_sha: str, *, run=subprocess.run,
                     timeout: float = 90) -> dict:
    """Validate one focal commit relationship; this is evidence acquisition, not target materialization."""
    remote = f"https://github.com/{repository}.git"
    with tempfile.TemporaryDirectory(prefix="dir-post-c-v2-rel-") as directory:
        run(["git", "init", "--bare", "-q", directory], check=True, capture_output=True, timeout=30)
        fetched = run(["git", "-C", directory, "-c", "credential.helper=", "fetch",
                       "--no-tags", "--depth=2", remote, focal_sha], check=False,
                      capture_output=True, timeout=timeout)
        if fetched.returncode:
            return {"status": "transport_failed", "remote_operations": 1,
                    "requested_sha": focal_sha, "parent_sha": "", "tree_sha": "",
                    "commit_time": ""}
        shown = run(["git", "-C", directory, "show", "-s", "--format=%P", focal_sha],
                    check=False, capture_output=True, timeout=30, text=True)
        parents = shown.stdout.strip().split()
        if shown.returncode or len(parents) != 1:
            return {"status": "relationship_unresolved", "remote_operations": 1,
                    "requested_sha": focal_sha, "parent_sha": "", "tree_sha": "",
                    "commit_time": ""}
        parent = parents[0]
        parent_data = run(["git", "-C", directory, "show", "-s", "--format=%T%n%cI", parent],
                          check=False, capture_output=True, timeout=30, text=True)
        lines = parent_data.stdout.splitlines()
        if parent_data.returncode or len(lines) < 2:
            return {"status": "relationship_unresolved", "remote_operations": 1,
                    "requested_sha": focal_sha, "parent_sha": "", "tree_sha": "",
                    "commit_time": ""}
        return {"status": "validated", "remote_operations": 1,
                "requested_sha": focal_sha, "parent_sha": parent,
                "tree_sha": lines[0].strip(), "commit_time": lines[1].strip()}


def git_materialize(repository: str, sha: str, *, run=subprocess.run,
                    timeout: float = 90) -> dict:
    remote = f"https://github.com/{repository}.git"
    with tempfile.TemporaryDirectory(prefix="dir-post-c-v2-target-") as directory:
        run(["git", "init", "--bare", "-q", directory], check=True, capture_output=True, timeout=30)
        fetched = run(["git", "-C", directory, "-c", "credential.helper=", "fetch",
                       "--no-tags", "--depth=1", remote, sha], check=False,
                      capture_output=True, timeout=timeout)
        if fetched.returncode:
            return {"status": "transport_failed", "remote_operations": 1,
                    "object_type": "", "tree_sha": "", "deterministic_repeat": False}
        obj = run(["git", "-C", directory, "cat-file", "-t", sha], check=False,
                  capture_output=True, timeout=30, text=True)
        tree1 = run(["git", "-C", directory, "show", "-s", "--format=%T", sha], check=False,
                    capture_output=True, timeout=30, text=True)
        tree2 = run(["git", "-C", directory, "show", "-s", "--format=%T", sha], check=False,
                    capture_output=True, timeout=30, text=True)
        valid = obj.returncode == 0 and obj.stdout.strip() == "commit" and tree1.returncode == 0
        return {"status": "validated" if valid else "validation_failed", "remote_operations": 1,
                "object_type": obj.stdout.strip(), "tree_sha": tree1.stdout.strip() if valid else "",
                "deterministic_repeat": valid and tree1.stdout.strip() == tree2.stdout.strip()}


def _atomic_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)
    temporary.replace(path)


def validate_acquisition(record: dict) -> None:
    required = set(json.loads((Path(__file__).resolve().parents[2] / "schemas/historical_state_acquisition_v2.schema.json").read_text())["required"])
    if set(record) != required:
        raise ValueError("V2 acquisition contract mismatch")
    for claim in record["evidence_claims"]:
        validate_baseline_claim(claim)
    if not materialization_allowed(record["target_identity_status"], record["authoritative_R_i_tFG"]):
        if record["materialization_status"] != "not_attempted":
            raise ValueError("Git materialization occurred before authoritative identity")


def validate_boundary(record: dict) -> None:
    required = set(json.loads((Path(__file__).resolve().parents[2] / "schemas/historical_information_boundary_v2.schema.json").read_text())["required"])
    if set(record) != required:
        raise ValueError("V2 boundary contract mismatch")


def _git_with_retries(operation: Callable, repository: str, sha: str, config: dict,
                      sleep: Callable[[float], None]) -> tuple[dict, list[dict]]:
    attempts = []
    result = {}
    for number in range(1, config["transport_retries"] + 2):
        result = operation(repository, sha, timeout=config["timeout"])
        attempts.append({"attempt_number": number, **result})
        if result.get("status") not in {"transport_failed", "timed_out", "rate_limited"}:
            break
        if number <= config["transport_retries"]:
            sleep(min(2 ** (number - 1), 4))
    return result, attempts


def execute_case(root: Path, eligibility: dict[str, str], audit: dict[str, str],
                 config: dict, *, get: Callable = provider_get,
                 archive_loader: Callable = archived_claims,
                 relationship_probe: Callable = git_parent_probe,
                 materializer: Callable = git_materialize,
                 sleep: Callable[[float], None] = time.sleep) -> dict:
    case_id = eligibility["case_id"]
    record = initialize_acquisition_v2(eligibility, audit)
    claims = archive_loader(root, case_id, audit)
    case_dir = root / "cases/reconstruction" / case_id
    if claims:
        retained_archive = {"case_id": case_id,
                            "audit_reference": str(AUDIT_PATH),
                            "snapshot_sources": audit["archived_commit_sha_sources"],
                            "candidate_shas": audit["archived_commit_shas"],
                            "claims": claims}
        archive_path = case_dir / "evidence" / "archive_derivation_leads_v2.json"
        atomic_json(archive_path, retained_archive)
        archive_hash = file_sha256(archive_path)
        for claim in claims:
            claim["provenance_reference"] = str(archive_path.relative_to(root))
            claim["evidence_hash"] = archive_hash
    repository_slug = _repository_slug(eligibility)
    url = f"https://api.github.com/repos/{repository_slug}/pulls/{eligibility['pr_number']}"
    provider_requests = 0; git_operations = 0; result = None
    for number in range(1, config["transport_retries"] + 2):
        result = get(url, config["github_token"], config["timeout"]); provider_requests += 1
        attempt = {"attempt_number": number, "operation": "github_current_pr_metadata",
                   "status": result["status"], "retrieved_at": result["retrieved_at"],
                   "http_status": result["http_status"], "retry": result["status"] in {"rate_limited", "transport_failed", "timed_out", "server_error"}}
        record["attempts"].append(attempt)
        atomic_json(case_dir / "logs" / f"provider_attempt_v2_{number}.json", attempt)
        if not attempt["retry"]: break
        if number <= config["transport_retries"]: sleep(min(2 ** (number - 1), 4))
    assert result is not None
    if result["status"] == "success":
        payload = json.loads(result["body"])
        if payload.get("number") != int(eligibility["pr_number"]):
            raise ValueError("Provider PR identity mismatch")
        created_at, base_sha = payload["created_at"], payload["base"]["sha"]
        if audit["pr_created_at"] and not _same_instant(created_at, audit["pr_created_at"]):
            record["conflicts"].append({"type": "pr_created_at_mismatch",
                                        "retained": audit["pr_created_at"], "provider": created_at})
            pr_exists = "unresolved"
        else:
            pr_exists = classify_pr_existence(created_at, "timestamp", eligibility["tFG"], eligibility["tFG_precision"])
        record["pr"].update(created_at=created_at, existed_by_tFG=pr_exists,
                            component_status={"yes": "available_by_tFG", "no": "unavailable_by_tFG", "unresolved": "unresolved"}[pr_exists])
        evidence = {"source_url": url, "pr_number": payload["number"],
                    "repository": eligibility["repository"], "base_sha": base_sha,
                    "created_at": created_at, "retrieved_at": result["retrieved_at"],
                    "raw_response_sha256": hashlib.sha256(result["body"]).hexdigest()}
        evidence_path = case_dir / "evidence" / "current_pr_metadata_sanitized_v2.json"
        atomic_json(evidence_path, evidence)
        claims.append(current_metadata_claim(case_id, url, base_sha, result["retrieved_at"], str(evidence_path.relative_to(root))))
    else:
        record["operational_reason"] = result["status"]

    # A B4 lead can become B2 only after its own historical linkage and time are established.
    for lead in list(claims):
        if (lead["evidence_level"], lead["validation_status"], lead["relation_to_tFG"],
                lead["development_context_linkage"]) != ("B4", "unresolved", "at_or_before", "established"):
            continue
        probe, probe_attempts = _git_with_retries(relationship_probe, repository_slug,
                                                  lead["candidate_sha"], config, sleep)
        git_operations += sum(a.get("remote_operations", 0) for a in probe_attempts)
        record["attempts"].extend({"operation": "git_relationship_probe", **a}
                                  for a in probe_attempts)
        if probe["status"] == "validated" and probe["parent_sha"]:
            relation = temporal_relation(probe["commit_time"], "timestamp", eligibility["tFG"], eligibility["tFG_precision"])
            claims.append(_claim(case_id, "B2", probe["parent_sha"], lead["source_identifier"],
                                 probe["commit_time"], relation, "established", "validated",
                                 rule="first_parent_of_historically_linked_focal_revision",
                                 inputs=[lead["claim_id"], lead["candidate_sha"]],
                                 relationships=[f"{lead['candidate_sha']}^={probe['parent_sha']}"]))
    resolution = resolve_repository_boundary(claims)
    record["evidence_claims"] = resolution["claims"]
    record["candidate_repository_boundaries"] = list(dict.fromkeys(c["candidate_sha"] for c in claims if c["candidate_sha"]))
    record["target_identity_status"] = resolution["status"]
    record["authoritative_R_i_tFG"] = resolution["authoritative_R_i_tFG"]
    if resolution["status"] == "established":
        chosen = next(c for c in claims if c["candidate_sha"].lower() == record["authoritative_R_i_tFG"])
        record["development_linkage_status"] = chosen["development_context_linkage"]
        record["temporal_applicability_status"] = chosen["relation_to_tFG"]
        record["derivation_chain"] = [{"claim_id": chosen["claim_id"], "rule": chosen["derivation_rule"],
                                        "inputs": chosen["derivation_inputs"], "relationships": chosen["immutable_git_relationships"]}]
        material, material_attempts = _git_with_retries(
            materializer, repository_slug, record["authoritative_R_i_tFG"], config, sleep)
        git_operations += sum(a.get("remote_operations", 0) for a in material_attempts)
        record["attempts"].extend({"operation": "git_target_materialization", **a}
                                  for a in material_attempts)
        if material["status"] == "validated":
            record.update(materialization_status="materialized", object_validation_status="validated",
                          tree_validation_status="validated", tree_identity=material["tree_sha"])
        else:
            record.update(materialization_status="failed", object_validation_status="unresolved",
                          tree_validation_status="unresolved", operational_reason=material["status"])
        record["historical_state_reconstructible"] = reconstructibility_v2(
            target_identity_status=record["target_identity_status"],
            development_linkage_status=record["development_linkage_status"],
            temporal_applicability_status=record["temporal_applicability_status"],
            object_validation_status=record["object_validation_status"],
            materialization_status=record["materialization_status"],
            tree_validation_status=record["tree_validation_status"],
            deterministic_repeat=material.get("deterministic_repeat", False), provenance_retained=True,
            outcome_information_required=False, failure_category=("transport_failed" if material["status"] == "transport_failed" else ""))
    else:
        record["scientific_reason"] = resolution["basis"]
        if resolution["status"] == "ambiguous":
            record["conflicts"] = [{"candidate_shas": sorted({c["candidate_sha"] for c in claims if c["candidate_sha"]})}]
            record["human_adjudication_status"] = "required"
    record["executed"] = True
    if not record["scientific_reason"] or record["scientific_reason"] == "development_baseline_not_yet_assessed":
        record["scientific_reason"] = ("full_v2_chain_validated" if record["historical_state_reconstructible"] == "yes" else resolution["basis"])
    boundary = initialize_boundary_v2(record)
    for key in ("authoritative_R_i_tFG", "target_identity_status", "development_linkage_status",
                "temporal_applicability_status", "materialization_status", "object_validation_status",
                "tree_validation_status", "tree_identity", "historical_state_reconstructible"):
        boundary[key] = record[key]
    boundary["provenance_references"] = [c["provenance_reference"] for c in claims]
    validate_acquisition(record); validate_boundary(boundary)
    paths = output_paths(case_id)
    atomic_json(root / paths["acquisition"], record)
    atomic_json(root / paths["boundary"], boundary)
    return {"case_id": case_id, "record": record, "boundary": boundary,
            "provider_requests": provider_requests, "git_operations": git_operations,
            "paths": paths}


def run_pilot(root: Path, config: dict, **dependencies) -> list[dict]:
    pilot, eligibility, audit = preflight(root)
    results = []
    for row in pilot:
        if row["executed"] == "true":
            continue
        result = execute_case(root, eligibility[row["case_id"]], audit[row["case_id"]],
                              config, **dependencies)
        row["executed"] = "true"
        _atomic_csv(root / PILOT_PATH, list(pilot[0]), pilot)
        results.append(result)
    return results
