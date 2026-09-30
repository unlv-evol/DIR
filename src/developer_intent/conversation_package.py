"""Protocol v5 isolation boundary for conversation-side extraction."""

from __future__ import annotations

import hashlib
import json
import re
import base64
from copy import deepcopy
from datetime import datetime
from urllib.parse import urlparse

from .first_generation import draft_record, freeze_record, visible_events
from .screening_chatgpt import parse_share, share_id

METHODOLOGY_VERSION = "dir-tfg-v2"
FORBIDDEN_INPUT_KEYS = {"pr", "repository", "pr_url", "Outcome_Class", "files",
                        "commits", "final_diff", "integrated_implementation"}
PACKAGE_KEYS = {"package_version", "methodology_version", "case_id", "start",
                "precision", "temporal_status", "temporal_source",
                "source_conversation_sha256", "visible_turns", "artifact_candidates", "records",
                "complete", "reconstruction_safe"}
FENCE = re.compile(r"^```([^\n]*)\n(.*?)^```[ \t]*(?=\n|\Z)", re.MULTILINE | re.DOTALL)


def build_case_linkage_record(screened_row: dict) -> dict:
    """Restricted administrative crosswalk; never pass this to Stage C."""
    required = ("case_id", "source_case_id", "pr_url", "conversation_id",
                "conversation_url", "Outcome_Class")
    if not all(screened_row.get(key) for key in required):
        raise ValueError("Screened case lacks required linkage identity")
    return {"linkage_version": "case-linkage-v2", "methodology_version": METHODOLOGY_VERSION,
            **{key: screened_row[key] for key in required},
            "repository": screened_row.get("repository", ""),
            "pr_number": screened_row.get("pr_number", ""),
            "canonical_pr_url": screened_row.get("canonical_pr_url", ""),
            "case_integrity_status": screened_row.get("case_integrity_status", ""),
            "integrity_notes": screened_row.get("integrity_notes", ""),
            "screening_schema_version": screened_row.get("screening_schema_version", ""),
            "stage_a_eligibility_status": screened_row.get("eligibility_status", "not_checked_technical_smoke"),
            "stage_b_readiness_status": screened_row.get("stage_b_readiness_status", "not_checked_technical_smoke"),
            "stage_a_screening_record_ref": screened_row.get("stage_a_screening_record_ref", ""),
            "source_linkage_status": screened_row.get("source_linkage_status", "not_checked_technical_smoke"),
            "pr_conversation_match": screened_row.get("pr_conversation_match", "not_checked_technical_smoke"),
            "correspondence_review_ref": screened_row.get("correspondence_review_ref", "")}


def build_source_archive(case_id: str, source_payload: bytes, *, source_url: str,
                         retrieval_status: str, retrieved_at: str,
                         content_type: str = "", http_status: int | None = None,
                         final_url: str = "", source_origin: str = "unknown") -> dict:
    """Preserve source bytes and allowlisted provenance, never request credentials."""
    if not case_id or not isinstance(source_payload, bytes) or not source_payload:
        raise ValueError("Source archive requires case ID and retrieved payload")
    if share_id(source_url) is None or urlparse(source_url).query or urlparse(source_url).fragment:
        raise ValueError("Source archive requires a public share URL")
    if final_url:
        parsed_final = urlparse(final_url)
        if (parsed_final.scheme != "https" or parsed_final.hostname not in
                {"chatgpt.com", "chat.openai.com"} or parsed_final.username
                or parsed_final.password or parsed_final.query or parsed_final.fragment
                or (share_id(final_url) is None and not re.fullmatch(
                    r"/backend-api/share/[0-9a-fA-F-]{36}", parsed_final.path))):
            raise ValueError("Final source URL cannot contain credentials")
    if source_origin not in {"fresh", "cached", "unknown"}:
        raise ValueError("Unsupported source origin")
    if retrieved_at:
        try:
            if datetime.fromisoformat(retrieved_at.replace("Z", "+00:00")).tzinfo is None:
                raise ValueError
        except (AttributeError, ValueError) as exc:
            raise ValueError("Retrieval time requires a source-supported timezone") from exc
    source_prefix = source_payload.lstrip()[:200]
    source_format = ("structured_json" if source_prefix.startswith((b"{", b"[")) else
                     "next_data_html" if b"__NEXT_DATA__" in source_payload else
                     "react_router_html" if b"streamController.enqueue(" in source_payload else
                     "unrecognized")
    return {"archive_version": "chatgpt-source-v1", "case_id": case_id,
            "source_url": source_url, "final_url": final_url,
            "retrieved_at": retrieved_at, "retrieval_status": retrieval_status,
            "retrieval_time_status": "recorded" if retrieved_at else "unknown_legacy_cache",
            "source_origin": source_origin,
            "http_status": http_status, "content_type": content_type,
            "source_format": source_format,
            "parser_version": "screening-chatgpt-structured-v1",
            "source_sha256": hashlib.sha256(source_payload).hexdigest(),
            "source_payload_base64": base64.b64encode(source_payload).decode("ascii")}


def normalize_conversation(case_id: str, parsed_conversation: dict,
                           source_archive: dict | None = None) -> dict:
    """Keep all parsed source records, including tool and later records."""
    if not case_id or not isinstance(parsed_conversation, dict):
        raise ValueError("A neutral case ID and parsed conversation are required")
    if FORBIDDEN_INPUT_KEYS.intersection(parsed_conversation):
        raise ValueError("Conversation package input contains project/outcome material")
    if parsed_conversation.get("complete") is not True or not isinstance(
        parsed_conversation.get("records"), list
    ):
        raise ValueError("A complete ordered conversation is required")
    events = visible_events(parsed_conversation)
    if not events or not any(event["role"] == "user" for event in events):
        raise ValueError("No visible developer turns")
    if source_archive is not None and (source_archive.get("case_id") != case_id
                                       or source_archive.get("archive_version") != "chatgpt-source-v1"):
        raise ValueError("Source archive and normalized conversation identity differ")
    original = parsed_conversation["records"]
    turns = []
    for event in events:
        position = event["event_index"]
        record = original[position]
        turns.append({**{key: event[key] for key in
                         ("turn_id", "event_index", "role", "text", "create_time")},
                      "source_record_index": position,
                      "source_node_id": record.get("node_id"),
                      "source_parent_id": record.get("parent")})
    candidates = []
    for turn in turns:
        if turn["role"] != "assistant":
            continue
        for ordinal, match in enumerate(FENCE.finditer(turn["text"]), 1):
            candidates.append({
                "artifact_id": f"ARTIFACT_{turn['event_index']:06d}_{ordinal:03d}",
                "source_response_id": turn["turn_id"],
                "response_event_index": turn["event_index"],
                "source_record_index": turn["source_record_index"],
                "order_within_response": ordinal,
                "fence_label": match.group(1).strip(),
                "content": match.group(2),
                "status": "candidate_requires_review",
            })
    limitations = []
    if source_archive is None:
        limitations.append("retrieved_source_payload_not_attached")
    elif source_archive.get("source_format") in {"next_data_html", "react_router_html"}:
        limitations.append("html_source_envelope_preserved_only_in_source_archive")
    if parsed_conversation.get("raw_conversation") is None:
        limitations.append("raw_conversation_structure_not_available")
    for index, record in enumerate(original):
        if record.get("message") is None:
            limitations.append(f"non_message_source_record_preserved:{index}")
    return {"normalized_version": "lossless-conversation-v1",
            "methodology_version": METHODOLOGY_VERSION,
            "case_id": case_id,
            "start": parsed_conversation.get("start", ""),
            "precision": parsed_conversation.get("precision", ""),
            "temporal_status": parsed_conversation.get("temporal_status", "unresolved"),
            "temporal_source": "first developer turn in parsed conversation",
            "source_archive_sha256": source_archive.get("source_sha256", "") if source_archive else "",
            "source_conversation_sha256": hashlib.sha256(json.dumps(
                parsed_conversation.get("raw_conversation", original), sort_keys=True,
                ensure_ascii=False).encode("utf-8")).hexdigest(),
            "visible_turns": turns,
            "artifact_candidates": candidates,
            "records": deepcopy(original),
            "tool_trace": deepcopy(parsed_conversation.get("tool_trace", [])),
            "other_records": deepcopy(parsed_conversation.get("other_records", [])),
            "raw_conversation": deepcopy(parsed_conversation.get("raw_conversation")),
            "normalization_limitations": limitations,
            "complete": True,
            "reconstruction_safe": False}


def prepare_conversation_layers(case_id: str, source_payload: bytes, *,
                                source_url: str, retrieval_status: str,
                                retrieved_at: str, content_type: str = "",
                                http_status: int | None = None,
                                final_url: str = "",
                                source_origin: str = "unknown") -> tuple[dict, dict | None, dict | None]:
    """Build archive, normalized record, and isolated model view from one source."""
    archive = build_source_archive(case_id, source_payload, source_url=source_url,
                                   retrieval_status=retrieval_status,
                                   retrieved_at=retrieved_at, content_type=content_type,
                                   http_status=http_status, final_url=final_url,
                                   source_origin=source_origin)
    try:
        parsed = parse_share(source_payload, content_type)
    except ValueError as exc:
        archive["normalization_status"] = "unsupported_or_malformed"
        archive["normalization_error"] = str(exc)
        return archive, None, None
    archive["normalization_status"] = "parsed"
    normalized = normalize_conversation(case_id, parsed, archive)
    return archive, normalized, build_stage_c_model_view(normalized)


def build_stage_c_model_view(normalized: dict) -> dict:
    """Expose only conversation-addressed turns; retain raw source separately."""
    if normalized.get("normalized_version") != "lossless-conversation-v1":
        raise ValueError("Expected lossless normalized conversation")
    if FORBIDDEN_INPUT_KEYS.intersection(normalized):
        raise ValueError("Normalized conversation contains administrative metadata")
    turns = normalized["visible_turns"]
    sanitized_records = [{} for _ in normalized["records"]]
    for turn in turns:
        sanitized_records[turn["event_index"]] = {"message": {
            "author": {"role": turn["role"]},
            "content": {"content_type": "text", "parts": [turn["text"]]},
            "create_time": turn["create_time"]}}
    return {"package_version": "conversation-only-v1",
            "methodology_version": METHODOLOGY_VERSION,
            "case_id": normalized["case_id"], "start": normalized["start"],
            "precision": normalized["precision"],
            "temporal_status": normalized["temporal_status"],
            "temporal_source": normalized["temporal_source"],
            "source_conversation_sha256": normalized["source_conversation_sha256"],
            "visible_turns": deepcopy(turns),
            "artifact_candidates": deepcopy(normalized["artifact_candidates"]),
            "records": sanitized_records, "complete": True,
            "reconstruction_safe": False}


def build_conversation_package(case_id: str, parsed_conversation: dict) -> dict:
    """Compatibility wrapper for a Stage C view; use normalize for archival work."""
    return build_stage_c_model_view(normalize_conversation(case_id, parsed_conversation))


def draft_supplied_record(package: dict, artifact_refs: list[dict],
                          supplied_items: list[dict], record_version: str = "1") -> dict:
    """Stage C may receive this package and conversation artifact references only."""
    if (package.get("package_version") != "conversation-only-v1"
            or package.get("methodology_version") != METHODOLOGY_VERSION
            or set(package) != PACKAGE_KEYS):
        raise ValueError("Expected an isolated Protocol v5 conversation package")
    candidates = {(candidate["artifact_id"], candidate["response_event_index"])
                  for candidate in package["artifact_candidates"]}
    if any((ref.get("artifact_id"), ref.get("response_event_index")) not in candidates
           for ref in artifact_refs):
        raise ValueError("Artifact reference is not present in the conversation package")
    turn_text = {turn["turn_id"]: turn["text"] for turn in package["visible_turns"]}
    if any(not isinstance(item.get("text"), str)
           or item["text"] not in turn_text.get(item.get("source_turn_id"), "")
           for item in supplied_items):
        raise ValueError("Supplied item must be supported by its cited conversation turn")
    draft = draft_record(package["case_id"], package, artifacts=artifact_refs,
                         supplied_items=supplied_items, record_version=record_version,
                         methodology_version=METHODOLOGY_VERSION,
                         schema_version="conversation-draft-v2")
    draft["conversation_package_sha256"] = hashlib.sha256(
        json.dumps(package, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    return draft


def freeze_validated_record(
    draft: dict, *, procedure_validation_status: str,
    stage_a_eligibility_status: str,
    case_human_validation_status: str, case_extraction_status: str,
    case_boundary_status: str, case_processability_status: str,
    independent_judgments: list[dict] | None = None,
    adjudication_record: dict | None = None,
    systematic_defect_affects_case: bool = False,
) -> dict:
    """Freeze a processable v5 record under a validated extraction procedure.

    Sampling is recorded independently; an unsampled case is never called
    individually human validated. The caller retains earlier versions.
    """
    judgments = independent_judgments or []
    human_statuses = {"not_sampled", "sampled_human_validated", "sampled_adjudicated"}
    if (draft.get("methodology_version") != METHODOLOGY_VERSION
            or draft.get("record_status") != "draft"
            or procedure_validation_status != "validated"
            or stage_a_eligibility_status != "eligible"
            or case_human_validation_status not in human_statuses
            or case_extraction_status != "completed"
            or case_boundary_status != "established"
            or case_processability_status != "passed"
            or systematic_defect_affects_case
            or not draft.get("record_version")
            or not draft.get("first_snippet_family_id")
            or not draft.get("first_generation_response_id")
            or not draft.get("target_prompt_id")
            or not draft.get("first_generation_cutoff", {}).get("value")
            or draft["first_generation_cutoff"].get("status") in {"unresolved", "unavailable"}):
        raise ValueError("Unvalidated procedure or unresolved case cannot be frozen")
    if case_human_validation_status == "not_sampled":
        if judgments or adjudication_record:
            raise ValueError("Unsampled case cannot carry individual validation judgments")
        frozen = deepcopy(draft)
        frozen["record_status"] = "frozen"
    else:
        reviewer_ids = [judgment.get("validator_id") for judgment in judgments]
        if len(reviewer_ids) < 2 or len(set(reviewer_ids)) != len(reviewer_ids):
            raise ValueError("Sampled case needs two independent reviewers")
        if case_human_validation_status == "sampled_adjudicated" and not adjudication_record:
            raise ValueError("Adjudicated status requires an adjudication record")
        frozen = freeze_record(draft, judgments,
                               expected_methodology_version=METHODOLOGY_VERSION)
    frozen.update(procedure_validation_status=procedure_validation_status,
                  stage_a_eligibility_status=stage_a_eligibility_status,
                  case_human_validation_status=case_human_validation_status,
                  case_extraction_status=case_extraction_status,
                  case_boundary_status=case_boundary_status,
                  case_processability_status=case_processability_status,
                  validation_status="procedure_validated",
                  validation_judgments=deepcopy(judgments),
                  adjudication_record=deepcopy(adjudication_record))
    return frozen
