"""Versioned, conversation-only first-generation draft records."""

from __future__ import annotations

from copy import deepcopy

from .screening_chatgpt import _date_value, _message_turn

METHODOLOGY_VERSION = "dir-tfg-v1"
VALIDATION_KEYS = (
    "validator_id", "boundary_correct", "target_prompt_correct", "item_supported",
    "category_assignment_correct", "provenance_correct", "future_information_leakage",
)
CATEGORIES = {"Context", "Specificity", "Verification"}


def visible_events(parsed: dict) -> list[dict]:
    """Assign stable IDs from raw event positions, preserving tool gaps."""
    events = []
    for index, record in enumerate(parsed.get("records", [])):
        message = record.get("message")
        if not isinstance(message, dict):
            continue
        turn, _ = _message_turn(message)
        if turn is not None:
            events.append({"turn_id": f"turn_{index:06d}", "event_index": index,
                           "role": turn["role"], "text": turn["text"],
                           "create_time": message.get("create_time")})
    return events


def draft_record(case_id: str, parsed: dict, artifacts: list[dict] | None = None,
                 supplied_items: list[dict] | None = None,
                 record_version: str = "1", methodology_version: str = METHODOLOGY_VERSION,
                 schema_version: str = "1") -> dict:
    """Create a review draft; never infer an artifact family from text.

    `artifacts` must be independently preserved artifact references with
    artifact_id, family_id, response_event_index, and generation_order.
    The first family/response requires later human validation.
    """
    events = visible_events(parsed)
    by_index = {event["event_index"]: event for event in events}
    source = "first_user_message.create_time"
    if parsed.get("archive_provenance"):
        source += " in " + parsed["archive_provenance"].get("member", "archive")
    t_c = {"value": parsed.get("start", ""), "precision": parsed.get("precision", ""),
           "status": parsed.get("temporal_status", "unresolved"),
           "source": source if parsed.get("start") else "unresolved"}
    t_fg = {"value": "", "precision": "", "status": "unresolved", "source": "unresolved"}
    chosen = None
    target = None
    family = ""
    if artifacts:
        required = ("artifact_id", "family_id", "response_event_index", "generation_order")
        if any(not all(key in artifact for key in required) for artifact in artifacts):
            raise ValueError("Artifact references require stable identity, family, response, and order")
        first_response = min(artifact["response_event_index"] for artifact in artifacts)
        response_artifacts = [artifact for artifact in artifacts
                              if artifact["response_event_index"] == first_response]
        first_order = min(artifact["generation_order"] for artifact in response_artifacts)
        first = [artifact for artifact in response_artifacts
                 if artifact["generation_order"] == first_order]
        identities = {(artifact["family_id"], artifact["response_event_index"]) for artifact in first}
        if len(identities) != 1:
            raise ValueError("First snippet family/response is ambiguous")
        family, response_index = next(iter(identities))
        chosen = by_index.get(response_index)
        if chosen is None or chosen["role"] != "assistant":
            raise ValueError("First artifact must cite a visible assistant response")
        target = next((event for event in reversed(events)
                       if event["event_index"] < response_index and event["role"] == "user"), None)
        if target is None:
            raise ValueError("No triggering developer prompt precedes first artifact")
        value, precision = _date_value(chosen["create_time"])
        if value:
            t_fg = {"value": value, "precision": precision, "status": "derivable",
                    "source": chosen["turn_id"] + ".create_time; exclusive before response"}
    allowed = [event for event in events if target and event["event_index"] < target["event_index"]]
    permitted_ids = {event["turn_id"] for event in allowed}
    if target:
        permitted_ids.add(target["turn_id"])
    supplied = {category: [] for category in CATEGORIES}
    item_ids = set()
    for item in supplied_items or []:
        category = item.get("category")
        item_id = item.get("item_id")
        if (category not in supplied or item.get("source_turn_id") not in permitted_ids
                or not item_id or item_id in item_ids or not item.get("text")):
            raise ValueError("Supplied item lacks an admissible category and turn provenance")
        item_ids.add(item_id)
        supplied[category].append(deepcopy(item))
    return {"schema_version": schema_version, "methodology_version": methodology_version,
            "record_version": record_version,
            "case_id": case_id, "record_status": "draft", "conversation_start_time": t_c,
            "first_generation_cutoff": t_fg, "primary_repository_cutoff": "tFG",
            "first_snippet_family_id": family,
            "first_generation_response_id": chosen["turn_id"] if chosen else "",
            "target_prompt_id": target["turn_id"] if target else "",
            "target_prompt": target["text"] if target else "",
            "allowed_prior_turn_ids": [event["turn_id"] for event in allowed],
            "allowed_prior_conversation": [{"turn_id": event["turn_id"],
                                            "role": event["role"], "text": event["text"]}
                                           for event in allowed],
            "context_supplied": supplied["Context"],
            "specificity_supplied": supplied["Specificity"],
            "verification_supplied": supplied["Verification"],
            "extraction_version": ("conversation-extraction-v2" if methodology_version == "dir-tfg-v2"
                                   else "conversation-extraction-v1"),
            "validation_status": "pending", "validation_judgments": []}


def freeze_record(draft: dict, independent_judgments: list[dict],
                  expected_methodology_version: str = METHODOLOGY_VERSION) -> dict:
    """Freeze only a validated first-generation record; preserve judgments."""
    if (draft.get("record_status") != "draft"
            or draft.get("methodology_version") != expected_methodology_version
            or not draft.get("record_version")):
        raise ValueError("Expected current-version draft")
    if (not draft.get("first_snippet_family_id") or not draft.get("first_generation_response_id")
            or not draft.get("target_prompt_id") or not draft["first_generation_cutoff"]["value"]):
        raise ValueError("First-generation boundary is unresolved")
    if not independent_judgments or any(not all(key in judgment for key in VALIDATION_KEYS)
                                        for judgment in independent_judgments):
        raise ValueError("Complete independent categorical validation is required")
    expected_items = {item["item_id"] for field in ("context_supplied", "specificity_supplied",
                                                    "verification_supplied") for item in draft[field]}
    for judgment in independent_judgments:
        checks = judgment.get("items", [])
        if ({check.get("item_id") for check in checks} != expected_items or len(checks) != len(expected_items)):
            raise ValueError("Every supplied item requires an individual validation judgment")
        if any(not all(check.get(key) is True for key in
                       ("supported", "category_assignment_correct", "provenance_correct"))
               or check.get("future_information_leakage") is not False for check in checks):
            raise ValueError("A supplied item failed validation")
    if any(any(not judgment[key] for key in VALIDATION_KEYS[1:-1])
           or judgment["future_information_leakage"] for judgment in independent_judgments):
        raise ValueError("Validation found an error or future-information leakage")
    frozen = deepcopy(draft)
    frozen.update(record_status="frozen", validation_status="validated",
                  validation_judgments=deepcopy(independent_judgments))
    return frozen
