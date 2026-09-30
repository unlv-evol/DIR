"""Build minimal, leakage-restricted Stage A correspondence evidence packets."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from .screening import case_id, conversation_identity
from .correspondence_workflow import REVIEW_CSV_FIELDS

EVIDENCE_SCHEMA_VERSION = "dir-correspondence-evidence-v1"
EVIDENCE_POLICY = "direct_share_reference_and_restricted_task_context_v1"
DOWNSTREAM_USE = "stage_a_correspondence_only_not_reconstruction_evidence"
FORBIDDEN_KEYS = {
    "Outcome_Class", "State", "MergedAt", "ClosedAt", "Additions", "Deletions",
    "ChangedFiles", "Commits", "CommitsTotalCount", "Answer", "ListOfCode",
    "HTMLContent", "final_diff", "integrated_implementation", "Adopt_Any",
    "Fraction_Adopted",
}


def _walk_pr_records(value, wanted: set[str]):
    if isinstance(value, dict):
        if value.get("Type") == "pull request" and value.get("URL") in wanted:
            yield value
        for child in value.values():
            yield from _walk_pr_records(child, wanted)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_pr_records(child, wanted)


def _archive_index(archive_dir: Path, wanted: set[str]) -> dict[str, list[dict]]:
    result = {url: [] for url in wanted}
    for path in sorted(archive_dir.glob("*.json")):
        raw = path.read_bytes()
        try:
            payload = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"Invalid PatchTrack archive JSON: {path}") from exc
        checksum = hashlib.sha256(raw).hexdigest()
        for record in _walk_pr_records(payload, wanted):
            result[record["URL"]].append({
                "archive_file": path.name,
                "archive_sha256": checksum,
                "record": record,
            })
    return result


def _share_candidates(records: list[dict]) -> list[dict]:
    result = []
    for snapshot in records:
        shares = snapshot["record"].get("ChatgptSharing", [])
        if not isinstance(shares, list):
            continue
        for share in shares:
            if isinstance(share, dict):
                result.append({**snapshot, "share": share})
    return result


def _sort_key(candidate: dict) -> tuple[str, str]:
    share = candidate["share"]
    return (str(share.get("DateOfAccess") or "9999"), candidate["archive_file"])


def _select_archive(records: list[dict], conversation_url: str) -> tuple[str, dict | None]:
    candidates = _share_candidates(records)
    exact = [item for item in candidates if item["share"].get("URL") == conversation_url]
    if exact:
        return "archive_exact_pair", sorted(exact, key=_sort_key)[0]
    mentioned = [item for item in candidates
                 if isinstance(item["share"].get("Mention"), dict)]
    if mentioned:
        return "archive_conflicting_reference", sorted(mentioned, key=_sort_key)[0]
    return "reviewer_attestation_only", None


def _developer_prompts(evidence_dir: Path, source_case_id: str) -> list[str]:
    path = evidence_dir / f"{source_case_id}.json"
    if not path.exists():
        return []
    facts = json.loads(path.read_text(encoding="utf-8"))
    turns = facts.get("conversation", {}).get("turns", [])
    return [turn["text"] for turn in turns
            if isinstance(turn, dict) and turn.get("role") == "user"
            and isinstance(turn.get("text"), str)]


def _packet(row: dict, source_case_id: str, evidence_dir: Path,
            archive_records: list[dict]) -> dict:
    status, selected = _select_archive(archive_records, row["conversation_url"])
    share = selected["share"] if selected else {}
    mention = share.get("Mention") if isinstance(share.get("Mention"), dict) else {}
    referenced_url = share.get("URL", "")
    packet = {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "policy": EVIDENCE_POLICY,
        "case_id": row["case_id"],
        "pr_url": row["pr_url"],
        "conversation_id": row["conversation_id"],
        "conversation_url": row["conversation_url"],
        "support_status": status,
        "review_observation": {
            "judgment": row["pr_conversation_match"],
            "reviewer": row["pr_conversation_match_reviewer"],
            "reviewed_at": row["pr_conversation_match_timestamp"],
            "review_version": row["pr_conversation_match_version"],
            "rationale": row["pr_conversation_match_reason"],
        },
        "pr_reference": {
            "referenced_conversation_url": referenced_url,
            "matches_indexed_conversation": bool(
                referenced_url and conversation_identity(referenced_url) == row["conversation_id"]),
            "mention_url": mention.get("MentionedURL", ""),
            "mention_property": mention.get("MentionedProperty", ""),
            "mention_author": mention.get("MentionedAuthor", ""),
            "mention_path": mention.get("MentionedPath", ""),
            "restricted_excerpt": mention.get("MentionedText", ""),
            "created_at": "",
            "temporal_status": "unresolved",
        },
        "conversation_reference": {
            "source": "screening_cache_visible_developer_turns",
            "developer_task_excerpts": _developer_prompts(evidence_dir, source_case_id),
        },
        "archive_provenance": {
            "archive_file": selected["archive_file"] if selected else "",
            "archive_sha256": selected["archive_sha256"] if selected else "",
            "archive_capture_time": str(share.get("DateOfAccess") or ""),
            "record_status": "available" if selected else "unavailable",
        },
        "downstream_use": DOWNSTREAM_USE,
    }
    return packet


def packet_bytes(packet: dict) -> bytes:
    return (json.dumps(packet, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def packet_reference(relative_path: str, content: bytes) -> str:
    return f"{relative_path}#sha256={hashlib.sha256(content).hexdigest()}"


def prepare_review_evidence(review_csv: Path, source_rows: list[dict], archive_dir: Path,
                            evidence_dir: Path, packet_dir: Path, output_csv: Path,
                            repository_root: Path) -> dict[str, int]:
    """Create restricted packets and a review CSV bound to their checksums."""
    with review_csv.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != list(REVIEW_CSV_FIELDS):
            raise ValueError("Correspondence review CSV header differs from contract")
        rows = list(reader)
    source_by_case = {case_id(row["Case ID"].strip()): row for row in source_rows
                      if row.get("Outcome_Class") in {"PA", "PN"}}
    archive = _archive_index(archive_dir, {row["pr_url"] for row in rows})
    planned = []
    counts: dict[str, int] = {}
    for row in rows:
        source = source_by_case.get(row["case_id"])
        if source is None:
            raise ValueError(f"No source row for {row['case_id']}")
        packet = _packet(row, source["Case ID"].strip(), evidence_dir,
                         archive.get(row["pr_url"], []))
        from .stage_a_contracts import validate_correspondence_evidence
        validate_correspondence_evidence(packet)
        output = packet_dir / f"{row['case_id']}.json"
        content = packet_bytes(packet)
        relative = output.resolve().relative_to(repository_root.resolve()).as_posix()
        ref = packet_reference(relative, content)
        updated = dict(row)
        updated["permitted_evidence_policy"] = EVIDENCE_POLICY
        updated["permitted_evidence_ref"] = ref
        updated["pr_conversation_match_evidence_ref"] = ref
        planned.append((output, content, updated))
        counts[packet["support_status"]] = counts.get(packet["support_status"], 0) + 1
    if output_csv.exists() or any(path.exists() for path, _, _ in planned):
        raise FileExistsError("Correspondence evidence output already exists")
    packet_dir.mkdir(parents=True, exist_ok=True)
    for path, content, _ in planned:
        path.write_bytes(content)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=REVIEW_CSV_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(row for _, _, row in planned)
    return counts


def validate_packet_reference(reference: str, repository_root: Path, row: dict) -> dict:
    marker = "#sha256="
    if marker not in reference:
        raise ValueError("Correspondence evidence reference lacks checksum")
    relative, expected = reference.rsplit(marker, 1)
    if not relative.startswith("cases/manifests/correspondence_evidence/"):
        raise ValueError("Correspondence evidence reference is outside restricted packet directory")
    path = (repository_root / relative).resolve()
    allowed = (repository_root / "cases/manifests/correspondence_evidence").resolve()
    if allowed not in path.parents:
        raise ValueError("Correspondence evidence path escapes restricted packet directory")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError("Correspondence evidence checksum mismatch")
    packet = json.loads(raw)
    from .stage_a_contracts import validate_correspondence_evidence
    validate_correspondence_evidence(packet)
    for field in ("case_id", "pr_url", "conversation_id", "conversation_url"):
        if packet[field] != row[field]:
            raise ValueError(f"Correspondence evidence {field} mismatch")
    if packet["policy"] != row["permitted_evidence_policy"]:
        raise ValueError("Correspondence evidence policy mismatch")
    if packet["review_observation"]["judgment"] != row["pr_conversation_match"]:
        raise ValueError("Correspondence evidence judgment mismatch")
    return packet
