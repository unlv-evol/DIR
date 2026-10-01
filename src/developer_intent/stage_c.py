"""Two-pass, conversation-only Protocol v5 Stage C extraction."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .screening_chatgpt import _date_value
from .stage_c_config import StageCModelConfig

METHODOLOGY_VERSION = "dir-tfg-v2"
SCHEMA_VERSION = "conversation-draft-v3"
EXTRACTION_VERSION = "conversation-extraction-v3"
PASS_1_PROMPT_VERSION = "dir-stage-c-first-generation-v2"
PASS_2_PROMPT_VERSION = "dir-stage-c-csv-extraction-v1"
PACKAGE_KEYS = {"package_version", "methodology_version", "case_id", "start", "precision",
                "temporal_status", "temporal_source", "source_conversation_sha256",
                "visible_turns", "artifact_candidates", "records", "complete",
                "reconstruction_safe"}
FORBIDDEN_KEYS = {"pr_url", "repository", "Outcome_Class", "eligible", "eligibility_status",
                  "final_diff", "integrated_implementation"}
CATEGORIES = ("context", "specificity", "verification")
FAMILY_ID_PREFIX = "FGF_"
FAMILY_ID_DIGEST_LENGTH = 24
CASE_ID = re.compile(r"CASE_[0-9A-F]{12}\Z")


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


def deterministic_family_identity(case_id: str, selected_artifacts: list[dict]) -> tuple[str, dict]:
    """Derive globally unique identity from one validated, canonically ordered artifact set."""
    if not isinstance(case_id, str) or not CASE_ID.fullmatch(case_id) or not selected_artifacts:
        raise ValueError("Family identity requires a case and validated selected artifacts")
    required = ("artifact_id", "response_event_index", "order_within_response")
    if any(not isinstance(item, dict) or not all(key in item for key in required)
           or not isinstance(item["artifact_id"], str) or not item["artifact_id"]
           or not isinstance(item["response_event_index"], int)
           or item["response_event_index"] < 0
           or not isinstance(item["order_within_response"], int)
           or item["order_within_response"] < 1
           for item in selected_artifacts):
        raise ValueError("Family identity cannot use malformed artifact references")
    ordered = sorted(selected_artifacts,
                     key=lambda item: (item["response_event_index"],
                                       item["order_within_response"], item["artifact_id"]))
    artifact_ids = [item["artifact_id"] for item in ordered]
    if len(set(artifact_ids)) != len(artifact_ids):
        raise ValueError("Family identity cannot use duplicate artifact references")
    canonical_value = {"artifact_ids": artifact_ids, "case_id": case_id}
    serialized = json.dumps(canonical_value, sort_keys=True, ensure_ascii=False,
                            separators=(",", ":"))
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    return FAMILY_ID_PREFIX + digest[:FAMILY_ID_DIGEST_LENGTH], {
        "algorithm": "sha256", "canonicalization": "json-sort-keys-compact-utf8",
        "canonical_input": canonical_value, "digest_hex": digest,
        "digest_prefix_length": FAMILY_ID_DIGEST_LENGTH,
        "case_id_included": True,
    }


def load_contract(root: Path, name: str) -> dict:
    return json.loads((root / "schemas" / name).read_text(encoding="utf-8"))


def load_prompt(root: Path, relative: str) -> tuple[str, str]:
    text = (root / relative).read_text(encoding="utf-8")
    return text, hashlib.sha256(text.encode()).hexdigest()


def validate_model_view(package: dict, case_id: str) -> None:
    if (set(package) != PACKAGE_KEYS or package.get("package_version") != "conversation-only-v1"
            or package.get("methodology_version") != METHODOLOGY_VERSION
            or package.get("case_id") != case_id or package.get("complete") is not True):
        raise ValueError("Stage C requires one complete dir-tfg-v2 Stage B model view")
    text = json.dumps(package, ensure_ascii=False)
    if any(key in package for key in FORBIDDEN_KEYS) or any(f'"{key}"' in text for key in FORBIDDEN_KEYS):
        raise ValueError("Stage C input contains prohibited administrative or repository data")
    turns = package.get("visible_turns")
    if (not isinstance(turns, list) or not turns
            or len({t.get("turn_id") for t in turns}) != len(turns)
            or [t.get("event_index") for t in turns] != sorted(t.get("event_index") for t in turns)):
        raise ValueError("Stage C input turn identity or ordering is invalid")


def _validate_keys(value: dict, expected: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"{label} does not satisfy its structured-output contract")


def validate_pass1(value: dict) -> None:
    keys = {"status", "family_label", "artifact_ids", "response_turn_id", "target_prompt_id",
            "candidate_artifact_ids", "rationale", "ambiguity_reason"}
    _validate_keys(value, keys, "Pass 1")
    if value["status"] not in {"complete", "ambiguous", "unresolved", "failed"}:
        raise ValueError("Pass 1 status is invalid")
    if any(not isinstance(value[k], str) for k in
           ("family_label", "response_turn_id", "target_prompt_id", "rationale", "ambiguity_reason")):
        raise ValueError("Pass 1 string field is invalid")
    if any(not isinstance(value[k], list) or any(not isinstance(x, str) for x in value[k])
           for k in ("artifact_ids", "candidate_artifact_ids")):
        raise ValueError("Pass 1 artifact lists are invalid")
    if value["status"] == "complete" and (not value["family_label"] or not value["artifact_ids"]
            or not value["response_turn_id"] or not value["target_prompt_id"]):
        raise ValueError("Complete Pass 1 output lacks an authoritative selection")


def resolve_first_generation(package: dict, selection: dict) -> tuple[dict, list[dict], dict]:
    validate_pass1(selection)
    unresolved_tfg = {"value": "", "precision": "", "status": "unresolved",
                      "source": "unresolved", "derivation_rule": "exclusive_before_selected_response"}
    if selection["status"] != "complete":
        fg = {"status": selection["status"], "family_id": "",
              "family_label": selection["family_label"],
              "family_id_provenance": {},
              "artifact_refs": selection["artifact_ids"], "response_turn_id": "",
              "response_event_index": None, "target_prompt_id": "",
              "target_prompt_event_index": None, "boundary": "unresolved",
              "candidate_artifact_ids": selection["candidate_artifact_ids"],
              "rationale": selection["rationale"], "ambiguity_reason": selection["ambiguity_reason"]}
        return fg, [], unresolved_tfg
    turns = {turn["turn_id"]: turn for turn in package["visible_turns"]}
    artifacts = {item["artifact_id"]: item for item in package["artifact_candidates"]}
    if any(artifact_id not in artifacts for artifact_id in selection["candidate_artifact_ids"]):
        raise ValueError("Pass 1 cited an unknown candidate artifact")
    response = turns.get(selection["response_turn_id"])
    target = turns.get(selection["target_prompt_id"])
    if response is None or response.get("role") != "assistant":
        raise ValueError("Pass 1 selected response is not a visible assistant turn")
    if target is None or target.get("role") != "user":
        raise ValueError("Pass 1 target is not a visible developer turn")
    selected = []
    for artifact_id in selection["artifact_ids"]:
        artifact = artifacts.get(artifact_id)
        if artifact is None or artifact.get("source_response_id") != response["turn_id"]:
            raise ValueError("Pass 1 artifact does not belong to selected response")
        selected.append(artifact)
    family_id, family_id_provenance = deterministic_family_identity(package["case_id"], selected)
    selected = sorted(selected, key=lambda item: (item["response_event_index"],
                                                   item["order_within_response"],
                                                   item["artifact_id"]))
    prior_users = [turn for turn in package["visible_turns"]
                   if turn["event_index"] < response["event_index"] and turn["role"] == "user"]
    if not prior_users or prior_users[-1]["turn_id"] != target["turn_id"]:
        raise ValueError("Pass 1 target is not the immediately triggering developer prompt")
    if target["event_index"] >= response["event_index"]:
        raise ValueError("Pass 1 boundary ordering is invalid")
    admissible = [dict(turn) for turn in package["visible_turns"]
                  if turn["event_index"] < response["event_index"]]
    value, precision = _date_value(response.get("create_time"))
    tfg = ({"value": value, "precision": precision, "status": "derivable",
            "source": f"{response['turn_id']}.create_time",
            "derivation_rule": "exclusive_before_selected_response"} if value else unresolved_tfg)
    fg = {"status": "complete", "family_id": family_id,
          "family_label": selection["family_label"],
          "family_id_provenance": family_id_provenance,
          "artifact_refs": [item["artifact_id"] for item in selected],
          "response_turn_id": response["turn_id"], "response_event_index": response["event_index"],
          "target_prompt_id": target["turn_id"], "target_prompt_event_index": target["event_index"],
          "boundary": f"exclusive_before:{response['turn_id']}",
          "candidate_artifact_ids": selection["candidate_artifact_ids"],
          "rationale": selection["rationale"], "ambiguity_reason": selection["ambiguity_reason"]}
    return fg, admissible, tfg


def validate_pass2(value: dict, admissible: list[dict]) -> None:
    keys = {"status", "context_supplied", "specificity_supplied",
            "verification_supplied", "failure_reason"}
    _validate_keys(value, keys, "Pass 2")
    if value["status"] not in {"complete", "ambiguous", "unresolved", "failed"}:
        raise ValueError("Pass 2 status is invalid")
    turns = {turn["turn_id"]: turn for turn in admissible}
    seen = set()
    for category in CATEGORIES:
        field = f"{category}_supplied"
        if not isinstance(value[field], list):
            raise ValueError("Pass 2 category is not a list")
        for item in value[field]:
            expected = {"id", "category", "text", "source_turns", "source_roles", "evidence"}
            _validate_keys(item, expected, "Pass 2 item")
            if item["category"] != category or not item["id"] or item["id"] in seen or not item["text"]:
                raise ValueError("Pass 2 item identity/category is invalid")
            seen.add(item["id"])
            if (not item["source_turns"] or len(item["source_turns"]) != len(item["source_roles"])
                    or not item["evidence"]):
                raise ValueError("Pass 2 item provenance is incomplete")
            source_text = []
            for turn_id, role in zip(item["source_turns"], item["source_roles"]):
                turn = turns.get(turn_id)
                if turn is None or turn["role"] != role:
                    raise ValueError("Pass 2 item cites an inadmissible turn or incorrect role")
                source_text.append(turn["text"])
            if any(not isinstance(evidence, str) or not evidence
                   or not any(evidence in text for text in source_text) for evidence in item["evidence"]):
                raise ValueError("Pass 2 evidence is not attributable to its cited turns")


def _tc(package: dict) -> dict:
    return {"value": package.get("start", ""), "precision": package.get("precision", ""),
            "status": package.get("temporal_status", "unresolved"),
            "source": package.get("temporal_source", "unresolved"),
            "derivation_rule": "first_developer_prompt"}


def _usage(response: Any) -> dict:
    usage = getattr(response, "usage", None)
    if usage is None:
        return {}
    if hasattr(usage, "model_dump"):
        return usage.model_dump()
    return dict(usage) if isinstance(usage, dict) else {}


class OpenAIStageCClient:
    """Thin Responses API adapter; each call is independent and tool-free."""
    def __init__(self, config: StageCModelConfig):
        if not config.live_permitted:
            raise ValueError("Live Stage C requires valid model configuration and OPENAI_API_KEY")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("Install the project OpenAI SDK dependency before --live") from exc
        options: dict[str, Any] = {"api_key": config.api_key}
        if config.base_url:
            options["base_url"] = config.base_url
        self.client = OpenAI(**options)
        self.config = config

    def invoke(self, prompt: str, payload: dict, schema_name: str, schema: dict) -> tuple[dict, dict]:
        invoked_at = datetime.now(timezone.utc).isoformat()
        response = self.client.responses.create(
            model=self.config.model,
            reasoning={"mode": self.config.reasoning_mode,
                       "effort": self.config.reasoning_effort},
            instructions=prompt,
            input=json.dumps(payload, ensure_ascii=False, sort_keys=True),
            tools=[],
            text={"format": {"type": "json_schema", "name": schema_name,
                             "strict": True, "schema": schema}},
        )
        if getattr(response, "status", "completed") != "completed":
            raise RuntimeError(f"OpenAI response was not complete: {getattr(response, 'status', '')}")
        try:
            parsed = json.loads(response.output_text)
        except (AttributeError, json.JSONDecodeError) as exc:
            raise ValueError("OpenAI Structured Output was malformed") from exc
        metadata = {"response_id": getattr(response, "id", ""),
                    "returned_model": getattr(response, "model", ""),
                    "invocation_timestamp": invoked_at, "usage": _usage(response)}
        return parsed, metadata


def extract_stage_c(root: Path, case_id: str, package: dict, client: Any,
                    config: StageCModelConfig, *, input_ref: str) -> dict:
    validate_model_view(package, case_id)
    p1_prompt, p1_hash = load_prompt(root, "prompts/stage_c/first_generation_v2.md")
    p2_prompt, p2_hash = load_prompt(root, "prompts/stage_c/csv_extraction_v1.md")
    pass1, meta1 = client.invoke(p1_prompt, package, "dir_stage_c_pass1_v2",
                                 load_contract(root, "stage_c_pass1_v2.schema.json"))
    validate_pass1(pass1)
    first_generation, admissible, tfg = resolve_first_generation(package, pass1)
    pass2 = {"status": "not_run", "context_supplied": [], "specificity_supplied": [],
             "verification_supplied": [], "failure_reason": "first_generation_not_complete"}
    meta2: dict = {}
    if first_generation["status"] == "complete":
        payload = {"case_id": case_id, "admissible_prior_turns": admissible}
        pass2, meta2 = client.invoke(p2_prompt, payload, "dir_stage_c_pass2_v1",
                                     load_contract(root, "stage_c_pass2_v1.schema.json"))
        validate_pass2(pass2, admissible)
    final_status = ("complete" if first_generation["status"] == "complete"
                    and pass2["status"] == "complete" and tfg["value"] else
                    first_generation["status"] if first_generation["status"] != "complete"
                    else "unresolved")
    record = {
        "schema_version": SCHEMA_VERSION, "methodology_version": METHODOLOGY_VERSION,
        "extraction_version": EXTRACTION_VERSION, "record_status": "draft", "case_id": case_id,
        "input": {"stage_b_model_view_ref": input_ref, "sha256": canonical_hash(package)},
        "first_generation": first_generation,
        "temporal": {"tC": _tc(package), "tFG": tfg, "primary_repository_cutoff": "tFG"},
        "admissible_prior_turns": admissible,
        "context_supplied": pass2["context_supplied"],
        "specificity_supplied": pass2["specificity_supplied"],
        "verification_supplied": pass2["verification_supplied"],
        "model_provenance": {
            "provider": "openai", "api": "responses", "requested_model": config.model,
            "returned_models": [m for m in (meta1.get("returned_model"), meta2.get("returned_model")) if m],
            "reasoning_mode": config.reasoning_mode, "reasoning_effort": config.reasoning_effort,
            "tools_enabled": [], "structured_outputs": True,
            "structured_output_schema_versions": ["stage-c-pass1-v2", "stage-c-pass2-v1"],
            "pass_1_prompt_version": PASS_1_PROMPT_VERSION,
            "pass_2_prompt_version": PASS_2_PROMPT_VERSION,
            "pass_1_prompt_sha256": p1_hash, "pass_2_prompt_sha256": p2_hash,
            "input_sha256": canonical_hash(package), "invocations": [meta1, meta2],
        },
        "scientific_status": {"eligibility_updated": False,
                              "post_stage_c_resolution_required": True},
        "record_derivation": {"mode": "fresh", "source_record_ref": "",
                              "source_record_sha256": "", "original_model_family_value": ""},
        "status": {"stage_c_status": final_status, "parser_status": "parsed",
                   "validation_status": "validated", "failure_reason": ""},
    }
    validate_stage_c_record(record)
    return record


def validate_stage_c_record(record: dict) -> None:
    required = {"schema_version", "methodology_version", "extraction_version", "record_status",
                "case_id", "input", "first_generation", "temporal", "admissible_prior_turns",
                "context_supplied", "specificity_supplied", "verification_supplied",
                "model_provenance", "scientific_status", "record_derivation", "status"}
    _validate_keys(record, required, "Stage C record")
    if (record["schema_version"] != SCHEMA_VERSION
            or record["methodology_version"] != METHODOLOGY_VERSION
            or record["extraction_version"] != EXTRACTION_VERSION
            or record["record_status"] != "draft"
            or record["temporal"]["primary_repository_cutoff"] != "tFG"
            or record["scientific_status"] != {"eligibility_updated": False,
                                                "post_stage_c_resolution_required": True}):
        raise ValueError("Stage C record version, temporal policy, or scientific status is invalid")
    validate_pass2({"status": "complete", "failure_reason": "",
                    "context_supplied": record["context_supplied"],
                    "specificity_supplied": record["specificity_supplied"],
                    "verification_supplied": record["verification_supplied"]},
                   record["admissible_prior_turns"])
    if record["first_generation"]["response_turn_id"] in {
            turn["turn_id"] for turn in record["admissible_prior_turns"]}:
        raise ValueError("First-generation response leaked into admissible prior turns")
    if record["model_provenance"].get("tools_enabled") != []:
        raise ValueError("Stage C model tools must be disabled")
    fg = record["first_generation"]
    if fg["status"] == "complete":
        if not isinstance(fg.get("family_label"), str) or not fg["family_label"]:
            raise ValueError("Complete family lacks a descriptive family label")
        provenance = fg.get("family_id_provenance")
        if not isinstance(provenance, dict):
            raise ValueError("Complete family lacks deterministic identity provenance")
        expected_input = {"artifact_ids": fg["artifact_refs"], "case_id": record["case_id"]}
        serialized = json.dumps(expected_input, sort_keys=True, ensure_ascii=False,
                                separators=(",", ":"))
        digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        if (provenance.get("canonical_input") != expected_input
                or provenance.get("algorithm") != "sha256"
                or provenance.get("canonicalization") != "json-sort-keys-compact-utf8"
                or provenance.get("digest_hex") != digest
                or provenance.get("digest_prefix_length") != FAMILY_ID_DIGEST_LENGTH
                or provenance.get("case_id_included") is not True
                or fg.get("family_id") != FAMILY_ID_PREFIX + digest[:FAMILY_ID_DIGEST_LENGTH]):
            raise ValueError("Family identity or derivation provenance is invalid")
    derivation = record["record_derivation"]
    if set(derivation) != {"mode", "source_record_ref", "source_record_sha256",
                           "original_model_family_value"}:
        raise ValueError("Record derivation provenance is malformed")
    if derivation["mode"] == "fresh":
        if any(derivation[key] for key in ("source_record_ref", "source_record_sha256",
                                           "original_model_family_value")):
            raise ValueError("Fresh record cannot claim migration provenance")
    elif derivation["mode"] == "deterministic_migration_from_v2":
        if (not derivation["source_record_ref"]
                or not isinstance(derivation["source_record_sha256"], str)
                or len(derivation["source_record_sha256"]) != 64
                or not derivation["original_model_family_value"]):
            raise ValueError("Migrated record lacks source provenance")
    else:
        raise ValueError("Unsupported Stage C record derivation mode")


def migrate_v2_record(record: dict, package: dict, *, source_record_ref: str) -> dict:
    """Create a v3 record beside an immutable v2 development result; make no model call."""
    if (record.get("schema_version") != "conversation-draft-v2"
            or record.get("extraction_version") != "conversation-extraction-v2"
            or record.get("methodology_version") != METHODOLOGY_VERSION
            or record.get("case_id") != package.get("case_id")):
        raise ValueError("Migration requires matching dir-tfg-v2 conversation-draft-v2 inputs")
    validate_model_view(package, record["case_id"])
    old_fg = record.get("first_generation", {})
    if old_fg.get("status") != "complete" or not old_fg.get("artifact_refs"):
        raise ValueError("Migration requires a validated complete artifact selection")
    artifacts = {item["artifact_id"]: item for item in package["artifact_candidates"]}
    selected = []
    for artifact_id in old_fg["artifact_refs"]:
        artifact = artifacts.get(artifact_id)
        if (artifact is None
                or artifact.get("source_response_id") != old_fg.get("response_turn_id")):
            raise ValueError("Legacy selected artifact reference is invalid")
        selected.append(artifact)
    family_id, provenance = deterministic_family_identity(record["case_id"], selected)
    migrated = deepcopy(record)
    migrated["schema_version"] = SCHEMA_VERSION
    migrated["extraction_version"] = EXTRACTION_VERSION
    migrated["first_generation"]["family_label"] = old_fg.get("family_id", "")
    migrated["first_generation"]["family_id"] = family_id
    migrated["first_generation"]["family_id_provenance"] = provenance
    migrated["first_generation"]["artifact_refs"] = provenance["canonical_input"]["artifact_ids"]
    migrated["record_derivation"] = {
        "mode": "deterministic_migration_from_v2",
        "source_record_ref": source_record_ref,
        "source_record_sha256": canonical_hash(record),
        "original_model_family_value": old_fg.get("family_id", ""),
    }
    validate_stage_c_record(migrated)
    return migrated


def failed_record(case_id: str, input_ref: str, input_hash: str,
                  config: StageCModelConfig, reason: str, *, package: dict | None = None) -> dict:
    anchor = {"value": "", "precision": "", "status": "unresolved", "source": "unresolved",
              "derivation_rule": "exclusive_before_selected_response"}
    return {"schema_version": SCHEMA_VERSION, "methodology_version": METHODOLOGY_VERSION,
            "extraction_version": EXTRACTION_VERSION, "record_status": "draft", "case_id": case_id,
            "input": {"stage_b_model_view_ref": input_ref, "sha256": input_hash},
            "first_generation": {"status": "failed", "family_id": "", "artifact_refs": [],
                "family_label": "", "family_id_provenance": {},
                "response_turn_id": "", "response_event_index": None, "target_prompt_id": "",
                "target_prompt_event_index": None, "boundary": "unresolved",
                "candidate_artifact_ids": [], "rationale": "", "ambiguity_reason": reason},
            "temporal": {"tC": _tc(package) if package else dict(anchor),
                         "tFG": dict(anchor), "primary_repository_cutoff": "tFG"},
            "admissible_prior_turns": [], "context_supplied": [], "specificity_supplied": [],
            "verification_supplied": [], "model_provenance": {"provider": "openai",
                "api": "responses", "requested_model": config.model, "tools_enabled": [],
                "structured_outputs": True},
            "scientific_status": {"eligibility_updated": False,
                                  "post_stage_c_resolution_required": True},
            "record_derivation": {"mode": "fresh", "source_record_ref": "",
                                  "source_record_sha256": "", "original_model_family_value": ""},
            "status": {"stage_c_status": "failed", "parser_status": "malformed",
                       "validation_status": "failed", "failure_reason": reason}}


def persist_stage_c(path: Path, record: dict) -> None:
    if path.exists():
        raise FileExistsError(f"Stage C output exists; no overwrite: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", dir=path.parent, prefix=".stage_c_", suffix=".tmp",
                                         encoding="utf-8", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(record, stream, indent=2, ensure_ascii=False, sort_keys=True)
            stream.write("\n"); stream.flush(); os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()
