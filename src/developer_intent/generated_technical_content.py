"""Deterministic Stage B V2 generated-technical-content candidates."""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from copy import deepcopy

METHODOLOGY_VERSION = "dir-tfg-v2"
PACKAGE_VERSION = "conversation-only-v2"
PRODUCER_VERSION = "generated-technical-content-v2"
STATUS = "candidate_requires_semantic_review"
GTC_ID = re.compile(r"GTC_[0-9]{6}_[0-9]{6}_[0-9]{6}_[0-9a-f]{16}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")

KINDS = {"source_code", "structured_xml_markup", "shell_sequence",
         "configuration_properties", "structured_json", "unclassified_technical"}
CONTAINERS = {"markdown_fence", "none"}
COMPLETENESS = {"complete", "fragment", "open_ended"}
CONTINUATIONS = {"none", "begins_mid_structure", "ends_mid_structure", "both"}

_DELIMITER = re.compile(r"^([ \t]*)```([^`\r\n]*)[ \t]*$")
_TAG = re.compile(r"</?[A-Za-z][A-Za-z0-9:_-]*(?:\s+[^<>]*)?/?>")
_PAIRED_TAG = re.compile(
    r"<([A-Za-z][A-Za-z0-9:_-]*)(?:\s+[^<>]*)?>.*?</\1\s*>", re.DOTALL)
_SELF_CLOSING = re.compile(r"<[A-Za-z][A-Za-z0-9:_-]*(?:\s+[^<>]*)?/\s*>")
_PARTIAL_TAG = re.compile(r"<[A-Za-z][^>]*\Z")
_LANG_SOURCE = {"python", "py", "javascript", "js", "typescript", "ts", "java",
                "c", "cpp", "c++", "csharp", "cs", "go", "rust", "ruby", "php",
                "swift", "kotlin", "scala", "sql", "r"}
_LANG_SHELL = {"bash", "sh", "shell", "zsh", "powershell", "pwsh"}
_LANG_CONFIG = {"ini", "properties", "env", "config", "conf", "toml"}
_LANG_MARKUP = {"xml", "html", "svg"}


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def candidate_id(event: int, start: int, end: int, raw_hash: str) -> str:
    """Create a semantic-field-independent candidate identifier."""
    if min(event, start, end) < 0 or end < start or not SHA256.fullmatch(raw_hash):
        raise ValueError("Cannot identify a malformed candidate span")
    return f"GTC_{event:06d}_{start:06d}_{end:06d}_{raw_hash[:16]}"


def _lines(text: str) -> list[tuple[int, int, str]]:
    result = []
    offset = 0
    for line in text.splitlines(keepends=True):
        content = line.rstrip("\r\n")
        result.append((offset, offset + len(line), content))
        offset += len(line)
    if offset < len(text) or not result:
        result.append((offset, len(text), text[offset:]))
    return result


def _markup_facts(text: str) -> tuple[bool, list[str], str, str]:
    stripped = text.strip()
    tags = _TAG.findall(text)
    paired = _PAIRED_TAG.findall(text)
    self_closing = _SELF_CLOSING.findall(text)
    software = bool(re.search(r"<(?:resources|string-array|html|body|div|svg)\b", text, re.I))
    resource = len(re.findall(r"<string\s+name\s*=\s*['\"][^'\"]+['\"]", text, re.I))
    root_nested = bool(re.search(
        r"<([A-Za-z][\w:-]*)\b[^>]*>.*<[A-Za-z][\w:-]*\b[^>]*>.*</\1\s*>",
        text, re.I | re.S))
    nonblank = [line for line in text.splitlines() if line.strip()]
    dominated = bool(nonblank) and sum(bool(_TAG.search(line)) for line in nonblank) / len(nonblank) >= .6
    qualified = (root_nested or len(paired) + len(self_closing) >= 2 or resource >= 2
                 or software and (bool(paired) or len(tags) >= 2)) and dominated
    if not qualified:
        return False, [], "fragment", "none"
    evidence = []
    if resource >= 2:
        evidence.extend(["android_string_resources", "repeated_paired_elements"])
    if root_nested:
        evidence.append("nested_root_structure")
    if software:
        evidence.append("recognized_software_markup")
    partial = bool(_PARTIAL_TAG.search(stripped)) or (resource and
              len(re.findall(r"</string\s*>", text, re.I)) < resource)
    if partial:
        evidence.append("partial_trailing_element")
    complete = not partial and bool(tags) and (root_nested or
        bool(re.search(r"</(?:resources|string-array|html|body|svg)\s*>\s*\Z", stripped, re.I))
        or len(paired) + len(self_closing) >= 2)
    return True, list(dict.fromkeys(evidence)), "complete" if complete else "fragment", \
        "none" if complete else "ends_mid_structure"


def _json_kind(text: str) -> bool:
    try:
        value = json.loads(text.strip())
    except (ValueError, TypeError):
        return False
    return isinstance(value, (dict, list))


def _shell_facts(text: str) -> tuple[bool, list[str]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()
             and not line.lstrip().startswith("# ")]
    commands = re.compile(r"^(?:[$#>]\s*)?(?:[A-Z_][A-Z0-9_]*=\S+\s+)?(?:git|cd|ls|cp|mv|rm|find|grep|sed|awk|cat|echo|npm|npx|yarn|pnpm|pip|python\d*|pytest|make|curl|wget|docker|kubectl|go|cargo|java|javac|node|export)\b")
    matched = [line for line in lines if commands.match(line)]
    strong = any(re.search(r"(?:\||&&|\|\||>>?|<|\\\s*$)", line) for line in matched)
    env_exec = any(re.match(r"^[A-Z_][A-Z0-9_]*=\S+\s+\S+", line) for line in lines)
    ok = len(matched) >= 2 or (len(matched) == 1 and (strong or env_exec))
    evidence = (["multiple_standalone_commands"] if len(matched) >= 2 else [])
    if strong:
        evidence.append("strong_shell_operator")
    if env_exec:
        evidence.append("environment_assignment_execution")
    return ok, evidence


def _config_facts(text: str) -> tuple[bool, list[str]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()
             and not line.strip().startswith(("#", ";"))]
    env = [x for x in lines if re.match(r"^[A-Z_][A-Z0-9_]*\s*=", x)]
    dotted = [x for x in lines if re.match(r"^[A-Za-z][\w-]*(?:\.[\w-]+)+\s*=", x)]
    sections = [x for x in lines if re.match(r"^\[[^\]\r\n]+\]$", x)]
    assignments = [x for x in lines if re.match(r"^[A-Za-z][\w.-]*\s*[=:]", x)]
    evidence = []
    if len(env) >= 2:
        evidence.append("multiple_environment_assignments")
    if len(dotted) >= 2:
        evidence.append("multiple_dotted_properties")
    if sections and assignments:
        evidence.append("ini_section_with_assignment")
    return bool(evidence), evidence


def _source_facts(text: str) -> tuple[bool, list[str]]:
    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) < 3:
        return False, []
    patterns = {
        "import_or_include": re.compile(r"^\s*(?:import\s|from\s+\S+\s+import|#include\b|using\s+\S)", re.M),
        "declaration": re.compile(r"^\s*(?:def|class|interface|function|func|type|public|private|protected|const|let|var)\b", re.M),
        "control_flow": re.compile(r"^\s*(?:if|for|while|switch|try|catch|return)\b", re.M),
        "braces": re.compile(r"[{}]"),
        "statement_terminators": re.compile(r";\s*$", re.M),
        "call_expression": re.compile(r"\b[A-Za-z_]\w*\s*\([^\n)]*\)"),
    }
    features = [name for name, pattern in patterns.items() if pattern.search(text)]
    code_like = sum(bool(re.search(r"(?:[{};]|\b(?:def|class|function|const|let|var|if|for|return|import)\b|\w+\s*\([^)]*\))", line)) for line in lines)
    return len(features) >= 2 and code_like / len(lines) >= .6, features


def classify_payload(text: str, label: str = "") -> tuple[str, list[str]]:
    """Classify bounded technical content without turning the label into identity."""
    markup, evidence, _, _ = _markup_facts(text)
    if markup:
        return "structured_xml_markup", evidence
    if _json_kind(text):
        return "structured_json", ["parser_valid_bounded_json"]
    shell, evidence = _shell_facts(text)
    if shell or label.lower() in _LANG_SHELL:
        return "shell_sequence", evidence or ["recognized_fence_label"]
    config, evidence = _config_facts(text)
    if config or label.lower() in _LANG_CONFIG:
        return "configuration_properties", evidence or ["recognized_fence_label"]
    source, evidence = _source_facts(text)
    if source or label.lower() in _LANG_SOURCE:
        return "source_code", evidence or ["recognized_fence_label"]
    if label.lower() in _LANG_MARKUP:
        return "structured_xml_markup", ["recognized_fence_label"]
    return "unclassified_technical", []


def _fenced_spans(text: str) -> tuple[list[dict], list[tuple[int, int]]]:
    lines = _lines(text)
    spans, blocked = [], []
    index = 0
    while index < len(lines):
        start, line_end, line = lines[index]
        match = _DELIMITER.fullmatch(line)
        if not match:
            index += 1
            continue
        indent, info = match.group(1), match.group(2).strip()
        close_index = None
        ambiguous = False
        probe = index + 1
        while probe < len(lines):
            nested = _DELIMITER.fullmatch(lines[probe][2])
            if not nested:
                probe += 1
                continue
            nested_indent, nested_info = nested.group(1), nested.group(2).strip()
            if nested_indent == indent and not nested_info:
                close_index = probe
                break
            if nested_indent == indent:
                ambiguous = True
                break
            # A differently indented delimiter pair is a nested literal region.
            # Skip it only when its matching closer is unambiguous.
            nested_close = None
            for nested_probe in range(probe + 1, len(lines)):
                possible = _DELIMITER.fullmatch(lines[nested_probe][2])
                if possible and possible.group(1) == nested_indent \
                        and not possible.group(2).strip():
                    nested_close = nested_probe
                    break
                if possible and possible.group(1) == indent \
                        and not possible.group(2).strip():
                    break
            if nested_close is None:
                ambiguous = True
                break
            probe = nested_close + 1
        payload_start = line_end
        if ambiguous:
            blocked.append((start, lines[probe][1]))
            index = probe + 1
            continue
        if close_index is not None:
            payload_end = lines[close_index][0]
            spans.append({"start": payload_start, "end": payload_end, "label": info,
                          "completeness": "complete", "continuation": "none",
                          "evidence": ["complete_standalone_markdown_fence"],
                          "cover_start": start, "cover_end": lines[close_index][1]})
            index = close_index + 1
            continue
        payload = text[payload_start:]
        technical = classify_payload(payload, info)[0] != "unclassified_technical"
        if payload and (info or technical):
            spans.append({"start": payload_start, "end": len(text), "label": info,
                          "completeness": "open_ended",
                          "continuation": "ends_mid_structure",
                          "evidence": ["unmatched_standalone_markdown_opener"],
                          "cover_start": start, "cover_end": len(text)})
        # An unlabelled, nontechnical unmatched delimiter is an orphan closer.
        index += 1
    return spans, blocked


def _unfenced_markup_spans(text: str, occupied: list[tuple[int, int]]) -> list[dict]:
    if occupied:
        # Detector precedence prevents lower-level discovery inside fenced regions.
        masked = list(text)
        for start, end in occupied:
            masked[start:end] = " " * (end - start)
        probe = "".join(masked)
    else:
        probe = text
    lines = _lines(probe)
    qualifying = [i for i, (_, _, line) in enumerate(lines) if _TAG.search(line)]
    if not qualifying:
        return []
    first, last = min(qualifying), max(qualifying)
    for index in range(last + 1, len(lines)):
        if lines[index][2].strip().startswith("<"):
            last = index
        elif lines[index][2].strip():
            break
    start, end = lines[first][0], lines[last][1]
    raw = text[start:end]
    ok, evidence, completeness, continuation = _markup_facts(raw)
    return ([{"start": start, "end": end, "kind": "structured_xml_markup",
              "completeness": completeness, "continuation": continuation,
              "evidence": evidence}] if ok else [])


def _whole_unfenced_span(text: str, occupied: list[tuple[int, int]]) -> list[dict]:
    boundaries = []
    cursor = 0
    for start, end in sorted(occupied):
        if cursor < start:
            boundaries.append((cursor, start))
        cursor = max(cursor, end)
    if cursor < len(text):
        boundaries.append((cursor, len(text)))
    if not occupied:
        boundaries = [(0, len(text))]
    found = []
    for region_start, region_end in boundaries:
        region = text[region_start:region_end]
        if not region.strip():
            continue
        shell, shell_evidence = _shell_facts(region)
        config, config_evidence = _config_facts(region)
        source, source_evidence = _source_facts(region)
        matches = [("shell_sequence", shell, shell_evidence),
                   ("configuration_properties", config, config_evidence),
                   ("source_code", source, source_evidence)]
        active = [(kind, ev) for kind, yes, ev in matches if yes]
        if not active:
            continue
        # Detector precedence resolves a same-region overlap deterministically.
        kind, evidence = active[0]
        start = region_start + len(region) - len(region.lstrip())
        end = region_end - (len(region) - len(region.rstrip()))
        found.append({"start": start, "end": end, "kind": kind,
                      "completeness": "fragment", "continuation": "none",
                      "evidence": evidence})
    return found


def detect_turn_candidates(turn: dict) -> list[dict]:
    """Return ordered candidate drafts for one assistant response."""
    if turn.get("role") != "assistant" or not isinstance(turn.get("text"), str):
        return []
    text = turn["text"]
    fenced, blocked = _fenced_spans(text)
    drafts = []
    occupied = blocked.copy()
    for span in fenced:
        raw = text[span["start"]:span["end"]]
        kind, evidence = classify_payload(raw, span["label"])
        drafts.append({key: value for key, value in {
            **span, "kind": kind, "container": "markdown_fence",
            "evidence": span["evidence"] + evidence}.items()
            if key not in {"cover_start", "cover_end"}})
        occupied.append((span["cover_start"], span["cover_end"]))
    drafts.extend({**span, "container": "none"}
                  for span in _unfenced_markup_spans(text, occupied))
    occupied.extend((item["start"], item["end"]) for item in drafts)
    drafts.extend({**span, "container": "none"}
                  for span in _whole_unfenced_span(text, occupied))
    unique = {}
    for item in drafts:
        key = (item["start"], item["end"])
        if key in unique:
            unique[key]["evidence"] = list(dict.fromkeys(
                unique[key]["evidence"] + item["evidence"]))
        else:
            unique[key] = item
    ordered = sorted(unique.values(), key=lambda item: (item["start"], item["end"]))
    return ordered


def _legacy_spans(normalized: dict) -> dict[tuple, str]:
    """Recover exact V1 fence spans for provenance mapping only."""
    result = {}
    turns = {turn["turn_id"]: turn for turn in normalized["visible_turns"]}
    old_pattern = re.compile(r"^```([^\n]*)\n(.*?)^```[ \t]*(?=\n|\Z)", re.M | re.S)
    by_response = defaultdict(list)
    for legacy in normalized.get("artifact_candidates", []):
        by_response[legacy["source_response_id"]].append(legacy)
    for response_id, legacy_items in by_response.items():
        turn = turns[response_id]
        matches = list(old_pattern.finditer(turn["text"]))
        for legacy, match in zip(sorted(legacy_items, key=lambda x: x["order_within_response"]), matches):
            raw = match.group(2)
            key = (normalized["case_id"], response_id, turn["event_index"],
                   turn["source_record_index"], match.start(2), match.end(2),
                   _sha(raw), _sha(turn["text"]))
            result[key] = legacy["artifact_id"]
    return result


def build_v2_model_view(normalized: dict) -> dict:
    """Build a coexisting conversation-only-v2 view from immutable normalized data."""
    if normalized.get("normalized_version") != "lossless-conversation-v1":
        raise ValueError("V2 requires lossless-conversation-v1")
    legacy = _legacy_spans(normalized)
    candidates = []
    seen_ids = {}
    for turn in normalized["visible_turns"]:
        for draft in detect_turn_candidates(turn):
            raw = turn["text"][draft["start"]:draft["end"]]
            raw_hash, turn_hash = _sha(raw), _sha(turn["text"])
            identifier = candidate_id(turn["event_index"], draft["start"], draft["end"], raw_hash)
            fingerprint = (turn["turn_id"], draft["start"], draft["end"], raw_hash)
            if identifier in seen_ids and seen_ids[identifier] != fingerprint:
                raise ValueError(f"V2 candidate identifier collision: {identifier}")
            if identifier in seen_ids:
                raise ValueError(f"Duplicate V2 candidate identifier: {identifier}")
            seen_ids[identifier] = fingerprint
            legacy_key = (normalized["case_id"], turn["turn_id"], turn["event_index"],
                          turn["source_record_index"], draft["start"], draft["end"],
                          raw_hash, turn_hash)
            candidates.append({
                "candidate_id": identifier, "legacy_artifact_id": legacy.get(legacy_key),
                "kind": draft["kind"], "container": draft["container"],
                "source_response_id": turn["turn_id"],
                "source_event_index": turn["event_index"],
                "source_record_index": turn["source_record_index"],
                "order_within_response": 0, "start_offset": draft["start"],
                "end_offset": draft["end"], "raw_text": raw,
                "raw_text_sha256": raw_hash, "source_turn_text_sha256": turn_hash,
                "detector": {"name": PRODUCER_VERSION, "version": "2"},
                "detector_evidence": list(dict.fromkeys(draft["evidence"])),
                "completeness": draft["completeness"],
                "continuation_status": draft["continuation"],
                "fence_language": draft.get("label") or None, "status": STATUS,
            })
    candidates.sort(key=lambda item: (item["source_event_index"], item["start_offset"],
                                      item["end_offset"], item["candidate_id"]))
    counts = defaultdict(int)
    for item in candidates:
        counts[item["source_response_id"]] += 1
        item["order_within_response"] = counts[item["source_response_id"]]
    turns = deepcopy(normalized["visible_turns"])
    sanitized_records = [{} for _ in normalized["records"]]
    for turn in turns:
        sanitized_records[turn["event_index"]] = {"message": {
            "author": {"role": turn["role"]},
            "content": {"content_type": "text", "parts": [turn["text"]]},
            "create_time": turn["create_time"]}}
    package = {
        "package_version": PACKAGE_VERSION, "candidate_producer_version": PRODUCER_VERSION,
        "methodology_version": METHODOLOGY_VERSION, "case_id": normalized["case_id"],
        "start": normalized["start"], "precision": normalized["precision"],
        "temporal_status": normalized["temporal_status"],
        "temporal_source": normalized["temporal_source"],
        "source_conversation_sha256": normalized["source_conversation_sha256"],
        "visible_turns": turns, "generated_technical_content_candidates": candidates,
        "records": sanitized_records, "complete": True, "reconstruction_safe": False,
    }
    validate_v2_model_view(package)
    return package


def validate_v2_model_view(package: dict) -> None:
    """Validate cross-object invariants not expressible in JSON Schema."""
    required = {"package_version", "candidate_producer_version", "methodology_version",
                "case_id", "start", "precision", "temporal_status", "temporal_source",
                "source_conversation_sha256", "visible_turns",
                "generated_technical_content_candidates", "records", "complete",
                "reconstruction_safe"}
    if set(package) != required or package.get("package_version") != PACKAGE_VERSION \
            or package.get("candidate_producer_version") != PRODUCER_VERSION \
            or package.get("methodology_version") != METHODOLOGY_VERSION \
            or package.get("complete") is not True or package.get("reconstruction_safe") is not False:
        raise ValueError("Invalid conversation-only-v2 envelope")
    turns = {turn.get("turn_id"): turn for turn in package.get("visible_turns", [])}
    candidates = package.get("generated_technical_content_candidates")
    if not isinstance(candidates, list):
        raise ValueError("V2 candidates must be a list")
    ids, spans = set(), set()
    previous = None
    order = defaultdict(int)
    for item in candidates:
        expected_keys = {"candidate_id", "legacy_artifact_id", "kind", "container",
                         "source_response_id", "source_event_index", "source_record_index",
                         "order_within_response", "start_offset", "end_offset", "raw_text",
                         "raw_text_sha256", "source_turn_text_sha256", "detector",
                         "detector_evidence", "completeness", "continuation_status",
                         "fence_language", "status"}
        if not isinstance(item, dict) or set(item) != expected_keys:
            raise ValueError("Malformed V2 candidate")
        turn = turns.get(item["source_response_id"])
        if turn is None or turn.get("role") != "assistant" \
                or turn.get("event_index") != item["source_event_index"] \
                or turn.get("source_record_index") != item["source_record_index"]:
            raise ValueError("V2 candidate response ownership is invalid")
        start, end = item["start_offset"], item["end_offset"]
        if not isinstance(start, int) or not isinstance(end, int) or start < 0 or end <= start \
                or turn["text"][start:end] != item["raw_text"]:
            raise ValueError("V2 candidate source span is invalid")
        raw_hash, turn_hash = _sha(item["raw_text"]), _sha(turn["text"])
        expected_id = candidate_id(item["source_event_index"], start, end, raw_hash)
        if item["candidate_id"] != expected_id or item["raw_text_sha256"] != raw_hash \
                or item["source_turn_text_sha256"] != turn_hash:
            raise ValueError("V2 candidate identity or hash is invalid")
        if item["candidate_id"] in ids:
            raise ValueError("Duplicate V2 candidate identifier")
        span = (item["source_response_id"], start, end)
        if span in spans:
            raise ValueError("Duplicate V2 candidate exact span")
        ids.add(item["candidate_id"]); spans.add(span)
        key = (item["source_event_index"], start, end, item["candidate_id"])
        if previous is not None and key <= previous:
            raise ValueError("V2 candidate ordering is invalid")
        previous = key
        order[item["source_response_id"]] += 1
        if item["order_within_response"] != order[item["source_response_id"]]:
            raise ValueError("V2 response-local ordering is invalid")
        if item["kind"] not in KINDS or item["container"] not in CONTAINERS \
                or item["completeness"] not in COMPLETENESS \
                or item["continuation_status"] not in CONTINUATIONS \
                or item["status"] != STATUS or not GTC_ID.fullmatch(item["candidate_id"]):
            raise ValueError("V2 candidate enum or identifier is invalid")
        if item["legacy_artifact_id"] is not None and not re.fullmatch(
                r"ARTIFACT_[0-9]{6}_[0-9]{3}", item["legacy_artifact_id"]):
            raise ValueError("V2 legacy artifact mapping is invalid")


def compare_v1_v2(normalized: dict, v2: dict, *, strict: bool = True) -> list[dict]:
    """Classify migration relationships without changing either package."""
    validate_v2_model_view(v2)
    mapped = {item["legacy_artifact_id"] for item in
              v2["generated_technical_content_candidates"] if item["legacy_artifact_id"]}
    report = []
    legacy_spans = _legacy_spans(normalized)
    legacy_positions = [{"artifact_id": artifact_id, "response_id": key[1],
                         "event": key[2], "start": key[4], "end": key[5]}
                        for key, artifact_id in legacy_spans.items()]
    for item in v2["generated_technical_content_candidates"]:
        classification = "exact_v1_equivalent" if item["legacy_artifact_id"] else "new_v2_candidate"
        if not item["legacy_artifact_id"] and legacy_positions:
            overlaps = [old for old in legacy_positions
                        if old["response_id"] == item["source_response_id"]
                        and max(old["start"], item["start_offset"])
                        < min(old["end"], item["end_offset"])]
            old_events = [old["event"] for old in legacy_positions]
            event = item["source_event_index"]
            classification = ("changed_span" if overlaps else
                              "earlier_response_addition" if event < min(old_events) else
                              "later_response_addition" if event > max(old_events) else
                              "same_response_addition")
        report.append({"candidate_id": item["candidate_id"],
                       "legacy_artifact_id": item["legacy_artifact_id"],
                       "classification": classification})
    missing = [item["artifact_id"] for item in normalized.get("artifact_candidates", [])
               if item["artifact_id"] not in mapped]
    report.extend({"candidate_id": None, "legacy_artifact_id": artifact_id,
                   "classification": "v1_candidate_missing"} for artifact_id in missing)
    if missing and strict:
        raise ValueError("V1 candidate missing from V2: " + ", ".join(missing))
    return report
