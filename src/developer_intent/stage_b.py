"""Protocol v5 Stage B preparation and failure-safe persistence."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from .conversation_package import (PACKAGE_KEYS, build_case_linkage_record,
                                   build_stage_c_model_view, prepare_conversation_layers)
from .screening import (SCREENING_SCHEMA_VERSION, case_id, conversation_identity,
                        expected_stage_b_readiness, github_identity)
from .screening_chatgpt import retrieve_share
from .screening_chatgpt import parse_share, share_id

ARCHIVE_MEMBER = re.compile(r"^(\d{8})_(\d{6})_pr_sharings\.json$")
ARCHIVE_SELECTION_RULE = "earliest-valid-exact-identity-v1"
PATCHTRACK_ARCHIVE_SHA256 = "88fc6d6da50d5af0ae8864bb6b4b3a8a5002d407d9979ea8ad2e9b02e6199378"
SEMANTIC_PROJECTION_FIELDS = (
    "start", "precision", "temporal_status", "visible_turns",
    "artifact_candidates", "records", "complete", "reconstruction_safe",
)


def select_linkage(source_rows: list[dict], selected_case_id: str,
                   screened_rows: list[dict] | None = None, *,
                   screened_manifest_ref: str = "cases/manifests/screened_PA_PN_cases.csv") -> dict:
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
        expected_readiness, expected_reason = expected_stage_b_readiness(screened)
        if (screened.get("stage_b_readiness_status") != expected_readiness
                or screened.get("stage_b_readiness_reason") != expected_reason):
            raise ValueError("Stage A readiness is inconsistent with packaging prerequisites")
        if expected_readiness != "ready_for_stage_b":
            raise ValueError("Case is not operationally ready for Stage B")
        linkage_input.update(screening_schema_version=SCREENING_SCHEMA_VERSION,
                             eligibility_status=screened["eligibility_status"],
                             stage_b_readiness_status=screened["stage_b_readiness_status"],
                             case_integrity_status=screened.get("case_integrity_status", ""),
                             canonical_pr_url=screened.get("canonical_pr_url", ""),
                             stage_a_screening_record_ref=(
                                 f"{screened_manifest_ref}#case_id={selected_case_id}"),
                             source_linkage_status=screened["source_linkage_status"],
                             pr_conversation_match=screened["pr_conversation_match"],
                             correspondence_review_ref=(
                                 "cases/manifests/correspondence_reviews/"
                                 f"{selected_case_id}.json"))
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
    if archive.get("source_origin") == "archived_http_response":
        provenance = archive.get("archived_http_import")
        if (archive.get("archive_version") != "chatgpt-source-v3"
                or archive.get("retrieved_at") is not None
                or archive.get("retrieval_time_status") != "unknown_archive_timezone"
                or not isinstance(provenance, dict)
                or provenance.get("embedded_field") != "HTMLContent"
                or provenance.get("original_vs_derived") != "original_archived_http_response"
                or provenance.get("selection_rule") != ARCHIVE_SELECTION_RULE
                or provenance.get("share_id") != linkage.get("conversation_id")
                or provenance.get("expected_pr_url") != linkage.get("pr_url")
                or provenance.get("archived_http_status") != 200
                or provenance.get("embedded_content_sha256") != archive.get("source_sha256")
                or not isinstance(provenance.get("qualifying_candidates"), list)
                or not provenance["qualifying_candidates"]):
            raise ValueError("Archived HTTP provenance is invalid")
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


def canonical_json_hash(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def semantic_model_projection(model_view: dict) -> dict:
    """Return the model-visible semantic fields used for source equivalence."""
    return {key: model_view[key] for key in SEMANTIC_PROJECTION_FIELDS}


def semantic_model_hash(model_view: dict) -> str:
    """SHA-256 of compact, key-sorted UTF-8 JSON over the semantic projection."""
    return canonical_json_hash(semantic_model_projection(model_view))


def _aware_import_time(value: str | None, label: str) -> str:
    imported = value or datetime.now(timezone.utc).isoformat()
    try:
        if datetime.fromisoformat(imported.replace("Z", "+00:00")).tzinfo is None:
            raise ValueError
    except (AttributeError, ValueError) as exc:
        raise ValueError(f"{label} import time must be timezone-aware") from exc
    return imported


def select_archived_http_response(linkage: dict, archive_path: Path, *,
                                  expected_archive_sha256: str | None = None) -> dict:
    """Select the earliest valid exact-identity HTMLContent snapshot offline."""
    if not archive_path.is_file():
        raise ValueError(f"Archived HTTP source ZIP is missing: {archive_path}")
    archive_bytes = archive_path.read_bytes()
    archive_sha = hashlib.sha256(archive_bytes).hexdigest()
    if expected_archive_sha256 and archive_sha != expected_archive_sha256:
        raise ValueError("Archived HTTP source ZIP checksum mismatch")
    expected_share = linkage["conversation_id"]
    expected_pr = linkage["pr_url"]
    qualifying = []
    try:
        bundle = zipfile.ZipFile(archive_path)
    except zipfile.BadZipFile as exc:
        raise ValueError("Archived HTTP source ZIP is malformed") from exc
    with bundle:
        for member in sorted(bundle.namelist()):
            match = ARCHIVE_MEMBER.fullmatch(member)
            if match is None:
                continue
            member_bytes = bundle.read(member)
            try:
                document = json.loads(member_bytes)
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            sources = document.get("Sources") if isinstance(document, dict) else None
            if not isinstance(sources, list):
                continue
            for source_index, source in enumerate(sources):
                if not isinstance(source, dict) or source.get("URL") != expected_pr:
                    continue
                sharings = source.get("ChatgptSharing")
                if not isinstance(sharings, list):
                    continue
                for sharing_index, sharing in enumerate(sharings):
                    if (not isinstance(sharing, dict)
                            or share_id(sharing.get("URL", "")) != expected_share
                            or sharing.get("Status") != 200):
                        continue
                    payload_text = sharing.get("HTMLContent")
                    if not isinstance(payload_text, str) or not payload_text:
                        continue
                    payload = payload_text.encode("utf-8")
                    try:
                        parsed = parse_share(payload, "text/html")
                    except ValueError:
                        continue
                    if parsed.get("complete") is not True:
                        continue
                    candidate = {
                        "archive_member": member,
                        "archive_snapshot_timestamp_raw": f"{match.group(1)}_{match.group(2)}",
                        "archive_member_sha256": hashlib.sha256(member_bytes).hexdigest(),
                        "source_index": source_index,
                        "sharing_index": sharing_index,
                        "embedded_content_sha256": hashlib.sha256(payload).hexdigest(),
                        "DateOfAccess_raw": sharing.get("DateOfAccess"),
                        "DateOfConversation_raw": sharing.get("DateOfConversation"),
                    }
                    qualifying.append({"selection_key": (
                        match.group(1), match.group(2), member, source_index, sharing_index),
                        "candidate": candidate, "payload": payload,
                        "sharing_url": sharing["URL"]})
    if not qualifying:
        raise ValueError("No qualifying archived HTTP response for exact case/share/PR identity")
    qualifying.sort(key=lambda item: item["selection_key"])
    selected = qualifying[0]
    candidates = [item["candidate"] for item in qualifying]
    return {
        "payload": selected["payload"], "sharing_url": selected["sharing_url"],
        "archive_sha256": archive_sha, "selected": selected["candidate"],
        "qualifying_candidates": candidates,
        "selection_reason": (
            "earliest qualifying archive filename timestamp; lexical archive-member, "
            "source-index, and sharing-index tie-break"),
    }


def prepare_stage_b_from_archived_http(linkage: dict, archive_path: Path, *,
                                       imported_at: str | None = None,
                                       expected_archive_sha256: str | None = None) -> dict:
    """Package original HTMLContent from the identity-matched replication ZIP."""
    selected = select_archived_http_response(
        linkage, archive_path, expected_archive_sha256=expected_archive_sha256)
    payload = selected["payload"]
    imported = _aware_import_time(imported_at, "Archived HTTP")
    chosen = selected["selected"]
    canonical = f"https://chatgpt.com/share/{linkage['conversation_id']}"
    provenance = {
        "archive_path": archive_path.as_posix(),
        "archive_sha256": selected["archive_sha256"],
        **chosen,
        "embedded_field": "HTMLContent",
        "source_format": "next_data_html",
        "share_id": linkage["conversation_id"],
        "canonical_share_url": canonical,
        "expected_pr_url": linkage["pr_url"],
        "source_dataset": "PatchTrack allPullRequestSharings replication archive",
        "source_dataset_version": None,
        "original_vs_derived": "original_archived_http_response",
        "archived_http_status": 200,
        "parser_version": "screening-chatgpt-structured-v1",
        "normalization_version": "lossless-conversation-v1",
        "selection_rule": ARCHIVE_SELECTION_RULE,
        "selection_reason": selected["selection_reason"],
        "qualifying_candidates": selected["qualifying_candidates"],
        "imported_at": imported,
    }
    archive, normalized, model_view = prepare_conversation_layers(
        linkage["case_id"], payload, source_url=linkage["conversation_url"],
        retrieval_status="retrieved_public", retrieved_at="", content_type="text/html",
        http_status=200, final_url=selected["sharing_url"],
        source_origin="archived_http_response", archived_http_import=provenance)
    if normalized is None or model_view is None:
        raise ValueError("Archived HTMLContent did not produce a complete current-parser package")
    validate_complete_package(linkage, archive, normalized, model_view)
    return {"linkage": linkage, "archive": archive, "normalized": normalized,
            "model_view": model_view,
            "status": {"case_id": linkage["case_id"], "stage_b_status": "complete",
                       "stage_a_eligibility_status": linkage["stage_a_eligibility_status"],
                       "stage_b_readiness_status": linkage["stage_b_readiness_status"],
                       "screening_schema_version": linkage["screening_schema_version"],
                       "retrieval_status": "retrieved_public", "parsing_status": "parsed",
                       "source_origin": "archived_http_response",
                       "retrieval_time_status": "unknown_archive_timezone",
                       "package_validation_status": "validated",
                       "model_view_sha256": canonical_json_hash(model_view),
                       "semantic_projection_sha256": semantic_model_hash(model_view)}}


def legacy_cache_paths(legacy_root: Path, conversation_url: str) -> tuple[Path, Path, str]:
    identity = share_id(conversation_url)
    if identity is None:
        raise ValueError("Legacy import requires a valid conversation URL")
    canonical = f"https://chatgpt.com/share/{identity}"
    key = hashlib.sha256(f"{canonical}|public".encode("utf-8")).hexdigest()
    return legacy_root / f"{key}.body", legacy_root / f"{key}.json", canonical


def prepare_stage_b_from_legacy(linkage: dict, legacy_root: Path, *,
                                imported_at: str | None = None,
                                expected_model_view_sha256: str | None = None) -> dict:
    """Validate and package one preserved raw response, without any network fallback."""
    body_path, metadata_path, canonical = legacy_cache_paths(
        legacy_root, linkage["conversation_url"])
    if not body_path.is_file():
        raise ValueError(f"Legacy raw body is missing: {body_path}")
    if not metadata_path.is_file():
        raise ValueError(f"Legacy metadata is missing: {metadata_path}")
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("Legacy metadata is malformed") from exc
    if metadata.get("status") != "retrieved_public":
        raise ValueError("Legacy retrieval status is not retrieved_public")
    if metadata.get("http_status") != 200:
        raise ValueError("Legacy HTTP status is not 200")
    if share_id(metadata.get("final_url", "")) != share_id(canonical):
        raise ValueError("Legacy final URL conversation identity mismatch")
    payload = body_path.read_bytes()
    if not payload:
        raise ValueError("Legacy raw body is empty")
    try:
        parsed = parse_share(payload, "")
    except ValueError as exc:
        raise ValueError("Legacy raw body is unsupported or malformed") from exc
    if parsed.get("complete") is not True:
        raise ValueError("Legacy parsed conversation is incomplete")
    imported = _aware_import_time(imported_at, "Legacy")
    provenance = {
        "legacy_body_path": body_path.as_posix(),
        "legacy_metadata_path": metadata_path.as_posix(),
        "raw_body_sha256": hashlib.sha256(payload).hexdigest(),
        "canonical_conversation_url": canonical,
        "legacy_final_url": metadata["final_url"],
        "legacy_http_status": metadata["http_status"],
        "legacy_retrieval_status": metadata["status"],
        "imported_at": imported,
    }
    archive, normalized, model_view = prepare_conversation_layers(
        linkage["case_id"], payload, source_url=linkage["conversation_url"],
        retrieval_status=metadata["status"], retrieved_at="", content_type="",
        http_status=metadata["http_status"], final_url=metadata["final_url"],
        source_origin="legacy_cache_import", legacy_import=provenance)
    if normalized is None or model_view is None:
        raise ValueError("Legacy raw body did not produce a complete current-parser package")
    model_hash = canonical_json_hash(model_view)
    if expected_model_view_sha256 and model_hash != expected_model_view_sha256:
        raise ValueError("Legacy model-view equivalence hash mismatch")
    validate_complete_package(linkage, archive, normalized, model_view)
    return {"linkage": linkage, "archive": archive, "normalized": normalized,
            "model_view": model_view,
            "status": {"case_id": linkage["case_id"], "stage_b_status": "complete",
                       "stage_a_eligibility_status": linkage["stage_a_eligibility_status"],
                       "stage_b_readiness_status": linkage["stage_b_readiness_status"],
                       "screening_schema_version": linkage["screening_schema_version"],
                       "retrieval_status": metadata["status"], "parsing_status": "parsed",
                       "source_origin": "legacy_cache_import",
                       "retrieval_time_status": "unknown_legacy_cache",
                       "package_validation_status": "validated",
                       "model_view_sha256": model_hash}}


def existing_package_status(root: Path, case_id: str) -> str:
    """Return existing_valid, incomplete, or absent without changing artifacts."""
    paths = output_paths(root, case_id)
    if not any(path.exists() for path in paths.values()):
        return "absent"
    if not all(paths[name].exists() for name in paths):
        return "incomplete"
    try:
        values = {name: json.loads(path.read_text(encoding="utf-8"))
                  for name, path in paths.items()}
        if values["status"].get("stage_b_status") != "complete":
            return "incomplete"
        validate_complete_package(values["linkage"], values["source_archive"],
                                  values["normalized"], values["model_view"])
    except (OSError, json.JSONDecodeError, ValueError):
        return "incomplete"
    return "existing_valid"


def preserve_incomplete_outputs(root: Path, case_id: str) -> list[Path]:
    """Move an incomplete attempt into checksum-addressed history before replacement."""
    paths = output_paths(root, case_id)
    existing = {name: path for name, path in paths.items() if path.exists()}
    if not existing:
        return []
    if existing_package_status(root, case_id) == "existing_valid":
        raise FileExistsError("Existing valid Stage B package cannot be replaced")
    digest = hashlib.sha256(b"".join(path.read_bytes() for path in existing.values())).hexdigest()[:16]
    history = root / "cases/manifests/stage_b_attempts" / case_id / digest
    if history.exists():
        raise FileExistsError(f"Stage B attempt history exists: {history}")
    history.mkdir(parents=True)
    moved = []
    for name, path in existing.items():
        destination = history / f"{name}.json"
        path.rename(destination)
        moved.append(destination)
    return moved


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
