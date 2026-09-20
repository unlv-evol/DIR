"""Candidate screening; never reads downstream outcome columns."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse

ALLOWED_CLASSES = {"PA", "PN"}
GITHUB_PR = re.compile(r"^/([^/]+)/([^/]+)/pull/(\d+)/?$")
FIELDS = (
    "screening_schema_version", "case_id", "source_case_id", "conversation_id", "conversation_url",
    "repository", "pr_number", "pr_url", "canonical_pr_url", "pr_redirect_verified",
    "Outcome_Class", "C_score",
    "S_score", "V_score", "changed_files", "additions", "deletions",
    "changed_lines", "pr_commits", "developer_prompts", "assistant_responses",
    "conversation_words", "conversation_start", "temporal_precision",
    "conversation_title", "conversation_source", "conversation_archive_status",
    "conversation_retrieval_status", "conversation_parsing_status",
    "conversation_temporal_status", "pr_retrieval_status", "pr_state",
    "pr_created_at", "pr_closed_at", "pr_merged_at",
    "complete_conversation_available", "required_links_present",
    "passes_changed_files", "passes_changed_lines", "passes_prompt_count",
    "passes_conversation_length", "commits_preferred", "case_integrity_status",
    "duplicate_of", "integrity_notes", "data_completeness_status",
    "scientific_data_eligible", "pilot_manageability_eligible",
    "screening_eligible", "exclusion_reason",
)


def case_id(source_case_id: str) -> str:
    """Stable across input row ordering and study membership."""
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
    if parsed.scheme != "https" or parsed.netloc.lower() not in {
        "chat.openai.com", "chatgpt.com"
    }:
        return None
    match = re.fullmatch(r"/share/([0-9a-fA-F-]{36})/?", parsed.path)
    return match[1].lower() if match else None


def _verified_pr_alias(pr: dict, source_url: str, pr_number: str) -> bool:
    """Recheck redirect provenance before accepting a changed repository URL."""
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
    return sum(len(str(turn["text"]).split()) for turn in turns)


def _flag(value: bool | None) -> str:
    return "" if value is None else str(value).lower()


def _valid_start(value: str, precision: str) -> bool:
    try:
        if precision == "date":
            return date.fromisoformat(value).isoformat() == value
        if precision == "timestamp":
            return datetime.fromisoformat(value).tzinfo is not None
    except ValueError:
        pass
    return False


def _load_evidence(source_dir: Path | None, source_case_id: str) -> dict:
    if source_dir is None:
        return {}
    path = source_dir / f"{source_case_id}.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def screen_rows(source_rows: list[dict], source_dir: Path | None = None) -> list[dict]:
    """Screen PA/PN rows from independently supplied source evidence.

    Evidence JSON may contain `pr` (GitHub PR response), `files` (all PR
    files), `commits` (all PR commits), and `conversation` with `url`,
    `start`, `precision`, `complete`, and ordered `turns` (`role`, `text`).
    Missing evidence stays missing; a partial conversation never passes.
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
        pr = evidence.get("pr")
        files = evidence.get("files")
        commits = evidence.get("commits")
        conv = evidence.get("conversation")
        notes: list[str] = []
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
        if isinstance(pr, dict) and isinstance(files, list) and isinstance(pr.get("changed_files"), int):
            if pr["changed_files"] != len({item.get("filename") for item in files if isinstance(item, dict)}):
                notes.append("pr_file_count_mismatch")
        if any(note.endswith("mismatch") or note == "invalid_source_link" for note in notes):
            integrity = "conflict"
        elif duplicate_of:
            integrity = "duplicate"
        elif pr is None or conv is None or not conv.get("start"):
            integrity = "unresolved"
        else:
            integrity = "ok"
        if integrity == "unresolved":
            notes.append("source_linkage_not_fully_verified")

        changed_files = additions = deletions = changed_lines = None
        if isinstance(files, list) and pr is not None:
            names = [item.get("filename") for item in files]
            if all(names) and all(isinstance(item.get("additions"), int) and
                                  isinstance(item.get("deletions"), int) for item in files):
                changed_files = len(set(names))
                additions = sum(item["additions"] for item in files)
                deletions = sum(item["deletions"] for item in files)
                changed_lines = additions + deletions
        commit_count = len(commits) if isinstance(commits, list) else (
            pr.get("commits") if isinstance(pr, dict) and isinstance(pr.get("commits"), int) else None)
        turns = conv.get("turns") if isinstance(conv, dict) else None
        complete = bool(conv and conv.get("complete") is True and isinstance(turns, list))
        prompts = responses = words = None
        if complete and all(isinstance(t, dict) and t.get("role") in {"user", "assistant"}
                            and isinstance(t.get("text"), str) for t in turns):
            prompts = sum(t["role"] == "user" for t in turns)
            responses = sum(t["role"] == "assistant" for t in turns)
            words = word_count(turns)
        else:
            complete = False
        start = conv.get("start", "") if isinstance(conv, dict) else ""
        precision = conv.get("precision", "") if isinstance(conv, dict) else ""
        if precision not in {"date", "timestamp"}:
            precision = ""
        if start and not _valid_start(start, precision):
            notes.append("invalid_conversation_start_or_precision")
            start = ""
        required_links = bool(pr_identity and conv_identity)
        checks = {
            "passes_changed_files": None if changed_files is None else changed_files <= 10,
            "passes_changed_lines": None if changed_lines is None else changed_lines <= 300,
            "passes_prompt_count": None if prompts is None else prompts <= 10,
            "passes_conversation_length": None if words is None else words <= 8000,
        }
        missing = []
        for key, value in (("changed_files", changed_files), ("changed_lines", changed_lines),
                           ("pr_commits", commit_count), ("developer_prompts", prompts),
                           ("conversation_words", words), ("conversation_start", start),
                           ("temporal_precision", precision)):
            if value is None or value == "":
                missing.append(key)
        if not complete:
            missing.append("complete_conversation")
        reasons = [key.removeprefix("passes_") + "_limit" for key, value in checks.items()
                   if value is False]
        if any(value is False for value in checks.values()):
            reasons.append("pilot_manageability_exclusion")
        reasons += ["missing_" + key for key in missing]
        if not required_links:
            reasons.append("required_links_missing_or_invalid")
        if integrity != "ok":
            reasons.append("integrity_" + integrity)
        scientific_data_eligible = bool(required_links and integrity == "ok" and not missing)
        pilot_manageability_eligible = (False if any(value is False for value in checks.values())
                                        else None if any(value is None for value in checks.values())
                                        else True)
        row = {
            "screening_schema_version": "dir-screening-v2",
            "case_id": cid, "source_case_id": sid,
            "conversation_id": conv_identity or "", "conversation_url": conv_url,
            "repository": pr_identity[0] if pr_identity else "",
            "pr_number": pr_identity[1] if pr_identity else "", "pr_url": pr_url,
            "canonical_pr_url": pr.get("html_url", "") if isinstance(pr, dict) else "",
            "pr_redirect_verified": _flag(_verified_pr_alias(pr, pr_url, pr_identity[1])
                                          if isinstance(pr, dict) and pr_identity else False),
            "Outcome_Class": source["Outcome_Class"], "C_score": source["Context"],
            "S_score": source["Specificity"], "V_score": source["Verification"],
            "changed_files": changed_files, "additions": additions,
            "deletions": deletions, "changed_lines": changed_lines,
            "pr_commits": commit_count, "developer_prompts": prompts,
            "assistant_responses": responses, "conversation_words": words,
            "conversation_start": start, "temporal_precision": precision,
            "conversation_title": conv.get("title", "") if isinstance(conv, dict) else "",
            "conversation_source": conv.get("source_type", "public_share") if isinstance(conv, dict) else "",
            "conversation_archive_status": evidence.get("conversation_archive_status", "not_attempted"),
            "conversation_retrieval_status": evidence.get("conversation_retrieval_status", "not_attempted"),
            "conversation_parsing_status": evidence.get("conversation_parsing_status", "not_attempted"),
            "conversation_temporal_status": conv.get("temporal_status", "unavailable") if isinstance(conv, dict) else "unavailable",
            "pr_retrieval_status": evidence.get("pr_retrieval_status", "not_attempted"),
            "pr_state": pr.get("state", "") if isinstance(pr, dict) else "",
            "pr_created_at": pr.get("created_at", "") if isinstance(pr, dict) else "",
            "pr_closed_at": pr.get("closed_at", "") if isinstance(pr, dict) else "",
            "pr_merged_at": pr.get("merged_at", "") if isinstance(pr, dict) else "",
            "complete_conversation_available": _flag(complete),
            "required_links_present": _flag(required_links),
            "commits_preferred": _flag(None if commit_count is None else commit_count <= 10),
            "case_integrity_status": integrity, "duplicate_of": duplicate_of,
            "integrity_notes": ";".join(notes),
            "data_completeness_status": "complete" if not missing else "incomplete",
            "scientific_data_eligible": _flag(scientific_data_eligible),
            "pilot_manageability_eligible": _flag(pilot_manageability_eligible),
            "screening_eligible": _flag(not reasons), "exclusion_reason": ";".join(reasons),
        }
        row.update({key: _flag(value) for key, value in checks.items()})
        result.append(row)
    return result


def read_source(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def write_manifest(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def screening_summary(source_rows: list[dict], screened: list[dict]) -> str:
    failures = Counter(reason for row in screened for reason in row["exclusion_reason"].split(";")
                       if reason)
    eligible = [row for row in screened if row["screening_eligible"] == "true"]
    missing = Counter(reason for row in screened for reason in row["exclusion_reason"].split(";")
                      if reason.startswith("missing_"))
    lines = ["# Screening summary", "", "Screening only; no pilot cases selected.",
             "Screening schema: `dir-screening-v2`; first-generation `tFG` is not derived here.", "",
             f"Source records: {len(source_rows)}",
             f"PA/PN candidates: {len(screened)}",
             f"Confirmed development-pilot screening eligible: {len(eligible)}",
             f"Scientific/data eligible: {sum(r['scientific_data_eligible'] == 'true' for r in screened)}",
             f"Pilot workload eligible: {sum(r['pilot_manageability_eligible'] == 'true' for r in screened)}",
             f"Pilot workload exceeded: {sum(r['pilot_manageability_eligible'] == 'false' for r in screened)}",
             f"Pilot workload unresolved: {sum(r['pilot_manageability_eligible'] == '' for r in screened)}",
             "The final eligible-pool size remains unresolved while required source facts are missing.",
             f"Detected duplicate candidates: "
             f"{sum(r['case_integrity_status'] == 'duplicate' for r in screened)}",
             f"Unresolved source linkage: "
             f"{sum(r['case_integrity_status'] == 'unresolved' for r in screened)}",
             f"Candidates with incomplete screening data: "
             f"{sum(r['data_completeness_status'] != 'complete' for r in screened)}", "",
             "## Hard-limit failures observed", ""]
    for field in ("passes_changed_files", "passes_changed_lines", "passes_prompt_count",
                  "passes_conversation_length"):
        lines.append(f"- {field}: {sum(r[field] == 'false' for r in screened)} "
                     f"failed; {sum(r[field] == '' for r in screened)} unresolved")
    lines += ["", "## PA/PN candidate distribution (descriptive only)", ""]
    lines += [f"- {key}: {value}" for key, value in sorted(Counter(
        row["Outcome_Class"] for row in screened).items())]
    lines += ["",
             "## Exclusion reasons", ""]
    lines += [f"- {key}: {value}" for key, value in sorted(failures.items())]
    lines += ["", "## Missing fields", ""]
    lines += [f"- {key}: {value}" for key, value in sorted(missing.items())]
    lines += ["", "## Eligible C/S/V distributions", ""]
    for field in ("C_score", "S_score", "V_score"):
        counts = Counter(row[field] for row in eligible)
        lines.append(f"- {field}: {dict(sorted(counts.items()))}")
    lines += ["", "## Eligible PA/PN distribution (descriptive only)", ""]
    lines += [f"- {key}: {value}" for key, value in sorted(Counter(
        row["Outcome_Class"] for row in eligible).items())]
    return "\n".join(lines) + "\n"
