"""Protocol v5 Stage B preparation and failure-safe persistence."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import tempfile
from pathlib import Path

from .conversation_package import (PACKAGE_KEYS, build_case_linkage_record,
                                   build_stage_c_model_view, prepare_conversation_layers)
from .screening import (SCREENING_SCHEMA_VERSION, case_id, conversation_identity,
                        github_identity)
from .screening_chatgpt import retrieve_share


def select_linkage(source_rows: list[dict], selected_case_id: str,
                   screened_rows: list[dict] | None = None) -> dict:
    """Resolve a neutral ID; an optional v5 manifest authorizes Stage B progression."""
    matches = [row for row in source_rows if row.get("Outcome_Class") in {"PA", "PN"}
               and case_id(row["Case ID"].strip()) == selected_case_id]
    if len(matches) != 1:
        raise ValueError("Case ID must identify exactly one PA/PN source row")
    row = matches[0]
    pr_url = row["PR_Link"].strip()
    conversation_url = row["Conversation_Link"].strip()
    pr_identity = github_identity(pr_url)
    conversation_id = conversation_identity(conversation_url)
    if pr_identity is None or conversation_id is None:
        raise ValueError("Technical smoke case has invalid source identity")
    linkage_input = {
        "case_id": selected_case_id, "source_case_id": row["Case ID"].strip(),
        "pr_url": pr_url, "repository": pr_identity[0], "pr_number": pr_identity[1],
        "conversation_id": conversation_id, "conversation_url": conversation_url,
        "Outcome_Class": row["Outcome_Class"],
        "case_integrity_status": "technical_smoke_unverified",
    }
    if screened_rows is not None:
        matching = [item for item in screened_rows if item.get("case_id") == selected_case_id]
        if len(matching) != 1:
            raise ValueError("Case ID must occur exactly once in the Stage A manifest")
        screened = matching[0]
        if (screened.get("screening_schema_version") != SCREENING_SCHEMA_VERSION
                or screened.get("methodology_version") != "dir-tfg-v2"
                or screened.get("source_case_id") != row["Case ID"].strip()
                or screened.get("Outcome_Class") != row["Outcome_Class"]
                or screened.get("pr_url") != pr_url
                or screened.get("conversation_url") != conversation_url):
            raise ValueError("Stage A manifest version or source linkage differs")
        if (screened.get("stage_b_readiness_status") != "ready_for_stage_b"
                or screened.get("eligibility_status") != "eligible"):
            raise ValueError("Case is not scientifically eligible for Stage B")
        linkage_input.update(screening_schema_version=SCREENING_SCHEMA_VERSION,
                             eligibility_status=screened["eligibility_status"],
                             stage_b_readiness_status=screened["stage_b_readiness_status"],
                             case_integrity_status=screened.get("case_integrity_status", ""))
    return build_case_linkage_record(linkage_input)


def output_paths(root: Path, case_id: str) -> dict[str, Path]:
    """Separate restricted linkage, raw source, and conversation-side files."""
    return {
        "linkage": root / "cases/manifests/linkage" / f"{case_id}.json",
        "source_archive": root / "cases/raw" / case_id / "conversation_source_archive.json",
        "normalized": root / "cases/conversations" / case_id / "normalized_conversation.json",
        "model_view": root / "cases/conversations" / case_id / "stage_c_model_view.json",
        "status": root / "cases/conversations" / case_id / "package_status.json",
    }


def check_new_outputs(paths: dict[str, Path]) -> None:
    existing = [str(path) for path in paths.values() if path.exists()]
    if existing:
        raise FileExistsError("Stage B output exists; no overwrite: " + ", ".join(existing))


def validate_complete_package(linkage: dict, archive: dict,
                              normalized: dict, model_view: dict) -> None:
    case_id = linkage["case_id"]
    if any(record.get("case_id") != case_id for record in (archive, normalized, model_view)):
        raise ValueError("Stage B case identities disagree")
    payload = base64.b64decode(archive["source_payload_base64"], validate=True)
    if (not payload or hashlib.sha256(payload).hexdigest() != archive.get("source_sha256")
            or normalized.get("source_archive_sha256") != archive["source_sha256"]):
        raise ValueError("Stage B source checksum or provenance mismatch")
    records = normalized.get("records")
    turns = normalized.get("visible_turns")
    if (not isinstance(records, list) or not isinstance(turns, list) or not turns
            or any(turn.get("source_record_index") != turn.get("event_index")
                   or not isinstance(turn.get("event_index"), int)
                   or turn["event_index"] >= len(records) for turn in turns)
            or [turn["event_index"] for turn in turns] != sorted(
                {turn["event_index"] for turn in turns})):
        raise ValueError("Stage B conversation ordering/provenance invalid")
    if (set(model_view) != PACKAGE_KEYS or model_view.get("complete") is not True
            or model_view.get("records") is None
            or model_view != build_stage_c_model_view(normalized)):
        raise ValueError("Stage C view is not the allowlisted normalized derivative")
    text = json.dumps(model_view, ensure_ascii=False)
    if any(identity and identity in text for identity in
           (linkage.get("pr_url"), linkage.get("repository"),
            linkage.get("canonical_pr_url"))):
        raise ValueError("Stage C view contains restricted PR/repository identity")


def prepare_stage_b(linkage: dict, http, *, refresh: bool = False) -> dict:
    """Use the existing share retriever; no GitHub or Stage C LLM execution."""
    case_id = linkage["case_id"]
    chat, source = retrieve_share(linkage["conversation_url"], http,
                                  refresh=refresh, with_source=True)
    result = {"linkage": linkage, "archive": None, "normalized": None,
              "model_view": None,
              "status": {"case_id": case_id, "stage_b_status": "retrieval_failed",
                         "stage_a_eligibility_status": linkage["stage_a_eligibility_status"],
                         "stage_b_readiness_status": linkage["stage_b_readiness_status"],
                         "screening_schema_version": linkage["screening_schema_version"],
                         "retrieval_status": chat["retrieval_status"],
                         "parsing_status": chat["parsing_status"]}}
    if source is None or source.body is None:
        return result
    archive, normalized, model_view = prepare_conversation_layers(
        case_id, source.body, source_url=linkage["conversation_url"],
        retrieval_status=source.status, retrieved_at=source.retrieved_at,
        content_type=source.content_type, http_status=source.http_status,
        final_url=source.final_url, source_origin="cached" if source.from_cache else "fresh")
    result["archive"] = archive
    result["status"].update(source_origin=archive["source_origin"],
                            retrieval_time_status=archive["retrieval_time_status"])
    if normalized is None or model_view is None:
        result["status"].update(stage_b_status="normalization_failed",
                                normalization_error=archive.get("normalization_error", ""))
        return result
    try:
        validate_complete_package(linkage, archive, normalized, model_view)
    except ValueError as exc:
        result["normalized"] = normalized
        result["status"].update(stage_b_status="validation_failed",
                                validation_error=str(exc))
        return result
    result["normalized"] = normalized
    result["model_view"] = model_view
    result["status"]["stage_b_status"] = "complete"
    return result


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", dir=path.parent, prefix=".stage_b_",
                                         suffix=".tmp", encoding="utf-8",
                                         delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(value, stream, indent=2, ensure_ascii=False, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)  # atomic create; cannot replace an existing artifact
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def persist_stage_b(root: Path, prepared: dict) -> dict[str, Path]:
    """Write completion marker last; absent marker means partial failure."""
    paths = output_paths(root, prepared["linkage"]["case_id"])
    check_new_outputs(paths)
    _atomic_json(paths["linkage"], prepared["linkage"])
    if prepared["archive"] is not None:
        _atomic_json(paths["source_archive"], prepared["archive"])
    if prepared["normalized"] is not None:
        _atomic_json(paths["normalized"], prepared["normalized"])
    if prepared["status"]["stage_b_status"] == "complete":
        if prepared["model_view"] is None:
            raise ValueError("Complete Stage B package lacks model view")
        validate_complete_package(prepared["linkage"], prepared["archive"],
                                  prepared["normalized"], prepared["model_view"])
        _atomic_json(paths["model_view"], prepared["model_view"])
    _atomic_json(paths["status"], prepared["status"])
    return paths
