"""Conservative screening fallback for PatchTrack's archived PR sharings."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from zipfile import ZipFile

from .screening_chatgpt import parse_share, share_id
from .screening_github import pr_identity


def _pr_key(url: str) -> tuple[str, str, int] | None:
    identity = pr_identity(url)
    return (identity[0].casefold(), identity[1].casefold(), identity[2]) if identity else None


def _summary_turns(sharing: dict) -> list[dict]:
    turns = []
    for exchange in sharing.get("Conversations") or []:
        if not isinstance(exchange, dict):
            continue
        for field, role in (("Prompt", "user"), ("Answer", "assistant")):
            if isinstance(exchange.get(field), str) and exchange[field]:
                turns.append({"role": role, "text": exchange[field]})
    return turns


def archive_fallback(archive: Path, source_rows: list[dict]) -> dict[str, dict]:
    """Match both PR identity and share ID, then assess archived evidence.

    HTML is promoted only if the existing parser obtains ordered turns and a
    first-user temporal value. Summary-only records are retained as leads;
    they cannot establish conversation completeness or the first-prompt date.
    Conflicting HTML snapshots are never silently selected.
    """
    targets = {row["Case ID"].strip(): (_pr_key(row["PR_Link"].strip()),
                                      share_id(row["Conversation_Link"].strip()),
                                      row["Conversation_Link"].strip()) for row in source_rows}
    results = {sid: {"status": "not_found"} for sid in targets}
    if not archive.exists():
        return {sid: {"status": "archive_unavailable"} for sid in targets}
    archive_sha = hashlib.sha256(archive.read_bytes()).hexdigest()
    by_share = defaultdict(list)
    with ZipFile(archive) as bundle:
        for member in sorted(bundle.infolist(), key=lambda item: item.filename):
            if (not member.filename.endswith(".json") or member.filename.startswith("__MACOSX/")
                    or member.file_size > 100_000_000):
                continue
            payload = json.loads(bundle.read(member))
            if not isinstance(payload, dict) or not isinstance(payload.get("Sources"), list):
                continue
            for pr in payload["Sources"]:
                if not isinstance(pr, dict):
                    continue
                for sharing in pr.get("ChatgptSharing") or []:
                    if not isinstance(sharing, dict):
                        continue
                    identity = share_id(str(sharing.get("URL", "")))
                    if identity:
                        by_share[identity].append((member.filename, pr, sharing))
    for sid, (expected_pr, identity, source_url) in targets.items():
        if not expected_pr or not identity:
            results[sid] = {"status": "invalid_source_link"}
            continue
        hits = by_share.get(identity, [])
        matches = [(member, pr, sharing) for member, pr, sharing in hits
                   if _pr_key(str(pr.get("URL", ""))) == expected_pr]
        if not matches:
            results[sid] = {"status": "pr_mismatch" if hits else "not_found"}
            continue
        parsed = []
        leads = []
        for member, pr, sharing in matches:
            provenance = {"archive_path": str(archive), "archive_sha256": archive_sha,
                          "member": member, "pr_url": pr["URL"], "conversation_url": sharing["URL"],
                          "date_of_conversation": sharing.get("DateOfConversation"),
                          "date_of_access": sharing.get("DateOfAccess")}
            html = sharing.get("HTMLContent")
            if isinstance(html, str) and html and identity in html.lower():
                try:
                    conversation = parse_share(html.encode("utf-8"))
                except ValueError:
                    pass
                else:
                    if conversation["start"] and conversation["precision"] in {"date", "timestamp"}:
                        conversation.update(url=source_url, canonical_url=source_url,
                                            share_id=identity, source_type="patchtrack_archive",
                                            archive_provenance=provenance)
                        parsed.append(conversation)
                        continue
            leads.append({"provenance": provenance, "status": sharing.get("Status"),
                          "reported_prompt_count": sharing.get("NumberOfPrompts"),
                          "turns": _summary_turns(sharing),
                          "raw_sharing": {key: value for key, value in sharing.items()
                                          if key != "HTMLContent"}})
        if parsed:
            signatures = {json.dumps((item["turns"], item["start"], item["precision"]),
                                     sort_keys=True) for item in parsed}
            if len(signatures) == 1:
                results[sid] = {"status": "recovered", "conversation": parsed[0],
                                "matching_members": [item["archive_provenance"]["member"]
                                                     for item in parsed]}
            else:
                results[sid] = {"status": "conflicting_snapshots",
                                "matching_members": [item["archive_provenance"]["member"]
                                                     for item in parsed]}
        else:
            results[sid] = {"status": "summary_only_unresolved", "leads": leads}
    return results
