"""Deterministic restricted case mapping derived from the Stage A source index."""

from __future__ import annotations

import csv
from pathlib import Path

from .screening import SCREENING_SCHEMA_VERSION, case_id, conversation_identity

MAPPING_SCHEMA_VERSION = "dir-case-mapping-v1"
MAPPING_FIELDS = ("mapping_schema_version", "case_id", "pr_url", "Outcome_Class",
                  "source_case_id", "conversation_id", "conversation_url")


def case_mapping_rows(source_rows: list[dict], screened_rows: list[dict]) -> list[dict]:
    """Validate linkage against the authoritative PA/PN index; never infer eligibility."""
    source_by_id = {}
    for source in source_rows:
        if source.get("Outcome_Class") not in {"PA", "PN"}:
            continue
        source_id = source["Case ID"].strip()
        if source_id in source_by_id:
            raise ValueError("Duplicate source Case ID in PA/PN index")
        source_by_id[source_id] = source
    seen = set()
    result = []
    for screened in screened_rows:
        source_id = screened["source_case_id"]
        source = source_by_id.get(source_id)
        neutral_id = screened["case_id"]
        if (source is None or neutral_id in seen or neutral_id != case_id(source_id)
                or screened.get("screening_schema_version") != SCREENING_SCHEMA_VERSION
                or screened.get("pr_url") != source["PR_Link"].strip()
                or screened.get("conversation_url") != source["Conversation_Link"].strip()
                or screened.get("conversation_id") != (
                    conversation_identity(source["Conversation_Link"].strip()) or "")
                or screened.get("Outcome_Class") != source["Outcome_Class"]):
            raise ValueError("Stage A mapping differs from the authoritative source index")
        seen.add(neutral_id)
        result.append({"mapping_schema_version": MAPPING_SCHEMA_VERSION,
                       "case_id": neutral_id, "pr_url": screened["pr_url"],
                       "Outcome_Class": screened["Outcome_Class"],
                       "source_case_id": source_id,
                       "conversation_id": screened["conversation_id"],
                       "conversation_url": screened["conversation_url"]})
    return sorted(result, key=lambda row: row["case_id"])


def write_case_mapping(rows: list[dict], path: Path) -> None:
    """Write a private mapping manifest; caller checks output protection first."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=MAPPING_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
