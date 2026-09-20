"""Conservative, source-traceable prompt signals for pilot screening review.

A missed lexical cue is not evidence that the characteristic is absent.
Qualitative judgments and generated-artifact relationships are deferred.
"""

from __future__ import annotations

import json
import re

SIGNAL_RULES = {
    "prompt_identifier_signal": re.compile(
        r"`[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*`|\b[A-Za-z_$][\w$]*\s*\(", re.UNICODE),
    "prompt_file_path_signal": re.compile(
        r"(?<![\w/])(?:\.{1,2}/)?(?:[\w.-]+/)+[\w.-]+|"
        r"\b[\w.-]+\.(?:py|js|jsx|ts|tsx|go|rb|rs|java|cpp|h|yaml|yml|json|md|sh|sql|html|css)\b",
        re.IGNORECASE),
    "prompt_code_fragment_signal": re.compile(
        r"```|`[^`\n]*[(){}=;][^`\n]*`|^\s*(?:def|function|class|const|let|var|import|from)\s+",
        re.MULTILINE),
    "prompt_error_log_signal": re.compile(
        r"\b(?:error|exception|traceback|stack\s+trace|warning|failed|failure|logs?)\b", re.IGNORECASE),
    "prompt_test_assertion_signal": re.compile(
        r"\b(?:tests?|pytest|unittest|assert(?:ion)?s?|expect|specs?)\b", re.IGNORECASE),
    "prompt_url_signal": re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE),
}

CONTEXT_CUE_RULES = {
    "implementation_change": re.compile(r"\b(?:implement|add|create|build|change|modify)\b", re.IGNORECASE),
    "bug_error": re.compile(r"\b(?:bug|error|exception|broken|fails?|failure|fix)\b", re.IGNORECASE),
    "test_ci_build": re.compile(r"\b(?:tests?|assert|ci|build|workflow|github actions?)\b", re.IGNORECASE),
    "refactoring": re.compile(r"\b(?:refactor|simplify|clean\s*up)\b", re.IGNORECASE),
    "api_library_usage": re.compile(r"\b(?:api|library|package|sdk)\b", re.IGNORECASE),
    "design_question": re.compile(r"\b(?:design|architecture|structure)\b", re.IGNORECASE),
    "code_review": re.compile(r"\b(?:review|feedback)\b", re.IGNORECASE),
    "issue_requirement": re.compile(r"\b(?:issue|requirement|ticket)\b", re.IGNORECASE),
    "configuration_dependency": re.compile(r"\b(?:config(?:uration)?|dependency|dependencies)\b", re.IGNORECASE),
}

SECONDARY_FIELDS = (
    "conversation_turn_pattern", "generated_artifact_pattern_status",
    *SIGNAL_RULES, "prompt_mostly_behavioral_status", "share_link_contributor_role_status",
    "help_seeking_context_status", "help_seeking_context_cues",
    "secondary_characteristics_basis", "secondary_characteristics_evidence",
)


def _first_match(prompts: list[str], pattern: re.Pattern) -> tuple[int, str] | None:
    for index, prompt in enumerate(prompts, 1):
        match = pattern.search(prompt)
        if match:
            return index, match.group(0)[:80]
    return None


def secondary_characteristics(conversation: dict | None) -> dict:
    """Record signals only from complete visible developer turns."""
    result = {field: "not_assessed" for field in SECONDARY_FIELDS}
    result["conversation_turn_pattern"] = "unavailable"
    result["help_seeking_context_cues"] = ""
    result["secondary_characteristics_basis"] = "unavailable"
    result["secondary_characteristics_evidence"] = ""
    for field in SIGNAL_RULES:
        result[field] = "unavailable"
    if not isinstance(conversation, dict) or conversation.get("complete") is not True:
        return result
    turns = conversation.get("turns")
    if not isinstance(turns, list) or not all(
        isinstance(turn, dict) and turn.get("role") in {"user", "assistant"}
        and isinstance(turn.get("text"), str) for turn in turns
    ):
        return result
    prompts = [turn["text"] for turn in turns if turn["role"] == "user"]
    result["conversation_turn_pattern"] = (
        "single_developer_prompt" if len(prompts) == 1 else
        "multiple_developer_prompts" if len(prompts) > 1 else "unavailable"
    )
    result["secondary_characteristics_basis"] = "complete_visible_developer_turns;lexical-v1"
    evidence = {}
    for field, pattern in SIGNAL_RULES.items():
        # URL substrings are not file paths or identifiers by themselves.
        searched = prompts if field == "prompt_url_signal" else [
            SIGNAL_RULES["prompt_url_signal"].sub(" ", text) for text in prompts
        ]
        hit = _first_match(searched, pattern)
        result[field] = "detected" if hit else "not_detected_by_rule"
        if hit:
            evidence[field] = {"developer_turn": hit[0], "matched_text": hit[1]}
    cues = []
    for category, pattern in CONTEXT_CUE_RULES.items():
        hit = _first_match(prompts, pattern)
        if hit:
            cues.append(category)
            evidence["cue_" + category] = {"developer_turn": hit[0], "matched_text": hit[1]}
    result["help_seeking_context_cues"] = json.dumps(cues, separators=(",", ":"))
    result["secondary_characteristics_evidence"] = json.dumps(evidence, sort_keys=True,
                                                                 separators=(",", ":"))
    return result
