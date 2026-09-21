"""Public ChatGPT share retrieval with conservative structured parsing."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

from .screening_http import HttpClient

SHARE_PATH = re.compile(r"^/share/([0-9a-fA-F-]{36})/?$")
NEXT_DATA = re.compile(r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>', re.S)


def share_id(url: str) -> str | None:
    parsed = urlparse(url)
    match = SHARE_PATH.fullmatch(parsed.path)
    if parsed.scheme != "https" or parsed.netloc.lower() not in {
        "chat.openai.com", "chatgpt.com"
    }:
        return None
    return match[1].lower() if match else None


def _find_conversation(value: object) -> dict | None:
    if isinstance(value, dict):
        if isinstance(value.get("mapping"), dict) or isinstance(value.get("messages"), list):
            return value
        for child in value.values():
            found = _find_conversation(child)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_conversation(child)
            if found is not None:
                return found
    return None


def _react_router_data(raw: str) -> object | None:
    """Decode the flattened JSON embedded in public React Router share pages.

    The page serializes an index table in streamController.enqueue(...).
    Objects use _N keys to refer to table entries holding their real keys;
    object values and array elements are table indices. Unknown negative
    sentinel values are left absent rather than invented as source facts.
    """
    marker = "streamController.enqueue("
    position = 0
    decoder = json.JSONDecoder()
    while (position := raw.find(marker, position)) >= 0:
        position += len(marker)
        try:
            chunk, end = decoder.raw_decode(raw, position)
            position = end
            table = json.loads(chunk)
        except (ValueError, TypeError):
            continue
        if not isinstance(table, list) or not table:
            continue
        cache: dict[int, object] = {}
        active: set[int] = set()

        def resolve(index: int) -> object:
            if index < 0 or index >= len(table):
                return None
            if index in cache:
                return cache[index]
            if index in active:
                raise ValueError("Cyclic structured share payload")
            active.add(index)
            item = table[index]
            if isinstance(item, dict) and all(re.fullmatch(r"_\d+", key) for key in item):
                value = {str(resolve(int(key[1:]))): resolve(ref)
                         for key, ref in item.items() if isinstance(ref, int) and ref >= 0}
            elif isinstance(item, list):
                value = [resolve(ref) if isinstance(ref, int) else ref for ref in item]
            else:
                value = item
            active.remove(index)
            cache[index] = value
            return value

        for index, item in enumerate(table):
            if not isinstance(item, dict):
                continue
            key_names = {table[int(key[1:])] for key in item
                         if re.fullmatch(r"_\d+", key) and int(key[1:]) < len(table)
                         and isinstance(table[int(key[1:])], str)}
            if not {"mapping", "current_node"}.issubset(key_names):
                continue
            try:
                value = resolve(index)
            except ValueError:
                continue
            if _find_conversation(value) is not None:
                return value
    return None


def _date_value(value: object) -> tuple[str, str]:
    if isinstance(value, (float, int)) and value > 0:
        return datetime.fromtimestamp(value, timezone.utc).isoformat(), "timestamp"
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is not None:
                return parsed.isoformat(), "timestamp"
            if len(value) == 10:
                return value, "date"
        except ValueError:
            pass
    return "", ""


def _message_turn(message: dict) -> tuple[dict | None, list[dict]]:
    role = message.get("author", {}).get("role") if isinstance(message.get("author"), dict) else message.get("role")
    if role == "system" or role == "tool":
        return None, []
    if role not in {"user", "assistant"}:
        raise ValueError("Unknown visible message role")
    # A message addressed wholly to a tool is retained in the raw trace by
    # parse_share, but is not a reply addressed to the conversation.
    if role == "assistant" and message.get("recipient") not in (None, "all"):
        return None, []
    content = message.get("content")
    tool_parts = []
    if isinstance(content, dict):
        parts = content.get("parts")
        if not isinstance(parts, list):
            raise ValueError("Non-text or unsupported message content")
        visible = []
        for part_index, part in enumerate(parts):
            if isinstance(part, str):
                visible.append(part)
            elif isinstance(part, dict) and part.get("content_type", part.get("type")) in {"text", "text/plain"} and isinstance(part.get("text"), str):
                visible.append(part["text"])
            elif (role == "assistant" and isinstance(part, dict)
                  and (any(key in part for key in ("tool_call", "tool_use", "recipient", "destination"))
                       or any(marker in str(part.get("content_type", part.get("type", ""))).lower()
                              for marker in ("tool", "browser", "search", "function", "invocation")))):
                tool_parts.append({"part_index": part_index, "part": part})
            else:
                raise ValueError("Non-text or unsupported message content part")
        text = "\n".join(visible)
    elif isinstance(content, str):
        text = content
    else:
        raise ValueError("Missing message content")
    return ({"role": role, "text": text} if text or not tool_parts else None), tool_parts


def parse_share(body: bytes, content_type: str = "") -> dict:
    """Return only a fully ordered text conversation or raise ValueError.

    Supported source shapes are a structured JSON share response or an
    HTML page containing structured __NEXT_DATA__. Visible-page text alone
    cannot establish completeness, so it is not counted as a conversation.
    """
    raw = body.decode("utf-8", errors="replace")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        match = NEXT_DATA.search(raw)
        if match:
            try:
                value = json.loads(unescape(match[1]))
            except json.JSONDecodeError as exc:
                raise ValueError("Malformed structured conversation payload") from exc
        else:
            value = _react_router_data(raw)
            if value is None:
                raise ValueError("No supported structured conversation payload")
    data = _find_conversation(value)
    if data is None:
        raise ValueError("No conversation mapping or messages")
    if isinstance(data.get("messages"), list):
        records = [{"node_id": None, "parent": None, "message": message}
                   for message in data["messages"]]
    else:
        mapping = data["mapping"]
        current = data.get("current_node")
        if not current or current not in mapping:
            raise ValueError("Conversation graph has no current node")
        chain = []
        seen = set()
        while current:
            if current in seen or current not in mapping:
                raise ValueError("Conversation graph is incomplete or cyclic")
            seen.add(current)
            node = mapping[current]
            chain.append({"node_id": current, "parent": node.get("parent"),
                          "message": node.get("message")})
            current = node.get("parent")
        records = list(reversed(chain))
    turns = []
    tool_trace = []
    other_records = []
    first_user_time: object = None
    for event_index, record in enumerate(records):
        message = record["message"]
        if message is None:
            other_records.append({"event_index": event_index, "record": record})
            continue
        if not isinstance(message, dict):
            raise ValueError("Malformed message")
        role = message.get("author", {}).get("role") if isinstance(message.get("author"), dict) else message.get("role")
        recipient = message.get("recipient")
        turn, tool_parts = _message_turn(message)
        if role == "tool" or (role == "assistant" and recipient not in (None, "all")):
            tool_trace.append({"event_index": event_index, "record": record})
        elif role == "system":
            other_records.append({"event_index": event_index, "record": record})
        for part in tool_parts:
            tool_trace.append({"event_index": event_index, "record": record, **part})
        if turn is not None:
            if turn["role"] == "user" and first_user_time is None:
                first_user_time = message.get("create_time")
            turns.append(turn)
    if not turns or not any(t["role"] == "user" for t in turns):
        raise ValueError("No visible developer turns")
    start, precision = _date_value(first_user_time)
    temporal_status = "derivable" if start else "unresolved"
    return {"title": data.get("title", ""), "start": start,
            "precision": precision, "temporal_status": temporal_status,
            "complete": True, "turns": turns, "records": records,
            "tool_trace": tool_trace, "other_records": other_records,
            "raw_conversation": data}


def retrieve_share(url: str, http: HttpClient, *, refresh: bool = False,
                   with_source: bool = False):
    identity = share_id(url)
    result = {"url": url, "canonical_url": "", "share_id": identity or "",
              "retrieval_status": "not_attempted", "parsing_status": "not_attempted",
              "temporal_status": "unavailable", "complete": False,
              "title": "", "start": "", "precision": "", "turns": [], "notes": ""}
    if not identity:
        result.update(retrieval_status="malformed_url", notes="Invalid public share URL")
        return (result, None) if with_source else result
    canonical = f"https://chatgpt.com/share/{identity}"
    result["canonical_url"] = canonical
    fetch = http.get(canonical, refresh=refresh, accept="text/html, application/json")
    source_fetch = fetch if fetch.body is not None else None
    result["retrieval_status"] = fetch.status
    if fetch.body is None:
        result["notes"] = fetch.note
        return result
    for body in (fetch.body,):
        try:
            parsed = parse_share(body)
            result.update(parsed)
            result["parsing_status"] = "parsed"
            break
        except ValueError as exc:
            result["notes"] = str(exc)
    if result["parsing_status"] != "parsed":
        # The public structured share endpoint is attempted only if the
        # HTML page did not expose a verifiable ordered conversation.
        api = http.get(f"https://chatgpt.com/backend-api/share/{identity}",
                       refresh=refresh, accept="application/json")
        if api.body is not None:
            source_fetch = api
            try:
                result.update(parse_share(api.body))
                result["parsing_status"] = "parsed"
                result["notes"] = ""
            except ValueError as exc:
                result["parsing_status"] = "unsupported_or_malformed"
                result["notes"] = str(exc)
        else:
            result["parsing_status"] = "unsupported_or_malformed"
            result["notes"] = f"Page parsing unavailable; structured source: {api.status}"
    parsed_dir = http.cache_dir / "parsed"
    parsed_dir.mkdir(parents=True, exist_ok=True)
    (parsed_dir / f"chatgpt_{identity}.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return (result, source_fetch) if with_source else result
