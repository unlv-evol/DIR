"""Offline Stage C two-pass extraction, temporal, provenance, and leakage tests."""

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from developer_intent.stage_c import (OpenAIStageCClient, StageCInvocationFailure,  # noqa: E402
                                      canonical_hash, extract_stage_c,
                                      deterministic_family_identity, failed_record,
                                      load_contract, migrate_v2_record, persist_stage_c,
                                      resolve_first_generation, validate_model_view,
                                      validate_pass1, validate_pass2,
                                      validate_stage_c_record)
from developer_intent.stage_c_config import StageCModelConfig, load_stage_c_config  # noqa: E402

CASE = "CASE_ABCDEF123456"


def turn(index, role, text, timestamp=None):
    return {"turn_id": f"turn_{index:06d}", "event_index": index,
            "source_record_index": index, "role": role, "text": text,
            "create_time": timestamp}


def package(multiple=True, response_time=1704067230):
    turns = ([turn(0, "user", "Use xUnit for the existing test.", 1704067200),
              turn(1, "assistant", "The data can be loaded from JSON.", 1704067210),
              turn(2, "user", "Implement that and keep the API stable.", 1704067220)]
             if multiple else [turn(0, "user", "Use JSON test data.", 1704067200)])
    response_index = 3 if multiple else 1
    turns += [turn(response_index, "assistant", "```csharp\nRun();\n```", response_time),
              turn(response_index + 1, "user", "Later request",
                   response_time + 10 if response_time is not None else None)]
    artifacts = [{"artifact_id": f"ARTIFACT_{response_index:06d}_001",
                  "source_response_id": f"turn_{response_index:06d}",
                  "response_event_index": response_index, "source_record_index": response_index,
                  "order_within_response": 1, "content": "Run();\n", "fence_label": "csharp",
                  "status": "candidate_requires_review"}]
    return {"package_version": "conversation-only-v1", "methodology_version": "dir-tfg-v2",
            "case_id": CASE, "start": "2024-01-01T00:00:00+00:00",
            "precision": "timestamp", "temporal_status": "derivable",
            "temporal_source": "first developer turn in parsed conversation",
            "source_conversation_sha256": "a" * 64, "visible_turns": turns,
            "artifact_candidates": artifacts,
            "records": [{"message": {"role": t["role"], "content": t["text"]}} for t in turns],
            "complete": True, "reconstruction_safe": False}


def pass1(pkg, **changes):
    response = pkg["artifact_candidates"][0]["source_response_id"]
    response_index = pkg["artifact_candidates"][0]["response_event_index"]
    users = [t for t in pkg["visible_turns"] if t["role"] == "user"
             and t["event_index"] < response_index]
    value = {"status": "complete", "family_label": "first generated family",
             "artifact_ids": [pkg["artifact_candidates"][0]["artifact_id"]],
             "response_turn_id": response, "target_prompt_id": users[-1]["turn_id"],
             "candidate_artifact_ids": [pkg["artifact_candidates"][0]["artifact_id"]],
             "rationale": "Earliest coherent generated artifact.", "ambiguity_reason": ""}
    value.update(changes)
    return value


def pass2(**changes):
    value = {"status": "complete",
             "context_supplied": [{"id": "C1", "category": "context",
                 "text": "The task uses xUnit.", "source_turns": ["turn_000000"],
                 "source_roles": ["user"], "evidence": ["xUnit"]}],
             "specificity_supplied": [{"id": "S1", "category": "specificity",
                 "text": "Load data from JSON.", "source_turns": ["turn_000001"],
                 "source_roles": ["assistant"], "evidence": ["loaded from JSON"]},
                {"id": "S2", "category": "specificity",
                 "text": "Keep the API stable.", "source_turns": ["turn_000002"],
                 "source_roles": ["user"], "evidence": ["keep the API stable"]}],
             "verification_supplied": [{"id": "V1", "category": "verification",
                 "text": "The API must remain stable.", "source_turns": ["turn_000002"],
                 "source_roles": ["user"], "evidence": ["keep the API stable"]}],
             "failure_reason": ""}
    value.update(changes)
    return value


class MockClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def invoke(self, prompt, payload, schema_name, schema):
        self.calls.append({"prompt": prompt, "payload": copy.deepcopy(payload),
                           "schema_name": schema_name, "schema": schema})
        answer = self.responses.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return copy.deepcopy(answer), {"response_id": f"response-{len(self.calls)}",
                                        "returned_model": "gpt-5.6-sol",
                                        "invocation_timestamp": "2026-09-30T00:00:00+00:00",
                                        "usage": {"input_tokens": 10, "output_tokens": 5,
                                                  "output_tokens_details": {"reasoning_tokens": 2}}}


CONFIG = StageCModelConfig("secret", None, "gpt-5.6-sol", "standard", "medium")


class StageCTests(unittest.TestCase):
    def test_deterministic_family_id_is_repeatable_and_case_scoped(self):
        artifacts = package()["artifact_candidates"]
        first = deterministic_family_identity(CASE, artifacts)[0]
        self.assertEqual(first, deterministic_family_identity(CASE, artifacts)[0])
        self.assertNotEqual(first, deterministic_family_identity("CASE_123456ABCDEF", artifacts)[0])

    def test_family_id_canonicalizes_order_and_changes_with_artifact_set(self):
        artifacts = package()["artifact_candidates"]
        second = {**artifacts[0], "artifact_id": "ARTIFACT_000003_002",
                  "order_within_response": 2}
        combined = artifacts + [second]
        self.assertEqual(deterministic_family_identity(CASE, combined)[0],
                         deterministic_family_identity(CASE, list(reversed(combined)))[0])
        self.assertNotEqual(deterministic_family_identity(CASE, artifacts)[0],
                            deterministic_family_identity(CASE, combined)[0])

    def test_family_wording_cannot_change_identity(self):
        pkg = package()
        first = resolve_first_generation(pkg, pass1(pkg, family_label="label one"))[0]
        second = resolve_first_generation(pkg, pass1(pkg, family_label="label two"))[0]
        self.assertEqual(first["family_id"], second["family_id"])
        self.assertNotEqual(first["family_label"], second["family_label"])

    def test_malformed_artifacts_cannot_generate_family_identity(self):
        with self.assertRaises(ValueError):
            deterministic_family_identity(CASE, [{"artifact_id": "A"}])
        with self.assertRaises(ValueError):
            deterministic_family_identity(CASE, [])

    def test_two_pass_single_case_and_strict_boundary(self):
        pkg = package()
        client = MockClient([pass1(pkg), pass2()])
        record = extract_stage_c(ROOT, CASE, pkg, client, CONFIG,
                                 input_ref=f"cases/conversations/{CASE}/stage_c_model_view.json")
        self.assertEqual(len(client.calls), 2)
        self.assertEqual(client.calls[0]["payload"], pkg)
        sent = client.calls[1]["payload"]["admissible_prior_turns"]
        self.assertEqual([t["turn_id"] for t in sent],
                         ["turn_000000", "turn_000001", "turn_000002"])
        self.assertNotIn("turn_000003", json.dumps(client.calls[1]["payload"]))
        self.assertNotIn("Later request", json.dumps(client.calls[1]["payload"]))
        self.assertEqual(record["first_generation"]["target_prompt_id"], "turn_000002")
        self.assertEqual(record["first_generation"]["response_turn_id"], "turn_000003")
        self.assertEqual(record["temporal"]["tFG"]["value"], "2024-01-01T00:00:30+00:00")
        self.assertEqual(record["temporal"]["tC"]["value"], "2024-01-01T00:00:00+00:00")
        self.assertEqual(record["temporal"]["primary_repository_cutoff"], "tFG")
        self.assertFalse(record["scientific_status"]["eligibility_updated"])
        self.assertTrue(record["first_generation"]["family_id"].startswith("FGF_"))
        self.assertEqual(record["first_generation"]["family_label"], "first generated family")
        self.assertEqual(record["model_provenance"]["sdk_max_retries"], 2)

    def test_one_prompt_first_generated_response(self):
        pkg = package(multiple=False)
        selection = pass1(pkg)
        fg, prior, tfg = resolve_first_generation(pkg, selection)
        self.assertEqual(fg["target_prompt_id"], "turn_000000")
        self.assertEqual([t["turn_id"] for t in prior], ["turn_000000"])
        self.assertTrue(tfg["value"])

    def test_earlier_assistant_is_admissible_and_attributed(self):
        pkg = package()
        _, prior, _ = resolve_first_generation(pkg, pass1(pkg))
        extracted = pass2()
        validate_pass2(extracted, prior)
        self.assertEqual(extracted["specificity_supplied"][0]["source_roles"], ["assistant"])

    def test_multiple_atomic_and_empty_categories(self):
        pkg = package(); _, prior, _ = resolve_first_generation(pkg, pass1(pkg))
        value = pass2(context_supplied=[], verification_supplied=[])
        validate_pass2(value, prior)
        self.assertEqual(len(value["specificity_supplied"]), 2)
        self.assertEqual(value["context_supplied"], [])

    def test_same_evidence_can_support_specificity_and_verification(self):
        pkg = package(); _, prior, _ = resolve_first_generation(pkg, pass1(pkg))
        validate_pass2(pass2(), prior)

    def test_multi_turn_provenance(self):
        pkg = package(); _, prior, _ = resolve_first_generation(pkg, pass1(pkg))
        item = {"id": "C2", "category": "context", "text": "xUnit data comes from JSON.",
                "source_turns": ["turn_000000", "turn_000001"],
                "source_roles": ["user", "assistant"], "evidence": ["xUnit", "loaded from JSON"]}
        validate_pass2(pass2(context_supplied=[item]), prior)

    def test_invalid_and_post_boundary_sources_rejected(self):
        pkg = package(); _, prior, _ = resolve_first_generation(pkg, pass1(pkg))
        for bad_id in ("turn_missing", "turn_000003", "turn_000004"):
            item = {"id": "C2", "category": "context", "text": "bad",
                    "source_turns": [bad_id], "source_roles": ["assistant"], "evidence": ["bad"]}
            with self.assertRaises(ValueError):
                validate_pass2(pass2(context_supplied=[item]), prior)

    def test_invalid_artifact_target_and_response_rejected(self):
        pkg = package()
        for changes in ({"artifact_ids": ["missing"]},
                        {"response_turn_id": "turn_000002"},
                        {"target_prompt_id": "turn_000000"}):
            with self.assertRaises(ValueError):
                resolve_first_generation(pkg, pass1(pkg, **changes))

    def test_multiple_artifact_candidates_preserve_selected_family(self):
        pkg = package()
        pkg["artifact_candidates"].append({
            "artifact_id": "ARTIFACT_000003_002", "source_response_id": "turn_000003",
            "response_event_index": 3, "source_record_index": 3,
            "order_within_response": 2, "content": "Later();\n", "fence_label": "csharp",
            "status": "candidate_requires_review"})
        selection = pass1(pkg, candidate_artifact_ids=[
            "ARTIFACT_000003_001", "ARTIFACT_000003_002"])
        fg, _, _ = resolve_first_generation(pkg, selection)
        self.assertEqual(fg["artifact_refs"], ["ARTIFACT_000003_001"])
        self.assertEqual(len(fg["candidate_artifact_ids"]), 2)

    def test_response_local_family_with_related_later_artifacts(self):
        pkg = package()
        pkg["visible_turns"] = [
            turn(0, "user", "Initial context", 1704067200),
            turn(1, "assistant", "No artifact yet", 1704067210),
            turn(5, "user", "Generate the implementation", 1704067250),
            turn(6, "assistant", "First implementation", 1704067260),
            turn(7, "user", "Show it another way", 1704067270),
            turn(8, "assistant", "Related demonstration", 1704067280),
            turn(9, "user", "Show a refinement", 1704067290),
            turn(10, "assistant", "Related refinement", 1704067300),
        ]
        pkg["records"] = [{"message": {"role": item["role"], "content": item["text"]}}
                          for item in pkg["visible_turns"]]
        pkg["artifact_candidates"] = [
            {"artifact_id": "ARTIFACT_000006_001", "source_response_id": "turn_000006",
             "response_event_index": 6, "source_record_index": 3,
             "order_within_response": 1, "content": "FirstA();", "fence_label": "csharp",
             "status": "candidate_requires_review"},
            {"artifact_id": "ARTIFACT_000006_002", "source_response_id": "turn_000006",
             "response_event_index": 6, "source_record_index": 3,
             "order_within_response": 2, "content": "FirstB();", "fence_label": "csharp",
             "status": "candidate_requires_review"},
            {"artifact_id": "ARTIFACT_000008_001", "source_response_id": "turn_000008",
             "response_event_index": 8, "source_record_index": 5,
             "order_within_response": 1, "content": "Demo();", "fence_label": "csharp",
             "status": "candidate_requires_review"},
            {"artifact_id": "ARTIFACT_000010_001", "source_response_id": "turn_000010",
             "response_event_index": 10, "source_record_index": 7,
             "order_within_response": 1, "content": "Refine();", "fence_label": "csharp",
             "status": "candidate_requires_review"},
        ]
        selected_ids = ["ARTIFACT_000006_001", "ARTIFACT_000006_002"]
        candidates = [item["artifact_id"] for item in pkg["artifact_candidates"]]
        selection = pass1(
            pkg, artifact_ids=selected_ids, response_turn_id="turn_000006",
            target_prompt_id="turn_000005", candidate_artifact_ids=candidates)

        fg, admissible, tfg = resolve_first_generation(pkg, selection)

        self.assertEqual(fg["artifact_refs"], selected_ids)
        self.assertEqual(fg["family_id_provenance"]["canonical_input"]["artifact_ids"],
                         selected_ids)
        self.assertEqual(fg["boundary"], "exclusive_before:turn_000006")
        self.assertEqual(tfg["value"], "2024-01-01T00:01:00+00:00")
        self.assertEqual([item["turn_id"] for item in admissible],
                         ["turn_000000", "turn_000001", "turn_000005"])

        rejected = pass1(
            pkg, artifact_ids=candidates, response_turn_id="turn_000006",
            target_prompt_id="turn_000005", candidate_artifact_ids=candidates)
        with self.assertRaisesRegex(ValueError, "does not belong"):
            resolve_first_generation(pkg, rejected)

    def test_historical_pass1_v2_prompt_is_immutable(self):
        prompt = (ROOT / "prompts/stage_c/first_generation_v2.md").read_bytes()
        self.assertEqual(hashlib.sha256(prompt).hexdigest(),
                         "4fddb8abb38270bbb59cd1baa83fdcc1c9c7146c36964a830a31631e604ebfe4")

    def test_ambiguous_and_no_artifact_are_explicit_and_skip_pass2(self):
        for status in ("ambiguous", "unresolved"):
            pkg = package()
            selection = pass1(pkg, status=status, family_label="", artifact_ids=[],
                              response_turn_id="", target_prompt_id="",
                              ambiguity_reason="multiple families" if status == "ambiguous" else "no artifact")
            client = MockClient([selection])
            record = extract_stage_c(ROOT, CASE, pkg, client, CONFIG, input_ref="input.json")
            self.assertEqual(len(client.calls), 1)
            self.assertEqual(record["status"]["stage_c_status"], status)
            self.assertEqual(record["temporal"]["tFG"]["status"], "unresolved")

    def test_missing_response_time_never_substitutes_tc(self):
        pkg = package(response_time=None)
        _, _, tfg = resolve_first_generation(pkg, pass1(pkg))
        self.assertEqual(tfg["status"], "unresolved")
        self.assertNotEqual(tfg["value"], pkg["start"])

    def test_model_view_rejects_administrative_and_repository_data(self):
        pkg = package(); validate_model_view(pkg, CASE)
        for key in ("Outcome_Class", "repository", "eligibility_status"):
            with self.assertRaises(ValueError):
                validate_model_view({**pkg, key: "secret"}, CASE)

    def test_prompts_state_stage_c_leakage_boundaries(self):
        pass1_prompt = (ROOT / "prompts/stage_c/first_generation_v3.md").read_text()
        pass2_prompt = (ROOT / "prompts/stage_c/csv_extraction_v2.md").read_text()
        for prohibited in ("PA/PN", "outcomes", "final implementation", "repository"):
            self.assertIn(prohibited, pass1_prompt)
            self.assertIn(prohibited, pass2_prompt)
        for required in ("not scores", "user and assistant", "originating role",
                         "Do not infer missing information", "first-generation response",
                         "later conversation turns", "zero, one, or multiple items",
                         "supporting evidence"):
            self.assertIn(required, pass2_prompt)

    def test_pass2_v2_preserves_modality_and_diagnostic_observations(self):
        prompt = (ROOT / "prompts/stage_c/csv_extraction_v2.md").read_text()
        for observation in ("Symptoms", "failures", "historical behavior",
                            "environment", "branch", "platform differences",
                            "diagnostic observations"):
            self.assertIn(observation, prompt)
        for explicit in ("desired condition", "expected outcome or behavior",
                         "correctness condition", "check or test", "assertion",
                         "acceptance condition", "verification activity",
                         "prescriptive guidance"):
            self.assertIn(explicit, prompt)
        for unsupported in ("fix must", "solution should"):
            self.assertIn(unsupported, prompt)
        self.assertIn("works on the feature branch but produces null on main", prompt)
        self.assertIn("not supported Verification", prompt)
        self.assertIn("I expect X to return Y", prompt)
        self.assertIn("should contain the supplied value rather than null", prompt)
        self.assertIn("assistant prescriptions", prompt)
        self.assertIn("keep them separate", prompt)

    def test_pass2_v2_keeps_desired_behavior_and_assistant_prescription_permitted(self):
        prompt = (ROOT / "prompts/stage_c/csv_extraction_v2.md").read_text()
        self.assertIn("Explicit statements", prompt)
        self.assertIn("may be Verification", prompt)
        self.assertIn("assistant provenance", prompt)

    def test_structured_contracts_reject_malformed_responses(self):
        with self.assertRaises(ValueError): validate_pass1({"status": "complete"})
        with self.assertRaises(ValueError): validate_pass2({"status": "complete"}, [])
        for name in ("stage_c_pass1_v2.schema.json", "stage_c_pass2_v1.schema.json",
                     "conversation_draft_v3.schema.json"):
            schema = load_contract(ROOT, name)
            self.assertFalse(schema["additionalProperties"])
        pass1_schema = load_contract(ROOT, "stage_c_pass1_v2.schema.json")
        self.assertIn("family_label", pass1_schema["required"])
        self.assertNotIn("family_id", pass1_schema["properties"])

    def test_v2_migration_preserves_model_provenance_and_model_family_value(self):
        pkg = package()
        current = extract_stage_c(ROOT, CASE, pkg, MockClient([pass1(pkg), pass2()]),
                                  CONFIG, input_ref="input.json")
        legacy = copy.deepcopy(current)
        legacy["schema_version"] = "conversation-draft-v2"
        legacy["extraction_version"] = "conversation-extraction-v2"
        legacy["model_provenance"]["pass_2_prompt_version"] = \
            "dir-stage-c-csv-extraction-v1"
        legacy["first_generation"]["family_id"] = "model_wording"
        legacy["first_generation"].pop("family_label")
        legacy["first_generation"].pop("family_id_provenance")
        legacy.pop("record_derivation")
        original = copy.deepcopy(legacy)
        migrated = migrate_v2_record(legacy, pkg, source_record_ref="legacy.json")
        self.assertEqual(legacy, original)
        self.assertEqual(migrated["model_provenance"], original["model_provenance"])
        self.assertEqual(migrated["first_generation"]["family_label"], "model_wording")
        self.assertNotEqual(migrated["first_generation"]["family_id"], "model_wording")
        self.assertEqual(migrated["record_derivation"]["original_model_family_value"],
                         "model_wording")

    def test_api_failure_record_is_explicit_and_secret_free(self):
        record = failed_record(CASE, "input.json", "a" * 64, CONFIG, "API failure",
                               package=package())
        self.assertEqual(record["status"]["stage_c_status"], "failed")
        self.assertNotIn("secret", json.dumps(record))
        self.assertFalse(record["scientific_status"]["eligibility_updated"])
        self.assertEqual(record["temporal"]["tC"]["value"], "2024-01-01T00:00:00+00:00")
        self.assertEqual(record["temporal"]["tFG"]["status"], "unresolved")
        self.assertEqual(record["model_provenance"]["pass_2_prompt_version"],
                         "dir-stage-c-csv-extraction-v2")
        validate_stage_c_record(record)

    def _assert_rejected_pass2(self, record, parser_status, validation_status):
        self.assertEqual(record["status"]["stage_c_status"], "failed")
        self.assertEqual(record["status"]["parser_status"], parser_status)
        self.assertEqual(record["status"]["validation_status"], validation_status)
        self.assertEqual(record["model_provenance"]["pass_2_prompt_version"],
                         "dir-stage-c-csv-extraction-v2")
        self.assertEqual(record["model_provenance"]["structured_output_schema_versions"],
                         ["stage-c-pass1-v2", "stage-c-pass2-v1"])
        self.assertEqual(record["model_provenance"]["sdk_max_retries"], 2)
        self.assertEqual(len(record["model_provenance"]["invocations"]), 2)
        self.assertEqual(record["context_supplied"], [])
        self.assertEqual(record["specificity_supplied"], [])
        self.assertEqual(record["verification_supplied"], [])
        validate_stage_c_record(record)

    def _assert_rejected_pass1(self, record, diagnostic, parser_status,
                               validation_status, *, parsed):
        self.assertEqual(record["status"]["stage_c_status"], "failed")
        self.assertEqual(record["status"]["parser_status"], parser_status)
        self.assertEqual(record["status"]["validation_status"], validation_status)
        self.assertEqual(record["first_generation"]["family_id"], "")
        self.assertEqual(record["first_generation"]["boundary"], "unresolved")
        self.assertEqual(record["temporal"]["tFG"]["status"], "unresolved")
        self.assertEqual(record["context_supplied"], [])
        self.assertEqual(record["specificity_supplied"], [])
        self.assertEqual(record["verification_supplied"], [])
        self.assertFalse(diagnostic["authoritative"])
        self.assertEqual(diagnostic["disposition"], "rejected_model_output")
        self.assertEqual(diagnostic["pass"], "pass_1")
        self.assertEqual(diagnostic["parsing"]["parsed_payload_retained"], parsed)
        self.assertFalse(diagnostic["validation"]["accepted"])
        self.assertEqual(diagnostic["request_provenance"]["tools_enabled"], [])
        self.assertEqual(diagnostic["request_provenance"]["sdk_max_retries"], 2)
        self.assertEqual(diagnostic["request_provenance"]["prompt_version"],
                         "dir-stage-c-first-generation-v3")
        self.assertEqual(diagnostic["request_provenance"]["schema_version"],
                         "stage-c-pass1-v2")
        validate_stage_c_record(record)

    def test_pass1_api_failure_preserves_non_authoritative_diagnostic(self):
        metadata = {"response_id": "", "returned_model": "",
                    "invocation_timestamp": "2026-09-30T00:00:00+00:00", "usage": {}}
        failure = StageCInvocationFailure("API failed with secret", metadata,
                                          parser_status="not_run",
                                          validation_status="not_validated")
        diagnostics = []
        record = extract_stage_c(ROOT, CASE, package(), MockClient([failure]), CONFIG,
                                 input_ref="input.json", diagnostics=diagnostics)
        self._assert_rejected_pass1(record, diagnostics[0], "not_run", "not_validated",
                                    parsed=False)
        self.assertFalse(diagnostics[0]["response_provenance"]["response_received"])
        self.assertNotIn("secret", json.dumps([record, diagnostics]))

    def test_pass1_malformed_response_preserves_response_provenance(self):
        metadata = {"response_id": "response-1", "returned_model": "gpt-5.6-sol",
                    "invocation_timestamp": "2026-09-30T00:00:00+00:00", "usage": {}}
        failure = StageCInvocationFailure(
            "malformed", metadata, parser_status="malformed",
            validation_status="not_validated", response_received=True,
            structured_content_status="malformed")
        diagnostics = []
        record = extract_stage_c(ROOT, CASE, package(), MockClient([failure]), CONFIG,
                                 input_ref="input.json", diagnostics=diagnostics)
        self._assert_rejected_pass1(record, diagnostics[0], "malformed", "not_validated",
                                    parsed=False)
        self.assertTrue(diagnostics[0]["response_provenance"]["response_received"])
        self.assertEqual(diagnostics[0]["response_provenance"]["invocation"], metadata)

    def test_pass1_parsed_structural_failure_retains_rejected_payload(self):
        diagnostics = []
        rejected = {"status": "complete"}
        record = extract_stage_c(ROOT, CASE, package(), MockClient([rejected]), CONFIG,
                                 input_ref="input.json", diagnostics=diagnostics)
        self._assert_rejected_pass1(record, diagnostics[0], "parsed", "failed", parsed=True)
        self.assertEqual(diagnostics[0]["rejected_parsed_payload"], rejected)

    def test_pass1_cross_response_artifact_is_rejected_and_retained(self):
        pkg = package()
        later = {**pkg["artifact_candidates"][0],
                 "artifact_id": "ARTIFACT_000001_001",
                 "source_response_id": "turn_000001", "response_event_index": 1,
                 "source_record_index": 1}
        pkg["artifact_candidates"].append(later)
        rejected = pass1(pkg, artifact_ids=[later["artifact_id"]],
                         candidate_artifact_ids=[later["artifact_id"]])
        diagnostics = []
        client = MockClient([rejected])
        record = extract_stage_c(ROOT, CASE, pkg, client, CONFIG,
                                 input_ref="input.json", diagnostics=diagnostics)
        self._assert_rejected_pass1(record, diagnostics[0], "parsed", "failed", parsed=True)
        self.assertIn("does not belong", record["status"]["failure_reason"])
        self.assertEqual(diagnostics[0]["rejected_parsed_payload"], rejected)
        self.assertEqual(len(client.calls), 1)

    def test_pass1_invalid_target_and_artifact_id_are_rejected_and_retained(self):
        pkg = package()
        for rejected in (pass1(pkg, target_prompt_id="turn_000000"),
                         pass1(pkg, artifact_ids=["missing-artifact"])):
            diagnostics = []
            record = extract_stage_c(ROOT, CASE, pkg, MockClient([rejected]), CONFIG,
                                     input_ref="input.json", diagnostics=diagnostics)
            self._assert_rejected_pass1(record, diagnostics[0], "parsed", "failed",
                                        parsed=True)
            self.assertEqual(diagnostics[0]["rejected_parsed_payload"], rejected)

    def test_successful_pass1_emits_no_rejected_diagnostic(self):
        pkg = package(); diagnostics = []
        record = extract_stage_c(ROOT, CASE, pkg, MockClient([pass1(pkg), pass2()]), CONFIG,
                                 input_ref="input.json", diagnostics=diagnostics)
        self.assertEqual(record["status"]["stage_c_status"], "complete")
        self.assertEqual(diagnostics, [])

    def test_pass2_api_failure_preserves_invocation_provenance(self):
        metadata = {"response_id": "", "returned_model": "",
                    "invocation_timestamp": "2026-09-30T00:01:00+00:00", "usage": {}}
        failure = StageCInvocationFailure("API unavailable for secret", metadata,
                                          parser_status="not_run",
                                          validation_status="not_validated")
        pkg = package()
        record = extract_stage_c(ROOT, CASE, pkg, MockClient([pass1(pkg), failure]),
                                 CONFIG, input_ref="input.json")
        self._assert_rejected_pass2(record, "not_run", "not_validated")
        self.assertEqual(record["model_provenance"]["invocations"][1], metadata)
        self.assertNotIn("secret", json.dumps(record))

    def test_pass2_parse_failure_preserves_invocation_provenance(self):
        metadata = {"response_id": "response-2", "returned_model": "gpt-5.6-sol",
                    "invocation_timestamp": "2026-09-30T00:01:00+00:00", "usage": {}}
        failure = StageCInvocationFailure("malformed structured output", metadata,
                                          parser_status="malformed",
                                          validation_status="not_validated")
        pkg = package()
        record = extract_stage_c(ROOT, CASE, pkg, MockClient([pass1(pkg), failure]),
                                 CONFIG, input_ref="input.json")
        self._assert_rejected_pass2(record, "malformed", "not_validated")

    def test_pass2_structural_failure_emits_no_rejected_items(self):
        pkg = package()
        record = extract_stage_c(ROOT, CASE, pkg,
                                 MockClient([pass1(pkg), {"status": "complete"}]),
                                 CONFIG, input_ref="input.json")
        self._assert_rejected_pass2(record, "parsed", "failed")
        self.assertIn("structured-output contract", record["status"]["failure_reason"])

    def test_pass2_provenance_failure_emits_no_rejected_items(self):
        pkg = package()
        invalid = pass2()
        invalid["verification_supplied"][0]["source_turns"] = []
        invalid["verification_supplied"][0]["source_roles"] = []
        diagnostics = []
        client = MockClient([pass1(pkg), invalid])
        record = extract_stage_c(ROOT, CASE, pkg, client,
                                 CONFIG, input_ref="input.json", diagnostics=diagnostics)
        self._assert_rejected_pass2(record, "parsed", "failed")
        self.assertIn("provenance is incomplete", record["status"]["failure_reason"])
        self.assertEqual(diagnostics[0]["pass"], "pass_2")
        self.assertFalse(diagnostics[0]["authoritative"])
        self.assertEqual(diagnostics[0]["rejected_parsed_payload"], invalid)
        self.assertEqual(len(client.calls), 2)

    def test_openai_client_receives_configured_sdk_retry_limit(self):
        config = StageCModelConfig("secret", None, "gpt-5.6-sol", "standard", "medium",
                                   max_retries=5)
        with patch("openai.OpenAI") as constructor:
            OpenAIStageCClient(config)
        constructor.assert_called_once_with(api_key="secret", max_retries=5)

    def test_responses_api_adapter_is_independent_structured_and_tool_free(self):
        calls = []

        class Response:
            status = "completed"
            id = "resp_1"
            model = "gpt-5.6-sol"
            output_text = json.dumps(pass1(package()))
            usage = {"input_tokens": 1, "output_tokens": 1}

        class Responses:
            def create(self, **kwargs):
                calls.append(kwargs)
                return Response()

        adapter = OpenAIStageCClient.__new__(OpenAIStageCClient)
        adapter.config = CONFIG
        adapter.client = type("FakeClient", (), {"responses": Responses()})()
        parsed, metadata = adapter.invoke("prompt", {"case_id": CASE}, "schema_name",
                                          load_contract(ROOT, "stage_c_pass1_v2.schema.json"))
        self.assertEqual(parsed["status"], "complete")
        self.assertEqual(metadata["returned_model"], "gpt-5.6-sol")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["model"], "gpt-5.6-sol")
        self.assertEqual(calls[0]["reasoning"], {"mode": "standard", "effort": "medium"})
        self.assertEqual(calls[0]["tools"], [])
        self.assertTrue(calls[0]["text"]["format"]["strict"])
        self.assertNotIn("previous_response_id", calls[0])

    def test_config_missing_model_and_key_is_safe(self):
        config = load_stage_c_config(ROOT, env_file=ROOT / ".env.test-does-not-exist", environ={})
        self.assertFalse(config.structurally_valid)
        self.assertFalse(config.live_permitted)
        self.assertEqual(config.max_retries, 2)
        report = config.safe_report()
        self.assertIn("OPENAI_API_KEY: missing", report)
        self.assertNotIn("sk-", report)
        configured = load_stage_c_config(ROOT, env_file=ROOT / ".env.test-does-not-exist",
                                         environ={"DIR_STAGE_C_MODEL": "gpt-5.6-sol",
                                                        "OPENAI_API_KEY": "sk-hidden"})
        self.assertTrue(configured.live_permitted)
        self.assertNotIn("sk-hidden", configured.safe_report())

    def test_sdk_retry_configuration_accepts_only_bounded_integers(self):
        for value in (0, 1, 2, 5):
            config = load_stage_c_config(
                ROOT, env_file=ROOT / ".env.test-does-not-exist",
                environ={"DIR_STAGE_C_MODEL": "gpt-5.6-sol",
                         "DIR_STAGE_C_MAX_RETRIES": str(value)})
            self.assertEqual(config.max_retries, value)
        for value in ("-1", "6", "not-an-integer"):
            with self.assertRaisesRegex(ValueError, "integer from 0 through 5"):
                load_stage_c_config(
                    ROOT, env_file=ROOT / ".env.test-does-not-exist",
                    environ={"DIR_STAGE_C_MODEL": "gpt-5.6-sol",
                             "DIR_STAGE_C_MAX_RETRIES": value})

    def test_check_config_makes_no_api_call_and_redacts(self):
        result = subprocess.run([sys.executable, "pipeline/stage_c/run.py", "--check-config"],
                                cwd=ROOT, check=True, capture_output=True, text=True,
                                env={"PATH": str(Path(sys.executable).parent),
                                     "DIR_STAGE_C_MODEL": "gpt-5.6-sol",
                                     "DIR_STAGE_C_MAX_RETRIES": "2",
                                     "OPENAI_API_KEY": "sk-never-print"})
        self.assertIn("Configured model: gpt-5.6-sol", result.stdout)
        self.assertIn("OpenAI SDK max retries: 2", result.stdout)
        self.assertNotIn("sk-never-print", result.stdout)

    def test_final_validation_and_atomic_no_overwrite(self):
        pkg = package(); record = extract_stage_c(ROOT, CASE, pkg,
            MockClient([pass1(pkg), pass2()]), CONFIG, input_ref="input.json")
        validate_stage_c_record(record)
        self.assertEqual(record["methodology_version"], "dir-tfg-v2")
        self.assertEqual(record["schema_version"], "conversation-draft-v3")
        self.assertEqual(record["extraction_version"], "conversation-extraction-v4")
        self.assertEqual(record["model_provenance"]["pass_2_prompt_version"],
                         "dir-stage-c-csv-extraction-v2")
        self.assertEqual(record["model_provenance"]["requested_model"], "gpt-5.6-sol")
        self.assertEqual(record["model_provenance"]["tools_enabled"], [])
        self.assertEqual(len(record["model_provenance"]["invocations"]), 2)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "record.json"
            persist_stage_c(path, record)
            with self.assertRaises(FileExistsError): persist_stage_c(path, record)

    def test_cases_are_independent_calls(self):
        for suffix in ("ABCDEF123456", "123456ABCDEF"):
            pkg = package(); pkg["case_id"] = "CASE_" + suffix
            client = MockClient([pass1(pkg), pass2()])
            extract_stage_c(ROOT, pkg["case_id"], pkg, client, CONFIG, input_ref="input.json")
            self.assertEqual(len(client.calls), 2)


if __name__ == "__main__":
    unittest.main()
