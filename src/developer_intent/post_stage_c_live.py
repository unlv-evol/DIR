"""Sequential live execution for the frozen eight-case Post-Stage-C pilot."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

from .post_stage_c import (
    ATTEMPT_RECORD_VERSION, ELIGIBILITY_CONTRACT_VERSION, HISTORICAL_INDEX_VERSION,
    MANIFEST_SCHEMA_VERSION, METHODOLOGY_VERSION, PILOT_MANIFEST_VERSION,
    RECONSTRUCTION_CONTRACT_VERSION, file_sha256, initialize_acquisition_record,
    initialize_historical_index, read_csv, resolve_target_identity,
    temporal_relation_to_tfg, validate_eligibility_row, validate_target_identity_claim,
    write_csv,
)
from .screening_config import _read_env

FROZEN_CASES = (
    "CASE_97AFC2022473", "CASE_F93FFAA22B9B", "CASE_85AD863F8290",
    "CASE_BFB2599E145D", "CASE_CE4BF3CB944D", "CASE_F13F98792012",
    "CASE_F7BED13B8119", "CASE_EE7F13CD9FB7",
)
TRANSIENT = {"rate_limited", "transport_failed", "timed_out", "server_error"}
SCHEMA_ROOT = Path(__file__).resolve().parents[2] / "schemas"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def load_live_config(root: Path, *, environ: dict[str, str] | None = None) -> dict:
    values = {**_read_env(root / ".env"), **dict(os.environ if environ is None else environ)}
    timeout = float(values.get("DIR_POST_C_TIMEOUT", "30"))
    retries = int(values.get("DIR_POST_C_TRANSPORT_RETRIES", "2"))
    if timeout <= 0 or retries < 0 or retries > 2:
        raise ValueError("Post-C timeout must be positive and transport retries must be 0..2")
    return {"github_token": values.get("GITHUB_TOKEN") or None,
            "timeout": timeout, "transport_retries": retries}


def safe_config_report(config: dict) -> dict:
    return {
        "reconstruction_contract_version": RECONSTRUCTION_CONTRACT_VERSION,
        "eligibility_contract_version": ELIGIBILITY_CONTRACT_VERSION,
        "methodology_version": METHODOLOGY_VERSION,
        "attempt_record_version": ATTEMPT_RECORD_VERSION,
        "historical_index_version": HISTORICAL_INDEX_VERSION,
        "transport_retries": config["transport_retries"],
        "github_token": "configured" if config["github_token"] else "not_configured",
        "target_selection_inputs": "identity_and_temporal_provenance_only",
        "outcome_inputs_enabled": False,
    }


def preflight(root: Path, *, require_unexecuted: bool = True
              ) -> tuple[list[dict[str, str]], dict[str, dict[str, str]]]:
    pilot = read_csv(root / "cases/manifests/post_stage_c_reconstruction_pilot.csv")
    eligibility = {r["case_id"]: r for r in read_csv(
        root / "cases/manifests/post_stage_c_eligibility.csv")}
    if len(pilot) != 8 or tuple(r["case_id"] for r in pilot) != FROZEN_CASES:
        raise ValueError("Frozen pilot population or order mismatch")
    if {r["pa_pn_stratum"] for r in pilot} != {"PA", "PN"} or sum(
            r["pa_pn_stratum"] == "PA" for r in pilot) != 4:
        raise ValueError("Frozen pilot must contain four PA and four PN cases")
    if require_unexecuted and any(r["reconstruction_executed"] != "false" for r in pilot):
        raise ValueError("Live pilot requires eight unexecuted rows")
    for case_id in FROZEN_CASES:
        if case_id not in eligibility:
            raise ValueError(f"Pilot case absent from Post-C eligibility: {case_id}")
        validate_eligibility_row(eligibility[case_id], root=root)
    return pilot, eligibility


def _provider_url(row: dict[str, str]) -> str:
    parts = urlparse(row["canonical_repository_url"]).path.strip("/").split("/")
    if len(parts) != 2:
        raise ValueError("Canonical repository URL cannot form provider API URL")
    return f"https://api.github.com/repos/{parts[0]}/{parts[1]}/pulls/{row['pr_number']}"


def provider_get(url: str, token: str | None, timeout: float) -> dict:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "DIR-post-stage-c/1"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
            return {"status": "success", "http_status": response.status, "body": body,
                    "retrieved_at": utc_now(), "final_url": response.geturl()}
    except urllib.error.HTTPError as exc:
        remaining = exc.headers.get("X-RateLimit-Remaining") if exc.headers else None
        if exc.code == 429 or (exc.code == 403 and remaining == "0"):
            status = "rate_limited"
        elif exc.code == 401:
            status = "authentication_blocked"
        elif exc.code == 404:
            status = "repository_unavailable"
        elif exc.code in {500, 502, 503, 504}:
            status = "server_error"
        else:
            status = "transport_failed"
        return {"status": status, "http_status": exc.code, "body": b"",
                "retrieved_at": utc_now(), "final_url": url}
    except TimeoutError:
        return {"status": "timed_out", "http_status": 0, "body": b"",
                "retrieved_at": utc_now(), "final_url": url}
    except (urllib.error.URLError, OSError):
        return {"status": "transport_failed", "http_status": 0, "body": b"",
                "retrieved_at": utc_now(), "final_url": url}


def _relative(root: Path, path: Path) -> str:
    return str(path.relative_to(root))


def _attempt(number: int, started: str, result: dict, url: str, case_dir: Path,
             root: Path) -> dict:
    log_path = case_dir / "logs" / f"provider_attempt_{number}.json"
    log = {"attempt_number": number, "url": url, "status": result["status"],
           "http_status": result["http_status"], "retrieved_at": result["retrieved_at"]}
    atomic_json(log_path, log)
    return {
        "attempt_id": f"provider-{number:02d}", "attempt_number": number,
        "started_at": started, "completed_at": result["retrieved_at"],
        "acquisition_source": "github_current_pr_api",
        "operations": [f"GET {url}"], "exit_status": 0 if result["status"] == "success" else 1,
        "stdout_ref": _relative(root, log_path), "stderr_ref": "",
        "retrieval_timestamp": result["retrieved_at"],
        "failure_category": "" if result["status"] == "success" else result["status"],
        "retry_disposition": ("not_applicable" if result["status"] == "success" else
                              "retry_allowed" if result["status"] in TRANSIENT and number < 3
                              else "retry_exhausted" if result["status"] in TRANSIENT
                              else "retry_prohibited"),
    }


def validate_acquisition_record(record: dict) -> None:
    required = set(json.loads((SCHEMA_ROOT / "historical_state_acquisition_v1.schema.json").read_text())[
        "required"])
    if set(record) != required:
        raise ValueError("Acquisition record top-level contract mismatch")
    if record["attempt_record_version"] != ATTEMPT_RECORD_VERSION:
        raise ValueError("Acquisition record version mismatch")
    if len(record["attempts"]) > 3:
        raise ValueError("Acquisition retry bound exceeded")
    for claim in record["target_selection"]["historical_identity_evidence"]:
        validate_target_identity_claim(claim)
    if record["target_selection"]["identity_status"] != "established" and any(
            [record["object_validation"]["object_sha"],
             record["object_validation"]["materialized_state_identifier"]]):
        raise ValueError("Materialization cannot promote or precede historical target identity")


def validate_historical_index(index: dict) -> None:
    required = set(json.loads((SCHEMA_ROOT / "historical_information_index_v1.schema.json").read_text())[
        "required"])
    if set(index) != required or index["historical_index_version"] != HISTORICAL_INDEX_VERSION:
        raise ValueError("Historical index contract mismatch")
    for claim in index["target_identity_claims"]:
        validate_target_identity_claim(claim)


def execute_case(root: Path, eligibility: dict[str, str], pilot_row: dict[str, str],
                 config: dict, *, get: Callable = provider_get,
                 sleep: Callable[[float], None] = time.sleep) -> dict:
    case_id = eligibility["case_id"]
    case_dir = root / "cases/reconstruction" / case_id
    index_dir = root / "data/derived/historical_information" / case_id
    record = initialize_acquisition_record(eligibility)
    index = initialize_historical_index(eligibility)
    url = _provider_url(eligibility)
    result = None
    for number in range(1, config["transport_retries"] + 2):
        started = utc_now()
        result = get(url, config["github_token"], config["timeout"])
        record["attempts"].append(_attempt(number, started, result, url, case_dir, root))
        if result["status"] not in TRANSIENT:
            break
        if number <= config["transport_retries"]:
            sleep(min(2 ** (number - 1), 4))
    assert result is not None
    if result["status"] == "success":
        try:
            payload = json.loads(result["body"])
            base_sha = payload["base"]["sha"]
            created_at = payload["created_at"]
            if payload.get("number") != int(eligibility["pr_number"]):
                raise ValueError("Provider PR identity mismatch")
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            result["status"] = "validation_failed"
        else:
            evidence_path = case_dir / "evidence" / "current_pr_metadata_sanitized.json"
            sanitized = {"source_url": url, "pr_number": payload["number"],
                         "repository": eligibility["repository"], "base_sha": base_sha,
                         "created_at": created_at, "updated_at": payload.get("updated_at", ""),
                         "retrieved_at": result["retrieved_at"],
                         "raw_response_sha256": hashlib.sha256(result["body"]).hexdigest()}
            atomic_json(evidence_path, sanitized)
            claim = {
                "claim_id": "current-pr-base", "evidence_level": "level_4_present_day_pr_metadata",
                "evidence_source_type": "current_provider_pr_metadata",
                "evidence_source_identifier": url,
                "evidence_historical_timestamp": result["retrieved_at"],
                "evidence_timestamp_precision": "timestamp",
                "evidence_relation_to_tFG": "after",
                "retrieval_timestamp": result["retrieved_at"],
                "evidence_hash": sanitized["raw_response_sha256"],
                "provenance_reference": _relative(root, evidence_path),
                "asserted_base_sha": base_sha,
                "evidence_status": "supporting_only", "adequate_provenance": True,
                "cross_validated": False,
            }
            resolution = resolve_target_identity([claim])
            record["target_selection"]["historical_identity_evidence"] = resolution["claims"]
            record["target_selection"]["identity_status"] = resolution["status"]
            record["target_selection"]["identity_basis"] = resolution["basis"]
            record["target_selection"]["candidate_identifiers"] = list(dict.fromkeys(
                record["target_selection"]["candidate_identifiers"] + [base_sha]))
            record["target_selection"]["authoritative_identifier"] = ""
            index["target_identity_claims"] = resolution["claims"]
            relation = temporal_relation_to_tfg(
                {"value": created_at, "precision": "timestamp"},
                {"value": eligibility["tFG"], "precision": eligibility["tFG_precision"]})
            index["components"]["pr"] = {"status": "available" if relation == "at_or_before"
                                                   else "unavailable" if relation == "after"
                                                   else "unresolved",
                "items": [{"stable_identifier": f"{eligibility['repository']}#{eligibility['pr_number']}",
                           "source_type": "pull_request", "source": url,
                           "historical_timestamp": created_at, "timestamp_precision": "timestamp",
                           "temporal_relation_to_tFG": relation,
                           "retrieval_timestamp": result["retrieved_at"],
                           "provenance_reference": _relative(root, evidence_path),
                           "availability_status": "available" if relation == "at_or_before"
                                                  else "unavailable" if relation == "after"
                                                  else "unresolved"}]}
            record["components"]["pr"] = {
                "status": index["components"]["pr"]["status"],
                "evidence_refs": [_relative(root, evidence_path)]}
            record["components"]["repository"]["status"] = "unresolved"
            record.update(reconstruction_status="unresolved",
                          failure_category="temporal_relation_unresolved",
                          failure_reason="present_day_pr_base_has_no_qualifying_historical_identity_evidence",
                          retry_disposition="not_applicable",
                          historical_state_reconstructible="unresolved",
                          scientific_basis="historical_target_identity_not_established; materialization_not_permitted")
    if result["status"] != "success":
        category = result["status"]
        if category == "server_error":
            category = "transport_failed"
        record["target_selection"]["identity_status"] = "unresolved"
        record["target_selection"]["identity_basis"] = "current_provider_metadata_unavailable"
        record["components"]["repository"]["status"] = "unresolved"
        record["components"]["pr"]["status"] = "unresolved"
        record.update(reconstruction_status="unresolved", failure_category=category,
                      failure_reason="current_provider_metadata_acquisition_failed",
                      retry_disposition=record["attempts"][-1]["retry_disposition"],
                      historical_state_reconstructible="unresolved",
                      scientific_basis="infrastructure_failure_is_not_scientific_nonreconstructibility")
    validate_acquisition_record(record)
    validate_historical_index(index)
    record_path = case_dir / "historical_state_acquisition_v1.json"
    index_path = index_dir / "historical_information_index_v1.json"
    atomic_json(record_path, record)
    atomic_json(index_path, index)
    eligibility.update(
        candidate_target_identifier=(record["target_selection"]["candidate_identifiers"][-1]
                                     if record["target_selection"]["candidate_identifiers"] else ""),
        authoritative_target_identifier=record["target_selection"]["authoritative_identifier"],
        target_identity_status=record["target_selection"]["identity_status"],
        target_identity_basis=record["target_selection"]["identity_basis"],
        historical_availability_status="unresolved", historical_availability_basis="",
        historical_state_reconstructible="unresolved",
        repository_component_status=record["components"]["repository"]["status"],
        pr_component_status=record["components"]["pr"]["status"],
        reconstruction_status=record["reconstruction_status"],
        reconstruction_attempt_id=record["attempts"][-1]["attempt_id"],
        reconstruction_evidence_ref=_relative(root, index_path),
        reconstruction_log_ref=_relative(root, record_path),
        failure_category=record["failure_category"], failure_reason=record["failure_reason"],
        retry_disposition=record["retry_disposition"],
        remaining_criteria_status="historical_state_reconstructible_unresolved",
        final_scientific_eligibility="pending_resolution",
        adjudication_required="false",
        notes="Live pilot attempted; historical target identity remains unresolved.")
    validate_eligibility_row(eligibility, root=root)
    pilot_row["reconstruction_executed"] = "true"
    return {"case_id": case_id, "record_path": _relative(root, record_path),
            "index_path": _relative(root, index_path),
            "provider_requests": len(record["attempts"]), "git_operations": 0,
            "record": record, "index": index}


def run_pilot(root: Path, config: dict, *, get: Callable = provider_get,
              sleep: Callable[[float], None] = time.sleep) -> list[dict]:
    pilot, eligibility = preflight(root)
    results = []
    for pilot_row in pilot:
        result = execute_case(root, eligibility[pilot_row["case_id"]], pilot_row, config,
                              get=get, sleep=sleep)
        results.append(result)
        write_csv(root / "cases/manifests/post_stage_c_eligibility.csv",
                  tuple(eligibility[next(iter(eligibility))]), list(eligibility.values()))
        write_csv(root / "cases/manifests/post_stage_c_reconstruction_pilot.csv",
                  tuple(pilot[0]), pilot)
    return results
