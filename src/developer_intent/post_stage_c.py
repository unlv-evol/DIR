"""Deterministic Post-Stage-C v4 temporal and lineage selection."""
from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

CONTRACT = "post-stage-c-reconstruction-v4"
PROCEDURE = "post-stage-c-git-lineage-v4"
ACQUISITION = "historical-state-acquisition-v4"
BOUNDARY = "historical-information-boundary-v4"
ELIGIBILITY_SCHEMA = "post-stage-c-eligibility-manifest-v2"
ELIGIBILITY_CONTRACT = "post-stage-c-eligibility-v2"
ELIGIBILITY_TARGET = "historical_repository_state_at_tFG"


def focal_root_external_parent(commits: list[dict]) -> tuple[str | None, str]:
    """Return the unique parent by which the ordered focal lineage joins its base."""
    if not commits:
        return None, "focal_lineage_empty"
    focal_shas = {c["sha"].lower() for c in commits}
    candidates = []
    for commit in commits:
        external = [p.lower() for p in commit.get("parent_shas", []) if p.lower() not in focal_shas]
        if external:
            candidates.extend(external)
            break
    unique = list(dict.fromkeys(candidates))
    if len(unique) != 1:
        return None, "focal_root_external_parent_ambiguous" if unique else "focal_root_external_parent_missing"
    return unique[0], "unique_focal_root_external_parent"


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else None
    except (TypeError, ValueError):
        return None


def annotate_commit(commit: dict, tfg: str, position: int) -> dict:
    cutoff, author, committer = parse_time(tfg), parse_time(commit.get("author_time")), parse_time(commit.get("committer_time"))
    if cutoff is None:
        raise ValueError("authoritative tFG must be a timezone-aware timestamp")
    effective, basis = (committer, "committer_time") if committer else ((author, "author_time_fallback") if author else (None, "unavailable"))
    relation = lambda value: "unknown" if value is None else ("at_or_before_tfg" if value <= cutoff else "after_tfg")
    if committer is None and author is not None:
        sensitivity = "committer_missing_author_used"
    elif author is None or committer is None:
        sensitivity = "not_applicable"
    else:
        sensitivity = "same_side_of_tfg" if relation(author) == relation(committer) else "crosses_tfg"
    return {"sha": commit["sha"].lower(), "parent_shas": [p.lower() for p in commit.get("parent_shas", [])],
            "tree_sha": commit.get("tree_sha", "").lower(), "author_time": commit.get("author_time"),
            "committer_time": commit.get("committer_time"), "effective_time": effective.isoformat() if effective else None,
            "temporal_basis": basis, "author_time_relation": relation(author),
            "committer_time_relation": relation(committer), "effective_time_relation": relation(effective),
            "author_time_sensitivity": sensitivity, "position": position,
            "repository": commit.get("repository", ""), "pr_number": commit.get("pr_number"),
            "provenance": commit.get("provenance", {})}


def select_from_lineage(commits: list[dict], tfg: str) -> dict:
    annotated = [annotate_commit(c, tfg, i + 1) for i, c in enumerate(commits)]
    by_sha = {c["sha"]: c for c in annotated}
    anomalies = []
    for child in annotated:
        for parent_sha in child["parent_shas"]:
            parent = by_sha.get(parent_sha)
            if parent and parent["effective_time_relation"] == "after_tfg" and child["effective_time_relation"] == "at_or_before_tfg":
                anomalies.append(f"ancestor_after_tfg_descendant_at_or_before_tfg:{parent_sha}:{child['sha']}")
    qualified = [c for c in annotated if c["effective_time_relation"] == "at_or_before_tfg"]
    maximal = [c for c in qualified if not any(c["sha"] in other["parent_shas"] for other in qualified)]
    if len(maximal) > 1:
        anomalies.append("non_linear_or_ambiguous_qualified_tips:" + ",".join(c["sha"] for c in maximal))
    if anomalies:
        return {"commits": annotated, "selected": None, "first_post_tfg": None,
                "temporal_consistency": "temporal_or_lineage_ambiguous", "reasons": anomalies}
    selected = maximal[0] if maximal else None
    first_post = next((c for c in annotated[(selected["position"] if selected else 0):]
                       if c["effective_time_relation"] == "after_tfg"), None)
    relationship = "not_applicable"
    if selected and first_post:
        frontier, visited = [first_post["sha"]], set()
        while frontier:
            current = frontier.pop()
            if current in visited: continue
            visited.add(current)
            node = by_sha.get(current)
            if node: frontier.extend(node["parent_shas"])
        relationship = "ancestor" if selected["sha"] in visited else "not_established"
    return {"commits": annotated, "selected": selected, "first_post_tfg": first_post,
            "selected_to_first_post_relationship": relationship,
            "temporal_consistency": "consistent", "reasons": []}


def choose_reconstruction(focal: list[dict], base: list[dict] | None, tfg: str,
                          base_route: str = "") -> dict:
    focal_result = select_from_lineage(focal, tfg)
    if focal_result["temporal_consistency"] != "consistent":
        return {"status": "unresolved", "path": "focal", "reason": "temporal_or_lineage_ambiguous",
                "focal": focal_result, "base": None, "selected": None}
    if focal_result["selected"]:
        return {"status": "reconstructed_focal_state", "path": "focal", "reason": "",
                "focal": focal_result, "base": None, "selected": focal_result["selected"]}
    if not base or not base_route:
        reason = "no_usable_temporal_information" if not base else "applicable_base_lineage_unresolved"
        return {"status": "unresolved", "path": "base", "reason": reason,
                "focal": focal_result, "base": None, "selected": None}
    base_result = select_from_lineage(base, tfg)
    if base_result["temporal_consistency"] != "consistent":
        return {"status": "unresolved", "path": "base", "reason": "temporal_or_lineage_ambiguous",
                "focal": focal_result, "base": base_result, "selected": None}
    if not base_result["selected"]:
        return {"status": "unresolved", "path": "base", "reason": "no_usable_temporal_information",
                "focal": focal_result, "base": base_result, "selected": None}
    return {"status": "reconstructed_base_state", "path": "base", "reason": "",
            "focal": focal_result, "base": base_result, "selected": base_result["selected"]}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def authority(root: Path) -> dict[str, dict[str, str]]:
    return {r["case_id"]: r for r in read_csv(root / "cases/manifests/stage_c_post_resolution_authority.csv")
            if r["stage_c_processability_status"] == "processable"}


def validate_record(record: dict) -> None:
    if record.get("record_version") != ACQUISITION or record.get("reconstruction_contract") != CONTRACT:
        raise ValueError("v4 version mismatch")
    if record.get("reconstruction_status") not in {"reconstructed_focal_state", "reconstructed_base_state", "unresolved"}:
        raise ValueError("invalid v4 reconstruction status")
    if record["reconstruction_status"].startswith("reconstructed_"):
        selected, material = record.get("selected_state", {}), record.get("materialization", {})
        if len(selected.get("commit_sha", "")) != 40 or len(selected.get("tree_sha", "")) != 40:
            raise ValueError("reconstruction lacks exact commit/tree identity")
        if material.get("status") != "materialized" or not material.get("complete_recursive_tree"):
            raise ValueError("reconstruction lacks complete exact materialization")
    if record.get("historical_observability") not in {"confirmed", "not_confirmed"}:
        raise ValueError("observability must remain explicit and orthogonal")
    forbidden = {"commit_message", "patch", "diff", "files", "contents", "pa_pn_stratum", "outcome_class"}
    def walk(value):
        if isinstance(value, dict):
            if forbidden.intersection(k.lower() for k in value): raise ValueError("prohibited content/outcome field in v4")
            for child in value.values(): walk(child)
        elif isinstance(value, list):
            for child in value: walk(child)
    walk(record)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def validate_eligibility_schema(schema: dict) -> None:
    """Validate the frozen structural constants needed by eligibility v2."""
    required = set(schema.get("required", []))
    properties = schema.get("properties", {})
    if schema.get("additionalProperties") is not False or required != set(properties):
        raise ValueError("eligibility schema fields are not exact")
    expected = {
        "manifest_schema_version": ELIGIBILITY_SCHEMA,
        "reconstruction_contract_version": CONTRACT,
        "reconstruction_procedure_version": PROCEDURE,
        "eligibility_contract_version": ELIGIBILITY_CONTRACT,
        "methodology_version": "dir-tfg-v2",
        "reconstruction_target_rule": ELIGIBILITY_TARGET,
    }
    for field, value in expected.items():
        if properties.get(field, {}).get("const") != value:
            raise ValueError(f"eligibility schema has wrong {field}")
    if properties.get("reconstruction_status", {}).get("enum") != [
        "reconstructed_focal_state", "reconstructed_base_state", "unresolved"
    ]:
        raise ValueError("eligibility schema has wrong reconstruction outcomes")


def validate_eligibility_record(record: dict[str, str], schema: dict) -> None:
    """Validate one CSV eligibility row against the v2 logical contract."""
    validate_eligibility_schema(schema)
    required, properties = set(schema["required"]), schema["properties"]
    if set(record) != required:
        raise ValueError("eligibility record fields differ from schema")
    for field, spec in properties.items():
        if "$ref" in spec:
            prefix = "#/$defs/"
            if not spec["$ref"].startswith(prefix):
                raise ValueError(f"{field}: unsupported schema reference")
            spec = schema["$defs"][spec["$ref"][len(prefix):]]
        value = record[field]
        if "const" in spec and value != spec["const"]:
            raise ValueError(f"{field}: wrong constant")
        if "enum" in spec and value not in spec["enum"]:
            raise ValueError(f"{field}: unsupported value {value!r}")
        if spec.get("minLength", 0) and not value:
            raise ValueError(f"{field}: required value missing")
        if "pattern" in spec and not re.fullmatch(spec["pattern"], value):
            raise ValueError(f"{field}: invalid value")
    if record["historical_state_reconstructible"] == "yes":
        if record["reconstruction_status"] not in {"reconstructed_focal_state", "reconstructed_base_state"}:
            raise ValueError("reconstructible case lacks an accepted outcome")
        if not record["authoritative_target_identifier"]:
            raise ValueError("reconstructible case lacks selected commit")
    expected_final = (
        "eligible" if record["first_generation_boundary_identifiable"] == "yes"
        and record["historical_state_reconstructible"] == "yes"
        else "excluded" if "no" in {
            record["first_generation_boundary_identifiable"],
            record["historical_state_reconstructible"],
        } else "pending_resolution"
    )
    if record["final_scientific_eligibility"] != expected_final:
        raise ValueError("final eligibility is inconsistent with criteria")
