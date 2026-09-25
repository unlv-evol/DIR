"""Protocol v5 conversation isolation and first-generation boundaries."""

import json
import base64
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from developer_intent.conversation_package import (  # noqa: E402
    build_case_linkage_record, build_conversation_package, build_source_archive,
    draft_supplied_record, freeze_validated_record, normalize_conversation,
    prepare_conversation_layers,
)
from developer_intent.screening_chatgpt import parse_share  # noqa: E402


def conversation_payload():
    messages = [
        {"role": "user", "create_time": 1704067200, "content": {"parts": ["initial context"]}},
        {"role": "assistant", "content": {"parts": ["acknowledged"]}},
        {"role": "user", "content": {"parts": ["implement feature"]}},
        {"role": "assistant", "recipient": "browser", "content": {"content_type": "code", "text": "search"}},
        {"role": "tool", "content": {"content_type": "result", "text": "project data"}},
        {"role": "assistant", "create_time": 1704153600,
         "content": {"parts": ["```python\nprint('artifact')\n```"]}},
        {"role": "user", "content": {"parts": ["later request"]}},
    ]
    return json.dumps({"messages": messages}).encode()


def parsed_conversation():
    return parse_share(conversation_payload())


class ConversationPackageTests(unittest.TestCase):
    @staticmethod
    def freeze_options(**changes):
        options = {"procedure_validation_status": "validated",
                   "stage_a_eligibility_status": "eligible",
                   "case_human_validation_status": "not_sampled",
                   "case_extraction_status": "completed",
                   "case_boundary_status": "established",
                   "case_processability_status": "passed"}
        options.update(changes)
        return options

    def test_package_exposes_no_project_fields_or_tool_content(self):
        package = build_conversation_package("CASE_X", parsed_conversation())
        self.assertEqual(package["methodology_version"], "dir-tfg-v2")
        self.assertFalse({"pr", "repository", "Outcome_Class", "pr_url", "files"} & set(package))
        self.assertNotIn("project data", json.dumps(package))
        self.assertEqual(package["visible_turns"][-1]["text"], "later request")
        self.assertEqual(package["artifact_candidates"][0]["source_response_id"], "turn_000005")
        self.assertEqual(package["artifact_candidates"][0]["content"], "print('artifact')\n")

    def test_restricted_linkage_and_three_layers(self):
        row = {"case_id": "CASE_X", "source_case_id": "PA-1",
               "pr_url": "https://github.com/acme/repo/pull/1",
               "repository": "acme/repo", "pr_number": "1",
               "conversation_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
               "conversation_url": "https://chatgpt.com/share/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
               "Outcome_Class": "PA", "case_integrity_status": "ok"}
        linkage = build_case_linkage_record(row)
        archive, normalized, view = prepare_conversation_layers(
            "CASE_X", conversation_payload(), source_url=row["conversation_url"],
            retrieval_status="retrieved_public", retrieved_at="2024-01-03T00:00:00+00:00",
            content_type="application/json", http_status=200)
        self.assertEqual(linkage["case_id"], normalized["case_id"])
        self.assertEqual(view["case_id"], linkage["case_id"])
        self.assertEqual(linkage["pr_url"], row["pr_url"])
        self.assertEqual(base64.b64decode(archive["source_payload_base64"]),
                         conversation_payload())
        self.assertEqual(normalized["source_archive_sha256"], archive["source_sha256"])
        self.assertEqual(archive["source_format"], "structured_json")
        self.assertEqual(len(normalized["records"]), 7)
        self.assertEqual([turn["event_index"] for turn in normalized["visible_turns"]],
                         [0, 1, 2, 5, 6])
        self.assertEqual(normalized["records"][5]["message"]["content"]["parts"][0],
                         "```python\nprint('artifact')\n```")
        self.assertEqual(normalized["visible_turns"][-1]["text"], "later request")
        self.assertEqual(normalized["visible_turns"][3]["source_record_index"], 5)
        self.assertEqual(normalized["artifact_candidates"][0]["source_record_index"], 5)
        self.assertEqual(len(normalized["tool_trace"]), 2)
        self.assertFalse({"pr_url", "pr_number", "repository", "Outcome_Class"} & set(view))
        self.assertNotIn(row["pr_url"], json.dumps(view))
        self.assertNotIn("project data", json.dumps(view))

    def test_unhandled_elements_reported_and_credentials_not_archived(self):
        source = "https://chatgpt.com/share/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        parsed = parsed_conversation()
        parsed["records"].insert(0, {"node_id": "root", "parent": None,
                                       "message": None, "unhandled": {"type": "source-marker"}})
        normalized = normalize_conversation("CASE_X", parsed)
        self.assertIn("non_message_source_record_preserved:0",
                      normalized["normalization_limitations"])
        self.assertEqual(normalized["records"][0]["unhandled"],
                         {"type": "source-marker"})
        archive = build_source_archive("CASE_X", conversation_payload(),
                                       source_url=source, retrieval_status="retrieved_public",
                                       retrieved_at="2024-01-03T00:00:00Z")
        archive_text = json.dumps(archive)
        self.assertNotIn("Authorization", archive_text)
        self.assertNotIn("Cookie", archive_text)
        with self.assertRaises(ValueError):
            build_source_archive("CASE_X", conversation_payload(),
                                 source_url=source + "?token=secret",
                                 retrieval_status="retrieved_public",
                                 retrieved_at="2024-01-03T00:00:00Z")
        unsupported_archive, no_normalized, no_view = prepare_conversation_layers(
            "CASE_X", b"<html>unsupported</html>", source_url=source,
            retrieval_status="retrieved_public", retrieved_at="2024-01-03T00:00:00Z")
        self.assertEqual(unsupported_archive["normalization_status"],
                         "unsupported_or_malformed")
        self.assertEqual(base64.b64decode(unsupported_archive["source_payload_base64"]),
                         b"<html>unsupported</html>")
        self.assertIsNone(no_normalized)
        self.assertIsNone(no_view)

    def test_draft_uses_only_target_and_prior_turns(self):
        package = build_conversation_package("CASE_X", parsed_conversation())
        ref = {"artifact_id": package["artifact_candidates"][0]["artifact_id"],
               "family_id": "F1", "response_event_index": 5, "generation_order": 1}
        item = {"item_id": "C1", "category": "Context", "text": "initial context",
                "source_turn_id": "turn_000000"}
        draft = draft_supplied_record(package, [ref], [item])
        self.assertEqual(draft["methodology_version"], "dir-tfg-v2")
        self.assertEqual(draft["target_prompt_id"], "turn_000002")
        self.assertEqual(draft["first_generation_response_id"], "turn_000005")
        self.assertEqual(draft["allowed_prior_turn_ids"], ["turn_000000", "turn_000001"])
        self.assertNotIn("later request", json.dumps(draft))
        self.assertNotIn("artifact", json.dumps(draft["context_supplied"]))
        self.assertEqual(draft["primary_repository_cutoff"], "tFG")
        self.assertNotIn("pr_conversation_match", draft)
        self.assertNotIn("correspondence_validation", draft)
        with self.assertRaises(ValueError):
            draft_supplied_record(package, [ref], [{**item, "source_turn_id": "turn_000006"}])
        with self.assertRaises(ValueError):
            draft_supplied_record({**package, "pr_url": "secret"}, [ref], [])
        with self.assertRaises(ValueError):
            draft_supplied_record(package, [ref], [{**item, "text": "project facts"}])
        with self.assertRaises(ValueError):
            draft_supplied_record(package, [{**ref, "artifact_id": "not_in_package"}], [])

    def test_freeze_requires_validation_and_never_defaults_tfg(self):
        package = build_conversation_package("CASE_X", parsed_conversation())
        draft = draft_supplied_record(package, [{"artifact_id": "ARTIFACT_000005_001", "family_id": "F1",
                                                  "response_event_index": 5,
                                                  "generation_order": 1}], [])
        self.assertEqual(draft["conversation_start_time"]["precision"], "timestamp")
        self.assertEqual(draft["first_generation_cutoff"]["precision"], "timestamp")
        with self.assertRaises(ValueError):
            freeze_validated_record(draft, **self.freeze_options(
                procedure_validation_status="pending"))
        with self.assertRaises(ValueError):
            freeze_validated_record(draft, **self.freeze_options(
                stage_a_eligibility_status="pending_resolution"))
        frozen = freeze_validated_record(draft, **self.freeze_options())
        self.assertEqual(frozen["record_status"], "frozen")
        self.assertEqual(frozen["validation_status"], "procedure_validated")
        self.assertEqual(frozen["case_human_validation_status"], "not_sampled")
        self.assertEqual(frozen["validation_judgments"], [])
        for field, value in (("case_extraction_status", "failed"),
                             ("case_boundary_status", "unresolved"),
                             ("case_processability_status", "failed")):
            with self.assertRaises(ValueError):
                freeze_validated_record(draft, **self.freeze_options(**{field: value}))
        with self.assertRaises(ValueError):
            freeze_validated_record(draft, **self.freeze_options(
                systematic_defect_affects_case=True))
        no_time = parsed_conversation()
        no_time["records"][5]["message"].pop("create_time", None)
        unresolved = draft_supplied_record(build_conversation_package("CASE_X", no_time),
                                            [{"artifact_id": "ARTIFACT_000005_001", "family_id": "F1",
                                              "response_event_index": 5,
                                              "generation_order": 1}], [])
        self.assertEqual(unresolved["first_generation_cutoff"]["status"], "unresolved")
        self.assertNotEqual(unresolved["first_generation_cutoff"],
                            unresolved["conversation_start_time"])
        with self.assertRaises(ValueError):
            freeze_validated_record(unresolved, **self.freeze_options())

    def test_sampled_status_requires_independent_judgments(self):
        package = build_conversation_package("CASE_X", parsed_conversation())
        draft = draft_supplied_record(package, [{"artifact_id": "ARTIFACT_000005_001",
                                                  "family_id": "F1", "response_event_index": 5,
                                                  "generation_order": 1}], [])
        judgment = {"validator_id": "reviewer-1", "boundary_correct": True,
                    "target_prompt_correct": True, "item_supported": True,
                    "category_assignment_correct": True, "provenance_correct": True,
                    "future_information_leakage": False, "items": []}
        with self.assertRaises(ValueError):
            freeze_validated_record(draft, **self.freeze_options(
                case_human_validation_status="sampled_human_validated",
                independent_judgments=[judgment]))
        frozen = freeze_validated_record(draft, **self.freeze_options(
            case_human_validation_status="sampled_human_validated",
            independent_judgments=[judgment, {**judgment, "validator_id": "reviewer-2"}]))
        self.assertEqual(frozen["case_human_validation_status"], "sampled_human_validated")
        self.assertEqual(len(frozen["validation_judgments"]), 2)
        with self.assertRaises(ValueError):
            freeze_validated_record(draft, **self.freeze_options(
                case_human_validation_status="sampled_adjudicated",
                independent_judgments=[judgment, {**judgment, "validator_id": "reviewer-2"}]))


if __name__ == "__main__":
    unittest.main()
