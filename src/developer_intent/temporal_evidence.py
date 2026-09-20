"""Conservative temporal judgments and a bounded SAFE/SEALED contract."""

from __future__ import annotations

from datetime import date, datetime, timezone

from .first_generation import METHODOLOGY_VERSION


def _temporal(value: str, precision: str):
    if not value:
        return None
    if precision == "date":
        return date.fromisoformat(value)
    if precision == "timestamp":
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("Timestamp has no timezone")
        return parsed.astimezone(timezone.utc)
    raise ValueError("Unknown temporal precision")


def availability(evidence_time: dict, cutoff: dict) -> str:
    """Return YES/NO only when ordering is supported at source precision."""
    if not evidence_time.get("value") or not cutoff.get("value"):
        return "UNAVAILABLE"
    earlier = _temporal(evidence_time["value"], evidence_time["precision"])
    later = _temporal(cutoff["value"], cutoff["precision"])
    if isinstance(earlier, datetime) and isinstance(later, datetime):
        return "YES" if earlier < later else "NO" if earlier > later else "UNCERTAIN"
    first_day = earlier.date() if isinstance(earlier, datetime) else earlier
    last_day = later.date() if isinstance(later, datetime) else later
    return "YES" if first_day < last_day else "NO" if first_day > last_day else "UNCERTAIN"


def evidence_record(frozen: dict, *, evidence_id: str, artifact_id: str,
                    historical_version: str, evidence_time: dict,
                    dimension: str, bounded_fact: str, task_relevant: bool,
                    adds_beyond_frozen_conversation: bool,
                    retrieval_cue: str, retrieval_cue_turn_id: str,
                    retrieval_operation: str,
                    retrieval_path: str, provenance: dict,
                    outcome_revealing: bool = False) -> dict:
    if frozen.get("record_status") != "frozen" or frozen.get("methodology_version") != METHODOLOGY_VERSION:
        raise ValueError("Current validated frozen conversation record required")
    if dimension not in {"Context", "Specificity", "Verification"}:
        raise ValueError("Evidence dimension must be C, S, or V information")
    allowed_cues = set(frozen["allowed_prior_turn_ids"]) | {frozen["target_prompt_id"]}
    if retrieval_cue_turn_id not in allowed_cues:
        raise ValueError("Retrieval cue is not in the target prompt or allowed prior turns")
    return {"schema_version": "1", "methodology_version": METHODOLOGY_VERSION,
            "case_id": frozen["case_id"], "evidence_id": evidence_id,
            "artifact_path_or_stable_identifier": artifact_id,
            "historical_version_or_SHA": historical_version,
            "temporal_basis": evidence_time,
            "available_by_tC": availability(evidence_time, frozen["conversation_start_time"]),
            "available_by_tFG": availability(evidence_time, frozen["first_generation_cutoff"]),
            "evidence_dimension": dimension, "bounded_excerpt_or_structural_fact": bounded_fact,
            "task_relevance": task_relevant,
            "adds_beyond_frozen_conversation": adds_beyond_frozen_conversation,
            "outcome_revealing": outcome_revealing,
            "retrieval_cue": retrieval_cue, "retrieval_cue_turn_id": retrieval_cue_turn_id,
            "retrieval_operation": retrieval_operation,
            "retrieval_path": retrieval_path, "provenance": provenance,
            "primary_repository_cutoff": "tFG"}


def partition_record(frozen: dict, item: dict) -> dict:
    """Partition one bounded evidence item; raw packages are never inputs."""
    if frozen.get("record_status") != "frozen" or item.get("methodology_version") != METHODOLOGY_VERSION:
        raise ValueError("Current validated frozen record and evidence required")
    if item.get("case_id") != frozen.get("case_id") or item.get("primary_repository_cutoff") != "tFG":
        raise ValueError("Evidence case or primary cutoff mismatch")
    safe = (item["available_by_tFG"] == "YES" and item["task_relevance"] is True
            and item["outcome_revealing"] is False)
    return {"case_id": frozen["case_id"], "methodology_version": METHODOLOGY_VERSION,
            "primary_repository_cutoff": "tFG",
            "conversation_start_time": frozen["conversation_start_time"],
            "first_generation_cutoff": frozen["first_generation_cutoff"],
            "partition": "SAFE" if safe else "SEALED", "evidence": item}


def case_evidence_conclusion(frozen: dict, items: list[dict], *, review_complete: bool) -> str:
    """Permit a no-evidence conclusion only after explicit case review."""
    if not review_complete:
        return "unresolved"
    useful = any(partition_record(frozen, item)["partition"] == "SAFE"
                 and item["adds_beyond_frozen_conversation"] is True for item in items)
    return "additional_evidence_found" if useful else "no_useful_additional_repository_evidence_found"
