"""Offline Stage A manual correspondence CSV export and canonical import."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from .screening import conversation_identity
from .stage_a_contracts import validate_correspondence_review

REVIEW_CSV_VERSION = "dir-correspondence-review-csv-v1"
DEFAULT_EVIDENCE_POLICY = "identifiers_and_source_linkage_only"
RESTRICTED_TASK_POLICY = "direct_share_reference_and_restricted_task_context_v1"
ALLOWED_EVIDENCE_POLICIES = {DEFAULT_EVIDENCE_POLICY, RESTRICTED_TASK_POLICY}

REVIEW_CSV_FIELDS = (
    "review_csv_version", "case_id", "pr_url",
    "conversation_id", "conversation_url", "source_linkage_status",
    "source_linkage_source", "automated_screening_status",
    "automated_screening_reasons", "permitted_evidence_policy",
    "permitted_evidence_ref", "pr_conversation_match",
    "pr_conversation_match_source", "pr_conversation_match_reviewer",
    "pr_conversation_match_timestamp", "pr_conversation_match_version",
    "pr_conversation_match_evidence_ref", "pr_conversation_match_reason",
)

MANUAL_FIELDS = (
    "pr_conversation_match", "pr_conversation_match_source",
    "pr_conversation_match_reviewer", "pr_conversation_match_timestamp",
    "pr_conversation_match_version", "pr_conversation_match_evidence_ref",
    "pr_conversation_match_reason",
)


def review_rows(screened_rows: list[dict], *,
                evidence_policy: str = DEFAULT_EVIDENCE_POLICY) -> list[dict]:
    """Build deterministic restricted rows for cases needing manual review."""
    if evidence_policy not in ALLOWED_EVIDENCE_POLICIES:
        raise ValueError("Unsupported correspondence evidence policy")
    result = []
    for row in sorted(screened_rows, key=lambda item: item["case_id"]):
        if (row.get("pr_conversation_match") != "unresolved"
                or row.get("source_linkage_status") != "established"
                or row.get("exclusion_reason")):
            continue
        reasons = row.get("pending_reason", "")
        result.append({
            "review_csv_version": REVIEW_CSV_VERSION,
            "case_id": row["case_id"],
            "pr_url": row["pr_url"],
            "conversation_id": row["conversation_id"],
            "conversation_url": row["conversation_url"],
            "source_linkage_status": row["source_linkage_status"],
            "source_linkage_source": row["source_linkage_source"],
            "automated_screening_status": (
                "processable_for_correspondence_review"),
            "automated_screening_reasons": ";".join(
                reason for reason in reasons.split(";")
                if reason and reason != "pr_conversation_match_unresolved"),
            "permitted_evidence_policy": evidence_policy,
            "permitted_evidence_ref": f"stage-a-restricted-packet:{row['case_id']}",
            **{field: "" for field in MANUAL_FIELDS},
        })
    return result


def write_review_csv(rows: list[dict], path: Path) -> None:
    """Write deterministically; an identical repeat is idempotent."""
    path.parent.mkdir(parents=True, exist_ok=True)
    from io import StringIO
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=REVIEW_CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    content = buffer.getvalue()
    if path.exists():
        if path.read_text(encoding="utf-8") == content:
            return
        raise FileExistsError(f"Review CSV exists with different content: {path}")
    path.write_text(content, encoding="utf-8")


def _read_review_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != list(REVIEW_CSV_FIELDS):
            raise ValueError("Correspondence review CSV header differs from contract")
        rows = list(reader)
    ids = [row["case_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate case row in correspondence review CSV")
    return rows


def import_review_csv(path: Path, screened_rows: list[dict], source_rows: list[dict],
                      review_dir: Path, repository_root: Path | None = None) -> dict[str, int]:
    """Validate completed cells and materialize canonical v1 JSON records."""
    screened = {row["case_id"]: row for row in screened_rows}
    sources = {row["Case ID"].strip(): row for row in source_rows}
    skipped = 0
    planned = []
    for row in _read_review_csv(path):
        case = screened.get(row["case_id"])
        if case is None:
            raise ValueError(f"Unknown case_id in correspondence CSV: {row['case_id']}")
        expected_reasons = ";".join(
            reason for reason in case.get("pending_reason", "").split(";")
            if reason and reason != "pr_conversation_match_unresolved")
        if (row["review_csv_version"] != REVIEW_CSV_VERSION
                or row["pr_url"] != case["pr_url"]
                or row["conversation_url"] != case["conversation_url"]
                or row["conversation_id"] != case["conversation_id"]
                or conversation_identity(row["conversation_url"]) != row["conversation_id"]
                or row["source_linkage_status"] != case["source_linkage_status"]
                or row["source_linkage_source"] != case["source_linkage_source"]
                or row["automated_screening_status"] != "processable_for_correspondence_review"
                or row["automated_screening_reasons"] != expected_reasons
                or row["permitted_evidence_policy"] not in ALLOWED_EVIDENCE_POLICIES):
            raise ValueError(f"Correspondence CSV identity/provenance mismatch: {row['case_id']}")
        if row["permitted_evidence_policy"] == DEFAULT_EVIDENCE_POLICY:
            if row["permitted_evidence_ref"] != f"stage-a-restricted-packet:{row['case_id']}":
                raise ValueError(f"Correspondence CSV identity/provenance mismatch: {row['case_id']}")
        else:
            if repository_root is None:
                raise ValueError("Repository root is required for restricted evidence validation")
            if row["pr_conversation_match_evidence_ref"] != row["permitted_evidence_ref"]:
                raise ValueError(f"Correspondence evidence references differ: {row['case_id']}")
            from .correspondence_evidence import validate_packet_reference
            validate_packet_reference(row["permitted_evidence_ref"], repository_root, row)
        judgment = row["pr_conversation_match"].strip()
        if not judgment:
            skipped += 1
            continue
        if judgment not in {"yes", "no", "unresolved"}:
            raise ValueError(f"Invalid correspondence judgment for {row['case_id']}")
        required = MANUAL_FIELDS[1:]
        if any(not row[field].strip() for field in required):
            raise ValueError(f"Completed review lacks required provenance: {row['case_id']}")
        review = {
            "case_id": row["case_id"], "pr_url": row["pr_url"],
            "conversation_url": row["conversation_url"], "judgment": judgment,
            "source": row["pr_conversation_match_source"].strip(),
            "reviewer": row["pr_conversation_match_reviewer"].strip(),
            "timestamp": row["pr_conversation_match_timestamp"].strip(),
            "version": row["pr_conversation_match_version"].strip(),
            "evidence_ref": row["pr_conversation_match_evidence_ref"].strip(),
            "rationale": row["pr_conversation_match_reason"].strip(),
            "review_csv_version": REVIEW_CSV_VERSION,
            "permitted_evidence_policy": row["permitted_evidence_policy"],
            "permitted_evidence_ref": row["permitted_evidence_ref"],
        }
        source = sources.get(case["source_case_id"])
        if source is None:
            raise ValueError(f"Source case is unavailable: {case['source_case_id']}")
        validate_correspondence_review(review, source)
        output = review_dir / f"{row['case_id']}.json"
        content = json.dumps(review, indent=2, sort_keys=True) + "\n"
        applicable = (case.get("source_linkage_status") == "established"
                      and not case.get("exclusion_reason"))
        if not applicable and not (output.exists()
                                   and output.read_text(encoding="utf-8") == content):
            raise ValueError(f"Case is not applicable for manual correspondence review: {row['case_id']}")
        planned.append((output, content))
    for output, content in planned:
        if output.exists() and output.read_text(encoding="utf-8") != content:
            raise FileExistsError(f"Canonical correspondence review conflicts: {output}")
    review_dir.mkdir(parents=True, exist_ok=True)
    imported = unchanged = 0
    for output, content in planned:
        if output.exists():
            unchanged += 1
        else:
            output.write_text(content, encoding="utf-8")
            imported += 1
    return {"imported": imported, "unchanged": unchanged, "skipped_blank": skipped}
