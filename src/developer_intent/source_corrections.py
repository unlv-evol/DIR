"""Versioned overlays for verified errors in inherited source linkage."""

from __future__ import annotations

import json
from pathlib import Path

from .screening import case_id, conversation_identity

CORRECTION_SCHEMA_VERSION = "dir-source-linkage-correction-v1"


def validate_source_correction(record: dict, source: dict) -> None:
    required = {
        "schema_version", "case_id", "source_case_id", "pr_url",
        "original_conversation_id", "original_conversation_url",
        "corrected_conversation_id", "corrected_conversation_url", "reason",
        "status", "reviewer", "timestamp", "version", "evidence_ref",
    }
    if set(record) != required:
        raise ValueError("Source-linkage correction fields differ from v1 contract")
    if record["schema_version"] != CORRECTION_SCHEMA_VERSION or record["status"] != "verified":
        raise ValueError("Source-linkage correction is not verified v1")
    source_id = source["Case ID"].strip()
    original_url = source["Conversation_Link"].strip()
    if (record["case_id"] != case_id(source_id)
            or record["source_case_id"] != source_id
            or record["pr_url"] != source["PR_Link"].strip()
            or record["original_conversation_url"] != original_url
            or record["original_conversation_id"] != conversation_identity(original_url)):
        raise ValueError("Source-linkage correction does not bind to inherited source row")
    corrected = conversation_identity(record["corrected_conversation_url"])
    if (not corrected or corrected != record["corrected_conversation_id"]
            or corrected == record["original_conversation_id"]):
        raise ValueError("Source-linkage correction conversation identity is invalid")
    for field in ("reason", "reviewer", "timestamp", "version", "evidence_ref"):
        if not isinstance(record[field], str) or not record[field].strip():
            raise ValueError(f"Source-linkage correction lacks {field}")
    from .stage_a_contracts import _timestamp
    _timestamp(record["timestamp"], "source_linkage_correction.timestamp")


def apply_source_corrections(source_rows: list[dict], correction_dir: Path) -> list[dict]:
    """Apply verified overlays while leaving caller/source files unchanged."""
    corrections = {}
    if correction_dir.exists():
        for path in sorted(correction_dir.glob("CASE_*.json")):
            record = json.loads(path.read_text(encoding="utf-8"))
            if path.stem != record.get("case_id") or record["case_id"] in corrections:
                raise ValueError("Duplicate or misnamed source-linkage correction")
            corrections[record["case_id"]] = record
    result = []
    used = set()
    for source in source_rows:
        copied = dict(source)
        cid = case_id(source["Case ID"].strip())
        correction = corrections.get(cid)
        if correction is not None:
            validate_source_correction(correction, source)
            copied["Conversation_Link"] = correction["corrected_conversation_url"]
            copied["DIR_Source_Linkage_Correction"] = correction["version"]
            used.add(cid)
        result.append(copied)
    unused = set(corrections) - used
    if unused:
        raise ValueError("Source-linkage correction has no inherited source row: " + ", ".join(sorted(unused)))
    return result
