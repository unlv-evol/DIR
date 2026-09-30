"""Protocol v5 PA/PN screening: integrity, availability, and processability."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse

from .screening_checks import correspondence

ALLOWED_CLASSES = {"PA", "PN"}
METHODOLOGY_VERSION = "dir-tfg-v2"
SCREENING_SCHEMA_VERSION = "dir-screening-v9"
GITHUB_PR = re.compile(r"^/([^/]+)/([^/]+)/pull/(\d+)/?$")
PROCESSABILITY_FIELDS = (
    "conversation_available", "first_generation_boundary_identifiable",
    "project_history_accessible", "historical_state_reconstructible",
)
DEFERRED_STAGE_B_PENDING_REASONS = frozenset({
    "first_generation_boundary_identifiable_unresolved",
    "historical_state_reconstructible_unresolved",
})
FIELDS = (
    "screening_schema_version", "methodology_version", "case_id", "source_case_id",
    "conversation_id", "conversation_url", "repository", "pr_number", "pr_url",
    "canonical_pr_url", "pr_redirect_verified", "Outcome_Class", "C_score", "S_score", "V_score",
    "conversation_available", "temporal_anchor_available", "first_generation_boundary_identifiable",
    "source_linkage_status", "source_linkage_source", "source_linkage_reason",
    "pr_conversation_match", "duplicate_status", "project_history_accessible",
    "historical_state_reconstructible", "processability_source", "eligible", "eligibility_status",
    "pr_conversation_match_source", "pr_conversation_match_reviewer",
    "pr_conversation_match_timestamp", "pr_conversation_match_version",
    "pr_conversation_match_evidence_ref", "pr_conversation_match_reason",
    "project_history_access_mechanism", "project_history_access_repository",
    "project_history_access_object", "project_history_access_status",
    "project_history_access_source", "project_history_access_reason",
    "stage_b_readiness_status", "stage_b_readiness_reason",
    "exclusion_reason", "pending_reason", "case_integrity_status", "duplicate_of", "integrity_notes",
    "conversation_start", "temporal_precision", "conversation_temporal_status", "conversation_source",
    "conversation_retrieval_status", "conversation_parsing_status", "conversation_archive_status",
    "pr_retrieval_status", "changed_files", "additions", "deletions", "changed_lines",
    "pr_commits", "developer_prompts", "assistant_responses", "conversation_words",
    "conversation_turn_pattern",
)


def expected_stage_b_readiness(row: dict) -> tuple[str, str]:
    """Derive packaging readiness without promoting scientific disposition."""
    pending = {reason for reason in str(row.get("pending_reason") or "").split(";")
               if reason}
    blockers = []
    if row.get("eligibility_status") == "excluded" or row.get("exclusion_reason"):
        blockers.append("scientifically_excluded")
    for field, expected in (
        ("source_linkage_status", "established"),
        ("pr_conversation_match", "yes"),
        ("conversation_available", "yes"),
        ("temporal_anchor_available", "yes"),
        ("duplicate_status", "unique"),
        ("project_history_accessible", "yes"),
        ("case_integrity_status", "ok"),
    ):
        if row.get(field) != expected:
            blockers.append(field)
    deferred_fields = {
        "first_generation_boundary_identifiable":
            "first_generation_boundary_identifiable_unresolved",
        "historical_state_reconstructible":
            "historical_state_reconstructible_unresolved",
    }
    for field, reason in deferred_fields.items():
        value = row.get(field)
        if value == "no":
            blockers.append(field)
        elif row.get("eligibility_status") == "eligible" and value != "yes":
            blockers.append(field)
        elif reason in pending and value not in {"unresolved", "unavailable"}:
            blockers.append(field)
    nondeferred = pending - DEFERRED_STAGE_B_PENDING_REASONS
    if nondeferred:
        blockers.extend(sorted(nondeferred))
    if blockers:
        return "blocked", "blocked:" + ";".join(dict.fromkeys(blockers))
    if row.get("eligibility_status") == "eligible":
        return "ready_for_stage_b", "scientifically_eligible"
    if (row.get("eligibility_status") == "pending_resolution"
            and pending and pending <= DEFERRED_STAGE_B_PENDING_REASONS):
        return "ready_for_stage_b", "pending_only_stage_c_tfg_deferred"
    return "blocked", "blocked:unsupported_scientific_status"


def case_id(source_case_id: str) -> str:
    digest = hashlib.sha256(source_case_id.encode("utf-8")).hexdigest()[:12]
    return f"CASE_{digest.upper()}"


def github_identity(url: str) -> tuple[str, str] | None:
    parsed = urlparse(url)
    match = GITHUB_PR.fullmatch(parsed.path)
    if parsed.scheme != "https" or parsed.netloc.lower() != "github.com" or not match:
        return None
    return f"{match[1]}/{match[2]}", match[3]


def conversation_identity(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc.lower() not in {"chat.openai.com", "chatgpt.com"}:
        return None
    match = re.fullmatch(r"/share/([0-9a-fA-F-]{36})/?", parsed.path)
    return match[1].lower() if match else None


def _verified_pr_alias(pr: dict, source_url: str, pr_number: str) -> bool:
    final = urlparse(pr.get("api_final_url", ""))
    match = re.fullmatch(r"/repositories/(\d+)/pulls/(\d+)/?", final.path)
    canonical = github_identity(pr.get("html_url", ""))
    return bool(pr.get("redirect_verified") is True
                and pr.get("source_url") == source_url
                and pr.get("canonical_url") == pr.get("html_url")
                and canonical and canonical[1] == pr_number
                and final.scheme == "https" and final.netloc.lower() == "api.github.com"
                and match and int(match[1]) == pr.get("repository_id")
                and match[2] == pr_number)


def word_count(turns: list[dict]) -> int:
    return sum(len(turn["text"].split()) for turn in turns)


def _valid_start(value: str, precision: str) -> bool:
    try:
        if precision == "date":
            return date.fromisoformat(value).isoformat() == value
        if precision == "timestamp":
            return datetime.fromisoformat(value).tzinfo is not None
    except (TypeError, ValueError):
        pass
    return False


def _load_evidence(source_dir: Path | None, source_case_id: str) -> dict:
    if source_dir is None:
        return {}
    path = source_dir / f"{source_case_id}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _processability(evidence: dict) -> tuple[dict, str]:
    review = evidence.get("processability")
    if not isinstance(review, dict) or not isinstance(review.get("source"), str) or not review["source"].strip():
        return {field: "unresolved" for field in PROCESSABILITY_FIELDS}, ""
    values = {field: review.get(field, "unresolved") for field in PROCESSABILITY_FIELDS}
    if any(value not in {"yes", "no", "unresolved", "unavailable"} for value in values.values()):
        raise ValueError("Unsupported processability judgment; use yes/no/unresolved/unavailable")
    return values, review["source"].strip()


def screen_rows(source_rows: list[dict], source_dir: Path | None = None) -> list[dict]:
    """Screen PA/PN without size exclusions or unsupported source inferences.

    Positive processability claims require an explicit `processability.source`
    in the case evidence JSON. Unreviewed claims remain unresolved.
    """
    seen_pair: dict[tuple[str, str], str] = {}
    seen_conversation: dict[str, str] = {}
    result = []
    for source in source_rows:
        if source["Outcome_Class"] not in ALLOWED_CLASSES:
            continue
        sid = source["Case ID"].strip()
        cid = case_id(sid)
        pr_url = source["PR_Link"].strip()
        conv_url = source["Conversation_Link"].strip()
        pr_identity = github_identity(pr_url)
        conv_identity = conversation_identity(conv_url)
        evidence = _load_evidence(source_dir, sid)
        pr = evidence.get("pr") if isinstance(evidence.get("pr"), dict) else None
        files = evidence.get("files")
        commits = evidence.get("commits")
        conv = evidence.get("conversation") if isinstance(evidence.get("conversation"), dict) else None
        reviewed, review_source = _processability(evidence)
        match_review = correspondence(evidence, source, cid)
        access = evidence.get("history_access")
        if not isinstance(access, dict):
            access = {}
        access_pr_identity = github_identity(pr.get("html_url", "")) if pr else None
        access_bound = bool(access_pr_identity
                            and access.get("repository", "").casefold() == access_pr_identity[0].casefold()
                            and access.get("object") == pr.get("base_sha")
                            and access.get("mechanism") == "git_fetch_commit_object"
                            and access.get("source") == "PR base_sha")
        access_judgment = access.get("judgment")
        access_verified = (access_bound and (
            (access_judgment == "yes" and access.get("status") == "commit_object_retrieved")
            or (access_judgment == "no" and access.get("status") == "repository_inaccessible")))
        reviewed["project_history_accessible"] = (
            access_judgment if access_verified else "unresolved")
        notes = []
        duplicate_of = ""
        if not pr_identity or not conv_identity:
            notes.append("invalid_source_link")
        pair = (pr_url, conv_identity or conv_url)
        if pair in seen_pair:
            duplicate_of = seen_pair[pair]
            notes.append("duplicate_pr_conversation_pair")
        else:
            seen_pair[pair] = cid
        if conv_identity and conv_identity in seen_conversation and not duplicate_of:
            duplicate_of = seen_conversation[conv_identity]
            notes.append("conversation_in_multiple_rows")
        elif conv_identity:
            seen_conversation[conv_identity] = cid
        if pr is not None and pr_identity:
            if (str(pr.get("number")) != pr_identity[1]
                    or (pr.get("html_url") != pr_url
                        and not _verified_pr_alias(pr, pr_url, pr_identity[1]))):
                notes.append("pr_identity_mismatch")
            elif pr.get("html_url") != pr_url:
                notes.append("verified_repository_redirect")
        if conv is not None and conv.get("url") != conv_url:
            notes.append("conversation_link_mismatch")
        changed_files = additions = deletions = changed_lines = None
        if isinstance(files, list) and pr is not None and all(
            isinstance(item, dict) and item.get("filename")
            and isinstance(item.get("additions"), int)
            and isinstance(item.get("deletions"), int) for item in files
        ):
            changed_files = len({item["filename"] for item in files})
            additions = sum(item["additions"] for item in files)
            deletions = sum(item["deletions"] for item in files)
            changed_lines = additions + deletions
            if isinstance(pr.get("changed_files"), int) and changed_files != pr["changed_files"]:
                notes.append("pr_file_count_mismatch")
        commit_count = len(commits) if isinstance(commits, list) else (
            pr.get("commits") if pr is not None and isinstance(pr.get("commits"), int) else None)
        turns = conv.get("turns") if conv is not None else None
        complete = bool(conv is not None and conv.get("complete") is True
                        and isinstance(turns, list) and all(
                            isinstance(turn, dict) and turn.get("role") in {"user", "assistant"}
                            and isinstance(turn.get("text"), str) for turn in turns))
        prompts = sum(turn["role"] == "user" for turn in turns) if complete else None
        responses = sum(turn["role"] == "assistant" for turn in turns) if complete else None
        words = word_count(turns) if complete else None
        start = conv.get("start", "") if conv is not None else ""
        precision = conv.get("precision", "") if conv is not None else ""
        if precision not in {"date", "timestamp"}:
            precision = ""
        valid_start = bool(start and _valid_start(start, precision))
        if start and not valid_start:
            notes.append("invalid_conversation_start_or_precision")
            start = ""
        conflict = any(note.endswith("mismatch") or note == "invalid_source_link" for note in notes)
        integrity = ("conflict" if conflict else "duplicate" if duplicate_of else
                     "unresolved" if pr is None or conv is None else "ok")
        source_linkage = ("conflicting" if conflict else "unresolved" if pr is None or conv is None
                          else "established")
        source_linkage_source = ("PatchPrompt source-index PR/share pair; retrieved PR and "
                                 "conversation identities" if source_linkage == "established" else
                                 "PatchPrompt source-index PR/share pair")
        source_linkage_reason = ("" if source_linkage == "established" else
                                 ";".join(notes) if conflict else
                                 "retrieved PR or conversation identity unavailable")
        conversation_available = ("yes" if complete else "no" if
                                  reviewed["conversation_available"] == "no" else "unresolved")
        temporal_anchor_available = "yes" if valid_start else "no" if complete else "unresolved"
        boundary = reviewed["first_generation_boundary_identifiable"]
        history = reviewed["project_history_accessible"]
        reconstructible = reviewed["historical_state_reconstructible"]
        match = match_review["judgment"]
        exclusions = []
        pending = []
        if conflict:
            exclusions.append("source_identity_conflict")
        if duplicate_of:
            exclusions.append("duplicate_case")
        if source_linkage == "unresolved":
            pending.append("source_linkage_unresolved")
        if temporal_anchor_available == "no":
            exclusions.append("unusable_temporal_anchor")
        for field, value in (("conversation_available", conversation_available),
                             ("first_generation_boundary_identifiable", boundary),
                             ("pr_conversation_match", match),
                             ("project_history_accessible", history),
                             ("historical_state_reconstructible", reconstructible)):
            if value == "no":
                exclusions.append(field + "_failed")
            elif value in {"unresolved", "unavailable"}:
                pending.append(field + "_unresolved")
        if temporal_anchor_available == "unresolved":
            pending.append("temporal_anchor_unresolved")
        if not pr_identity or not conv_identity:
            exclusions.append("required_identity_missing")
        if pr is None:
            pending.append("pr_source_unavailable")
        if exclusions:
            status, eligible = "excluded", "false"
        elif pending:
            status, eligible = "pending_resolution", ""
        else:
            status, eligible = "eligible", "true"
        row = {
            "screening_schema_version": SCREENING_SCHEMA_VERSION,
            "methodology_version": METHODOLOGY_VERSION,
            "case_id": cid, "source_case_id": sid,
            "conversation_id": conv_identity or "", "conversation_url": conv_url,
            "repository": pr_identity[0] if pr_identity else "",
            "pr_number": pr_identity[1] if pr_identity else "", "pr_url": pr_url,
            "canonical_pr_url": pr.get("html_url", "") if pr else "",
            "pr_redirect_verified": str(bool(pr and pr_identity and _verified_pr_alias(
                pr, pr_url, pr_identity[1]))).lower(),
            "Outcome_Class": source["Outcome_Class"],
            "C_score": source["Context"], "S_score": source["Specificity"],
            "V_score": source["Verification"],
            "conversation_available": conversation_available,
            "temporal_anchor_available": temporal_anchor_available,
            "first_generation_boundary_identifiable": boundary,
            "source_linkage_status": source_linkage,
            "source_linkage_source": source_linkage_source,
            "source_linkage_reason": source_linkage_reason,
            "pr_conversation_match": match,
            "duplicate_status": "duplicate" if duplicate_of else "unique",
            "project_history_accessible": history,
            "historical_state_reconstructible": reconstructible,
            "processability_source": review_source,
            "pr_conversation_match_source": match_review["source"],
            "pr_conversation_match_reviewer": match_review["reviewer"],
            "pr_conversation_match_timestamp": match_review["timestamp"],
            "pr_conversation_match_version": match_review["version"],
            "pr_conversation_match_evidence_ref": match_review["evidence_ref"],
            "pr_conversation_match_reason": match_review["reason"],
            "project_history_access_mechanism": access.get("mechanism", ""),
            "project_history_access_repository": access.get("repository", ""),
            "project_history_access_object": access.get("object", ""),
            "project_history_access_status": access.get("status", "not_attempted"),
            "project_history_access_source": access.get("source", ""),
            "project_history_access_reason": access.get("reason", ""),
            "eligible": eligible, "eligibility_status": status,
            "stage_b_readiness_status": "",
            "stage_b_readiness_reason": "",
            "exclusion_reason": ";".join(dict.fromkeys(exclusions)),
            "pending_reason": ";".join(dict.fromkeys(pending)),
            "case_integrity_status": integrity, "duplicate_of": duplicate_of,
            "integrity_notes": ";".join(notes),
            "conversation_start": start, "temporal_precision": precision,
            "conversation_temporal_status": conv.get("temporal_status", "unavailable") if conv else "unavailable",
            "conversation_source": conv.get("source_type", "") if conv else "",
            "conversation_retrieval_status": evidence.get("conversation_retrieval_status", "not_attempted"),
            "conversation_parsing_status": evidence.get("conversation_parsing_status", "not_attempted"),
            "conversation_archive_status": evidence.get("conversation_archive_status", "not_attempted"),
            "pr_retrieval_status": evidence.get("pr_retrieval_status", "not_attempted"),
            "changed_files": changed_files, "additions": additions, "deletions": deletions,
            "changed_lines": changed_lines, "pr_commits": commit_count,
            "developer_prompts": prompts, "assistant_responses": responses,
            "conversation_words": words,
            "conversation_turn_pattern": (
                "single_developer_prompt" if prompts == 1 else
                "multiple_developer_prompts" if prompts is not None and prompts > 1 else
                "unavailable"),
        }
        readiness, readiness_reason = expected_stage_b_readiness(row)
        row.update(stage_b_readiness_status=readiness,
                   stage_b_readiness_reason=readiness_reason)
        result.append(row)
    return result


def read_source(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def write_manifest(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def screening_summary(source_rows: list[dict], screened: list[dict]) -> str:
    eligible = [row for row in screened if row["eligibility_status"] == "eligible"]
    counts = Counter(row["eligibility_status"] for row in screened)
    readiness = Counter(row["stage_b_readiness_status"] for row in screened)
    lines = ["# Protocol v5 Stage A screening summary", "",
             f"Methodology: `{METHODOLOGY_VERSION}`; screening schema: `{SCREENING_SCHEMA_VERSION}`.",
             f"Source records: {len(source_rows)}", f"PA/PN candidates: {len(screened)}",
             f"Confirmed eligible: {counts['eligible']}", f"Excluded: {counts['excluded']}",
             f"Pending resolution: {counts['pending_resolution']}", "",
             "## Stage B progression (not scientific eligibility)", "",
             f"Ready for Stage B: {readiness['ready_for_stage_b']}",
             f"Blocked: {readiness['blocked']}", "",
             "## PA/PN counts before and after screening", "",
             "| Outcome class | Candidates | Confirmed eligible | Pending | Excluded |",
             "| --- | ---: | ---: | ---: | ---: |"]
    for outcome in ("PA", "PN"):
        group = [row for row in screened if row["Outcome_Class"] == outcome]
        by_status = Counter(row["eligibility_status"] for row in group)
        lines.append(f"| {outcome} | {len(group)} | {by_status['eligible']} | "
                     f"{by_status['pending_resolution']} | {by_status['excluded']} |")
    lines += ["", "| Outcome class | Ready for Stage B | Blocked |",
              "| --- | ---: | ---: |"]
    for outcome in ("PA", "PN"):
        group = [row for row in screened if row["Outcome_Class"] == outcome]
        by_readiness = Counter(row["stage_b_readiness_status"] for row in group)
        lines.append(f"| {outcome} | {by_readiness['ready_for_stage_b']} | "
                     f"{by_readiness['blocked']} |")
    lines += ["", "## Exclusion reasons", ""]
    excluded = Counter(reason for row in screened for reason in row["exclusion_reason"].split(";") if reason)
    lines += [f"- {key}: {value}" for key, value in sorted(excluded.items())]
    lines += ["", "## Pending evidence", ""]
    pending = Counter(reason for row in screened
                      if row["eligibility_status"] == "pending_resolution"
                      for reason in row["pending_reason"].split(";") if reason)
    lines += [f"- {key}: {value}" for key, value in sorted(pending.items())]
    lines += ["", "## Stage A manual PR/conversation correspondence queue", ""]
    queue = [row for row in screened
             if row["eligibility_status"] == "pending_resolution"
             and row["pr_conversation_match"] == "unresolved"]
    lines += [f"- {row['case_id']}: pending Stage A manual screening" for row in queue]
    if not queue:
        lines.append("- None")
    lines += ["", "Size and conversation-length measures are descriptive only.",
              "No real discovery/held-out assignment is produced by screening.", ""]
    return "\n".join(lines)
