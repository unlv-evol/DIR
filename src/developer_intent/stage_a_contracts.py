"""Explicit CSV-to-logical-record validation for stable Stage A artifacts."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID

from .case_mapping import MAPPING_FIELDS, MAPPING_SCHEMA_VERSION
from .screening import (FIELDS, conversation_identity, github_identity)
from .screening_checks import correspondence

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schemas"
SCREENING_SCHEMA = "dir_screening_v9.schema.json"
MAPPING_SCHEMA = "dir_case_mapping_v1.schema.json"
REVIEW_SCHEMA = "correspondence_review_v1.schema.json"
NULLABLE = "null"


def _schema(name: str) -> dict:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def _timestamp(value: str, field: str) -> datetime:
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field}: invalid timestamp") from exc
    if result.tzinfo is None:
        raise ValueError(f"{field}: timestamp needs timezone")
    return result


def _parse_cell(field: str, raw: str, spec: dict):
    if not isinstance(raw, str):
        raise ValueError(f"{field}: missing CSV cell")
    kinds = spec.get("type", "string")
    kinds = [kinds] if isinstance(kinds, str) else kinds
    if raw == "":
        if NULLABLE in kinds:
            return None
        raise ValueError(f"{field}: blank value is not permitted")
    if "boolean" in kinds:
        if raw not in {"true", "false"}:
            raise ValueError(f"{field}: boolean must be true or false")
        return raw == "true"
    if "integer" in kinds:
        if not re.fullmatch(r"0|[1-9][0-9]*", raw):
            raise ValueError(f"{field}: invalid nonnegative integer")
        return int(raw)
    if spec.get("format") == "date-time":
        return _timestamp(raw, field)
    return raw


def _json_value(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _validate_properties(record: dict, schema: dict) -> None:
    required = set(schema["required"])
    properties = schema["properties"]
    if not required <= set(record):
        raise ValueError("Missing required fields: " + ", ".join(sorted(required - set(record))))
    if schema.get("additionalProperties") is False and set(record) - set(properties):
        raise ValueError("Unexpected fields: " + ", ".join(sorted(set(record) - set(properties))))
    for field, spec in properties.items():
        if field not in record:
            continue
        value = record[field]
        kinds = spec.get("type")
        if kinds is not None:
            kinds = [kinds] if isinstance(kinds, str) else kinds
            actual = ("null" if value is None else "boolean" if isinstance(value, bool)
                      else "integer" if isinstance(value, int) else "string"
                      if isinstance(value, (str, date, datetime)) else "unsupported")
            if actual not in kinds:
                raise ValueError(f"{field}: expected {kinds}, got {actual}")
        comparable = _json_value(value)
        if "const" in spec and comparable != spec["const"]:
            raise ValueError(f"{field}: wrong contract version or constant")
        if "enum" in spec and comparable not in spec["enum"]:
            raise ValueError(f"{field}: unsupported value {comparable!r}")
        if value is None:
            continue
        if "minLength" in spec and len(comparable) < spec["minLength"]:
            raise ValueError(f"{field}: empty or too short")
        if "minimum" in spec and comparable < spec["minimum"]:
            raise ValueError(f"{field}: below minimum")
        if "pattern" in spec and not re.fullmatch(spec["pattern"], comparable):
            raise ValueError(f"{field}: invalid identifier or object reference")
        if spec.get("format") == "date-time":
            _timestamp(comparable, field)


def _parse_csv_row(row: dict, schema: dict) -> dict:
    record = {field: _parse_cell(field, row[field], spec)
              for field, spec in schema["properties"].items()}
    if "conversation_start" in record and record["conversation_start"] is not None:
        precision = record["temporal_precision"]
        if precision == "date":
            try:
                record["conversation_start"] = date.fromisoformat(record["conversation_start"])
            except ValueError as exc:
                raise ValueError("conversation_start: invalid date") from exc
        elif precision == "timestamp":
            record["conversation_start"] = _timestamp(record["conversation_start"],
                                                       "conversation_start")
        else:
            raise ValueError("conversation_start: temporal precision required")
    return record


def _require_url_shape(record: dict, mapping: bool = False) -> None:
    # Source URLs are retained even if malformed, since such rows may be
    # excluded. Validate parsed/canonical identities only when present.
    if record.get("conversation_id") is not None:
        try:
            UUID(record["conversation_id"])
        except ValueError as exc:
            raise ValueError("conversation_id: invalid share identifier") from exc
    expected_case_id = "CASE_" + hashlib.sha256(
        record["source_case_id"].encode("utf-8")).hexdigest()[:12].upper()
    if record["case_id"] != expected_case_id:
        raise ValueError("case_id differs from stable source Case ID")
    conversation = conversation_identity(record["conversation_url"])
    if record.get("conversation_id") != conversation:
        raise ValueError("conversation_id differs from source conversation URL")
    pr = github_identity(record["pr_url"])
    if not mapping:
        expected_repository, expected_number = (pr if pr else (None, None))
        if (record["repository"] != expected_repository
                or record["pr_number"] != (int(expected_number) if expected_number else None)):
            raise ValueError("PR identity differs from source PR URL")
    canonical = record.get("canonical_pr_url")
    if canonical:
        parsed = urlparse(canonical)
        if (parsed.scheme != "https" or parsed.netloc.lower() != "github.com"
                or not re.fullmatch(r"/[^/]+/[^/]+/pull/[0-9]+/?", parsed.path)):
            raise ValueError("canonical_pr_url: invalid GitHub PR URL")
    if not mapping and record["project_history_access_object"] is not None:
        if not re.fullmatch(r"[0-9a-fA-F]{40,64}", record["project_history_access_object"]):
            raise ValueError("project_history_access_object: invalid SHA")


def _screening_invariants(row: dict) -> None:
    checks = ("conversation_available", "temporal_anchor_available",
              "first_generation_boundary_identifiable", "pr_conversation_match",
              "project_history_accessible", "historical_state_reconstructible")
    status = row["eligibility_status"]
    pending_tokens = set((row["pending_reason"] or "").split(";")) - {""}
    expected_pending = {
        field + "_unresolved" for field in checks
        if field != "temporal_anchor_available"
        if row[field] in {"unresolved", "unavailable"}
    }
    if row["temporal_anchor_available"] == "unresolved":
        expected_pending.add("temporal_anchor_unresolved")
    if row["source_linkage_status"] == "unresolved":
        expected_pending.add("source_linkage_unresolved")
    if not expected_pending <= pending_tokens:
        raise ValueError("pending_reason omits unresolved required checks")
    if pending_tokens - expected_pending - {"pr_source_unavailable"}:
        raise ValueError("pending_reason contains unsupported reason")
    if status == "eligible":
        if (row["eligible"] is not True or row["pending_reason"] is not None
                or row["exclusion_reason"] is not None
                or any(row[field] != "yes" for field in checks)
                or row["source_linkage_status"] != "established"
                or row["duplicate_status"] != "unique"
                or row["case_integrity_status"] != "ok"):
            raise ValueError("eligible row has unresolved or failed required checks")
    elif status == "pending_resolution":
        if (row["eligible"] is not None or not pending_tokens
                or row["exclusion_reason"]):
            raise ValueError("pending_resolution needs blank eligible and pending reason")
    elif status == "excluded":
        if row["eligible"] is not False or not row["exclusion_reason"]:
            raise ValueError("excluded row needs false eligible and exclusion reason")
    if (row["stage_b_readiness_status"] == "ready_for_stage_b") != (status == "eligible"):
        raise ValueError("Stage B production readiness requires scientific eligibility")
    expected_readiness_reason = ("scientifically_eligible" if status == "eligible" else
                                 "scientific_screening_not_eligible")
    if row["stage_b_readiness_reason"] != expected_readiness_reason:
        raise ValueError("Stage B readiness reason differs from scientific status")
    if row["source_linkage_status"] == "conflicting" and status != "excluded":
        raise ValueError("Conflicting source linkage must exclude and block")
    if row["pr_conversation_match"] in {"yes", "no"}:
        for field in ("source", "reviewer", "timestamp", "version", "evidence_ref", "reason"):
            if row["pr_conversation_match_" + field] is None:
                raise ValueError("pr_conversation_match: missing Stage A review provenance")
        if (row["pr_conversation_match"] == "yes"
                and row["pr_conversation_match_source"] in {
                    "source_index_pair_only", "text_similarity_only", "outcome_class",
                    "final_diff", "integrated_implementation"}):
            raise ValueError("Unsupported positive correspondence basis")
    if row["project_history_accessible"] in {"yes", "no"}:
        expected = ("commit_object_retrieved" if row["project_history_accessible"] == "yes"
                    else "repository_inaccessible")
        if (row["project_history_access_mechanism"] != "git_fetch_commit_object"
                or row["project_history_access_status"] != expected
                or row["project_history_access_repository"] is None
                or row["project_history_access_object"] is None
                or row["project_history_access_source"] != "PR base_sha"):
            raise ValueError("project_history_accessible: missing probe provenance")
        if row["project_history_accessible"] == "no" and not row["project_history_access_reason"]:
            raise ValueError("project_history_accessible no needs failure reason")
    if row["temporal_anchor_available"] == "yes" and row["conversation_start"] is None:
        raise ValueError("temporal anchor yes needs conversation_start")
    prompts = row["developer_prompts"]
    pattern = ("single_developer_prompt" if prompts == 1 else
               "multiple_developer_prompts" if prompts is not None and prompts > 1 else
               "unavailable")
    if row["conversation_turn_pattern"] != pattern:
        raise ValueError("conversation_turn_pattern differs from developer_prompts")
    if all(row[field] is not None for field in ("additions", "deletions", "changed_lines")):
        if row["changed_lines"] != row["additions"] + row["deletions"]:
            raise ValueError("changed_lines differs from additions plus deletions")


def parse_screening_row(row: dict) -> dict:
    schema = _schema(SCREENING_SCHEMA)
    if set(row) != set(FIELDS):
        raise ValueError(f"Screening row does not have the {len(FIELDS)}-field v9 contract")
    record = _parse_csv_row(row, schema)
    _validate_properties(record, schema)
    _require_url_shape(record)
    _screening_invariants(record)
    return record


def parse_mapping_row(row: dict) -> dict:
    schema = _schema(MAPPING_SCHEMA)
    if set(row) != set(MAPPING_FIELDS):
        raise ValueError("Case mapping row differs from v1 contract")
    record = _parse_csv_row(row, schema)
    _validate_properties(record, schema)
    _require_url_shape(record, mapping=True)
    return record


def validate_csv(path: Path, kind: str) -> list[dict]:
    if kind not in {"screening", "mapping"}:
        raise ValueError("Unknown Stage A artifact kind")
    fields = FIELDS if kind == "screening" else MAPPING_FIELDS
    parser = parse_screening_row if kind == "screening" else parse_mapping_row
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != list(fields):
            raise ValueError(f"{kind} CSV header or field order differs from contract")
        return [parser(row) for row in reader]


def validate_stage_a_outputs(screened_path: Path, eligible_path: Path,
                             mapping_path: Path) -> tuple[list[dict], list[dict], list[dict]]:
    """Validate each artifact and the producer's between-artifact relationships."""
    screened = validate_csv(screened_path, "screening")
    eligible = validate_csv(eligible_path, "screening")
    mapping = validate_csv(mapping_path, "mapping")
    if len({row["case_id"] for row in screened}) != len(screened):
        raise ValueError("Duplicate case ID in screened manifest")
    by_case = {row["case_id"]: row for row in screened}
    expected_eligible = {case: row for case, row in by_case.items()
                         if row["eligibility_status"] == "eligible"}
    if (len({row["case_id"] for row in eligible}) != len(eligible)
            or {row["case_id"]: row for row in eligible} != expected_eligible):
        raise ValueError("Eligible manifest differs from confirmed screened cases")
    if (len(mapping) != len(screened)
            or len({row["case_id"] for row in mapping}) != len(mapping)):
        raise ValueError("Case mapping count differs from screened manifest")
    for row in mapping:
        screened_row = by_case.get(row["case_id"])
        if screened_row is None or any(row[field] != screened_row[field] for field in (
                "case_id", "source_case_id", "pr_url", "Outcome_Class",
                "conversation_id", "conversation_url")):
            raise ValueError("Case mapping identity differs from screened manifest")
    return screened, eligible, mapping


def validate_correspondence_review(review: dict, source: dict) -> dict:
    schema = _schema(REVIEW_SCHEMA)
    _validate_properties(review, schema)
    _timestamp(review["timestamp"], "timestamp")
    expected_case_id = "CASE_" + hashlib.sha256(
        source["Case ID"].strip().encode("utf-8")).hexdigest()[:12].upper()
    result = correspondence({"correspondence_review": review}, source, expected_case_id)
    if result["judgment"] != review["judgment"]:
        raise ValueError("Correspondence review judgment differs")
    return result
