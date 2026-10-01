"""Deterministic, resumable, offline Stage B corpus orchestration."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from .screening_http import HttpClient
from .stage_b import (canonical_json_hash, existing_package_status, legacy_cache_paths,
                      output_paths, persist_stage_b, prepare_stage_b,
                      prepare_stage_b_from_legacy, preserve_incomplete_outputs,
                      select_linkage)

SUMMARY_FIELDS = (
    "summary_version", "case_id", "source_id", "stage_a_scientific_status",
    "ready_for_stage_b", "stage_b_package_status", "source_origin",
    "retrieval_time_status", "raw_source_sha256", "normalized_conversation_status",
    "model_view_status", "package_validation_status", "tC", "failure_reason",
    "ready_for_stage_c",
)


def summarize_package(root: Path, linkage: dict, status: str, failure: str = "") -> dict:
    row = {key: "" for key in SUMMARY_FIELDS}
    row.update(summary_version="stage-b-summary-v1", case_id=linkage["case_id"],
               source_id=linkage["source_case_id"],
               stage_a_scientific_status=linkage["stage_a_eligibility_status"],
               ready_for_stage_b="true", stage_b_package_status=status,
               failure_reason=failure, ready_for_stage_c="false")
    paths = output_paths(root, linkage["case_id"])
    if status in {"complete", "existing_valid"}:
        archive = json.loads(paths["source_archive"].read_text(encoding="utf-8"))
        normalized = json.loads(paths["normalized"].read_text(encoding="utf-8"))
        row.update(source_origin=archive.get("source_origin", ""),
                   retrieval_time_status=archive.get("retrieval_time_status", ""),
                   raw_source_sha256=archive.get("source_sha256", ""),
                   normalized_conversation_status="complete",
                   model_view_status="complete", package_validation_status="validated",
                   tC=normalized.get("start", ""), ready_for_stage_c="true")
    return row


def materialize_offline(root: Path, linkage: dict, current_cache: Path,
                        legacy_cache: Path) -> dict:
    """Materialize one case from existing/current or explicit legacy raw bytes only."""
    state = existing_package_status(root, linkage["case_id"])
    if state == "existing_valid":
        return summarize_package(root, linkage, "existing_valid")
    body_path, metadata_path, _ = legacy_cache_paths(current_cache, linkage["conversation_url"])
    prepared = None
    failure = ""
    try:
        if body_path.is_file() and metadata_path.is_file():
            no_network = lambda *args, **kwargs: (_ for _ in ()).throw(
                AssertionError("Offline Stage B attempted network access"))
            prepared = prepare_stage_b(linkage, HttpClient(current_cache, opener=no_network))
            if prepared["status"]["stage_b_status"] != "complete":
                raise ValueError("Current raw cache did not produce a complete package")
        else:
            legacy_body, legacy_meta, _ = legacy_cache_paths(
                legacy_cache, linkage["conversation_url"])
            if not legacy_body.is_file() or not legacy_meta.is_file():
                return summarize_package(root, linkage, "unresolved_no_source",
                                         "no_current_or_legacy_raw_source")
            prepared = prepare_stage_b_from_legacy(linkage, legacy_cache)
        if state == "incomplete":
            preserve_incomplete_outputs(root, linkage["case_id"])
        persist_stage_b(root, prepared)
        return summarize_package(root, linkage, "complete")
    except (ValueError, FileExistsError, OSError, json.JSONDecodeError) as exc:
        failure = f"{type(exc).__name__}: {exc}"
        return summarize_package(root, linkage, "failed", failure)


def run_offline_corpus(root: Path, source_rows: list[dict], screened_rows: list[dict],
                       current_cache: Path, legacy_cache: Path,
                       screened_manifest_ref: str) -> list[dict]:
    ready = [row for row in screened_rows
             if row.get("stage_b_readiness_status") == "ready_for_stage_b"]
    output = []
    for row in sorted(ready, key=lambda item: item["case_id"]):
        linkage = select_linkage(source_rows, row["case_id"], screened_rows,
                                 screened_manifest_ref=screened_manifest_ref)
        output.append(materialize_offline(root, linkage, current_cache, legacy_cache))
    return output


def write_summary(csv_path: Path, markdown_path: Path, rows: list[dict]) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=SUMMARY_FIELDS)
        writer.writeheader(); writer.writerows(rows)
    counts: dict[str, int] = {}
    origins: dict[str, int] = {}
    for row in rows:
        counts[row["stage_b_package_status"]] = counts.get(row["stage_b_package_status"], 0) + 1
        if row["ready_for_stage_c"] == "true":
            origin = row["source_origin"]
            origins[origin] = origins.get(origin, 0) + 1
    complete = sum(row["ready_for_stage_c"] == "true" for row in rows)
    markdown_path.write_text(
        "# Stage B operational summary\n\n"
        "This summary reports deterministic packaging status and does not change scientific eligibility.\n\n"
        f"Total Stage-A-ready cases: {len(rows)}\n\n"
        f"Complete packages: {complete}\n\n"
        f"Operationally ready for Stage C: {complete}\n\n"
        f"Not ready for Stage C: {len(rows) - complete}\n\n"
        "## Run dispositions\n\n"
        + "\n".join(f"- `{key}`: {value}" for key, value in sorted(counts.items()))
        + "\n\n## Complete-package source origins\n\n"
        + "\n".join(f"- `{key}`: {value}" for key, value in sorted(origins.items())) + "\n",
        encoding="utf-8")
