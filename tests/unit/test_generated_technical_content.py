"""Stage B V2 generated-technical-content contract tests."""

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from developer_intent.generated_technical_content import (  # noqa: E402
    build_v2_model_view, candidate_id, compare_v1_v2, detect_turn_candidates,
    validate_v2_model_view,
)
from developer_intent.stage_c import (  # noqa: E402
    deterministic_family_identity, extract_stage_c, resolve_first_generation,
    validate_model_view,
)
from developer_intent.stage_c_config import StageCModelConfig  # noqa: E402


def normalized(texts):
    turns = []
    records = []
    for index, (role, text) in enumerate(texts):
        turn = {"turn_id": f"turn_{index:06d}", "event_index": index, "role": role,
                "text": text, "create_time": f"2024-01-{index + 1:02d}T00:00:00Z",
                "source_record_index": index, "source_node_id": None,
                "source_parent_id": None}
        turns.append(turn)
        records.append({"message": {"author": {"role": role},
                        "content": {"parts": [text]}, "create_time": turn["create_time"]}})
    return {"normalized_version": "lossless-conversation-v1",
            "methodology_version": "dir-tfg-v2", "case_id": "CASE_123456789ABC",
            "start": "2024-01-01T00:00:00Z", "precision": "timestamp",
            "temporal_status": "exact", "temporal_source": "first developer turn",
            "source_archive_sha256": "", "source_conversation_sha256": "a" * 64,
            "visible_turns": turns, "artifact_candidates": [], "records": records,
            "tool_trace": [], "other_records": [], "raw_conversation": {},
            "normalization_limitations": [], "complete": True,
            "reconstruction_safe": False}


def candidates(text):
    return detect_turn_candidates({"turn_id": "turn_000001", "event_index": 1,
                                   "source_record_index": 1, "role": "assistant",
                                   "text": text})


class GeneratedTechnicalContentTests(unittest.TestCase):
    def test_identity_is_span_based_and_semantic_fields_do_not_affect_it(self):
        digest = hashlib.sha256("λ=1".encode()).hexdigest()
        value = candidate_id(5, 2, 5, digest)
        self.assertEqual(value, "GTC_000005_000002_000005_" + digest[:16])
        self.assertEqual(len(value.rsplit("_", 1)[1]), 16)
        self.assertEqual(value, candidate_id(5, 2, 5, digest))
        # Kind and completeness are deliberately absent from this function.
        self.assertNotEqual(value, candidate_id(5, 1, 5, digest))

    def test_unicode_offsets_hashes_order_and_validation(self):
        data = normalized([("user", "ask"),
                           ("assistant", "é🙂\n```python\nprint('λ')\n```\n")])
        view = build_v2_model_view(data)
        item = view["generated_technical_content_candidates"][0]
        turn = data["visible_turns"][1]["text"]
        self.assertEqual(item["raw_text"], turn[item["start_offset"]:item["end_offset"]])
        self.assertEqual(item["raw_text_sha256"], hashlib.sha256(item["raw_text"].encode()).hexdigest())
        self.assertEqual(item["source_turn_text_sha256"], hashlib.sha256(turn.encode()).hexdigest())
        self.assertEqual(item["order_within_response"], 1)
        validate_v2_model_view(view)
        for field, replacement in (("raw_text", "changed"), ("start_offset", 0),
                                   ("raw_text_sha256", "0" * 64)):
            altered = copy.deepcopy(view)
            altered["generated_technical_content_candidates"][0][field] = replacement
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_v2_model_view(altered)

    def test_collision_and_duplicate_span_fail(self):
        data = normalized([("user", "ask"),
                           ("assistant", "```python\na=1\n```\n\n```python\nb=2\n```\n")])
        with patch("developer_intent.generated_technical_content.candidate_id",
                   return_value="GTC_000001_000000_000001_0000000000000000"):
            with self.assertRaisesRegex(ValueError, "collision"):
                build_v2_model_view(data)

    def test_markdown_indentation_tagging_and_exclusions(self):
        for indent in ("", "  ", "   ", "    ", "      ", "          ", "\t"):
            with self.subTest(indent=repr(indent)):
                found = candidates(f"{indent}```python\nprint(1)\n{indent}```\n")
                self.assertEqual(len(found), 1)
                self.assertEqual(found[0]["container"], "markdown_fence")
                self.assertEqual(found[0]["kind"], "source_code")
                self.assertEqual(found[0]["completeness"], "complete")
        self.assertEqual(len(candidates("```\nconst x = 1;\nreturn x;\n```\n")), 1)
        self.assertEqual(candidates("prose ```python\nx=1\n``` trailing"), [])
        self.assertEqual(candidates("before ```python\nx=1\n```"), [])
        self.assertEqual(candidates("```python\nx=1\n  ```\n"), [])

    def test_incomplete_orphan_cross_response_and_ambiguity(self):
        labelled = candidates("```python\nprint(1)\n")
        self.assertEqual(labelled[0]["completeness"], "open_ended")
        self.assertEqual(labelled[0]["continuation"], "ends_mid_structure")
        unlabelled = candidates("```\nimport os\ndef f():\n    return os.getcwd()\n")
        self.assertEqual(len(unlabelled), 1)
        self.assertEqual(candidates("```\nordinary prose only\n"), [])
        self.assertEqual(candidates("```\n"), [])
        self.assertEqual(candidates("```python\nx=1\n  ```js\ny=2\n```\n"), [])
        nested_text = "```python\ntext = '''\n  ```\n  example\n  ```\n'''\n```\n"
        nested = candidates(nested_text)
        self.assertEqual(len(nested), 1)
        self.assertEqual(nested[0]["start"], len("```python\n"))
        self.assertIn("  ```\n  example\n  ```",
                      nested_text[nested[0]["start"]:nested[0]["end"]])
        data = normalized([("user", "ask"), ("assistant", "```python\nprint(1)\n"),
                           ("assistant", "```\n")])
        view = build_v2_model_view(data)
        self.assertEqual(len(view["generated_technical_content_candidates"]), 1)
        self.assertEqual(view["generated_technical_content_candidates"][0]["source_response_id"],
                         "turn_000001")

    def test_markup_detection_and_false_positives(self):
        samples = {
            "<resources>\n<string name=\"a\">A</string>\n<string name=\"b\">B</string>\n</resources>\n": "complete",
            "<string name=\"a\">A</string>\n<string name=\"b\">B</string>\n<string name=\"c\"": "fragment",
            "<root><child>A</child><child>B</child></root>": "complete",
            "<div><span>A</span><span>B</span></div>": "complete",
            "<svg><path d=\"M0 0\"/><path d=\"M1 1\"/></svg>": "complete",
        }
        for text, completeness in samples.items():
            with self.subTest(text=text[:20]):
                found = candidates(text)
                self.assertEqual(len(found), 1)
                self.assertEqual(found[0]["kind"], "structured_xml_markup")
                self.assertEqual(found[0]["completeness"], completeness)
        for text in ("Use <name> here in prose.", "if a < b and c > d", "<broken prose"):
            with self.subTest(excluded=text):
                self.assertEqual(candidates(text), [])

    def test_source_shell_and_configuration_detectors(self):
        source = "import os\n\ndef f(x):\n    if x:\n        return os.path.join('a', x)\n"
        js = "const f = (x) => {\n  if (x) {\n    return call(x);\n  }\n};\n"
        for text in (source, js):
            self.assertEqual(candidates(text)[0]["kind"], "source_code")
        for text in ("x = 1", "Mention fetchData() in prose.", "Step 1 then Step 2 then stop."):
            self.assertEqual(candidates(text), [])
        self.assertEqual(candidates("git status\nmake test\n")[0]["kind"], "shell_sequence")
        self.assertEqual(candidates("git status | cat > out.txt\n")[0]["kind"], "shell_sequence")
        self.assertEqual(candidates("curl example.com \\\n+  | jq .\n")[0]["kind"], "shell_sequence")
        self.assertEqual(candidates("Run git status to check the repository"), [])
        self.assertEqual(candidates("git status"), [])
        self.assertEqual(candidates("API_KEY=x\nMODE=test\n")[0]["kind"],
                         "configuration_properties")
        self.assertEqual(candidates("db.host=x\ndb.port=1\n")[0]["kind"],
                         "configuration_properties")
        self.assertEqual(candidates("[server]\nhost=localhost\n")[0]["kind"],
                         "configuration_properties")
        self.assertEqual(candidates("local = 1\nother = 2\n"), [])

    def test_json_yaml_and_overlap(self):
        fenced_json = candidates("```json\n{\"a\": [1, 2]}\n```\n")
        self.assertEqual(len(fenced_json), 1)
        self.assertEqual(fenced_json[0]["kind"], "structured_json")
        self.assertEqual(candidates('{"a": 1}'), [])  # standalone discovery deferred
        self.assertEqual(candidates("a: 1\nb: 2\n"), [])
        yaml = candidates("```yaml\na: 1\nb: 2\n```\n")
        self.assertEqual(yaml[0]["kind"], "unclassified_technical")
        fenced_xml = candidates("```xml\n<resources><string name=\"a\">A</string><string name=\"b\">B</string></resources>\n```\n")
        self.assertEqual(len(fenced_xml), 1)
        self.assertEqual(fenced_xml[0]["kind"], "structured_xml_markup")
        distinct = candidates("```python\nprint(1)\n```\ngit status | cat > out.txt\n")
        self.assertEqual([item["kind"] for item in distinct],
                         ["source_code", "shell_sequence"])

    def test_legacy_mapping_and_migration_failure(self):
        text = "```python\nprint(1)\n```"
        data = normalized([("user", "ask"), ("assistant", text)])
        data["artifact_candidates"] = [{"artifact_id": "ARTIFACT_000001_001",
            "source_response_id": "turn_000001", "response_event_index": 1,
            "source_record_index": 1, "order_within_response": 1,
            "fence_label": "python", "content": "print(1)\n",
            "status": "candidate_requires_review"}]
        view = build_v2_model_view(data)
        item = view["generated_technical_content_candidates"][0]
        self.assertEqual(item["legacy_artifact_id"], "ARTIFACT_000001_001")
        self.assertEqual(compare_v1_v2(data, view)[0]["classification"],
                         "exact_v1_equivalent")
        altered = copy.deepcopy(view)
        altered["generated_technical_content_candidates"][0]["legacy_artifact_id"] = None
        with self.assertRaisesRegex(ValueError, "missing"):
            compare_v1_v2(data, altered)
        report = compare_v1_v2(data, altered, strict=False)
        self.assertIn("v1_candidate_missing", {item["classification"] for item in report})
        self.assertIn("changed_span", {item["classification"] for item in report})

    def test_stage_c_accepts_v2_and_enforces_response_local_selection(self):
        data = normalized([("user", "make it"),
                           ("assistant", "```python\nprint(1)\n```"),
                           ("assistant", "```python\nprint(2)\n```")])
        view = build_v2_model_view(data)
        validate_model_view(view, data["case_id"])
        first, second = view["generated_technical_content_candidates"]
        selection = {"status": "complete", "family_label": "prints",
                     "artifact_ids": [first["candidate_id"]],
                     "response_turn_id": "turn_000001", "target_prompt_id": "turn_000000",
                     "candidate_artifact_ids": [first["candidate_id"], second["candidate_id"]],
                     "rationale": "first generated response", "ambiguity_reason": ""}
        fg, admissible, tfg = resolve_first_generation(view, selection)
        self.assertTrue(fg["family_id"].startswith("FGF_"))
        self.assertEqual(fg["artifact_refs"], [first["candidate_id"]])
        self.assertEqual([turn["turn_id"] for turn in admissible], ["turn_000000"])
        self.assertNotEqual(tfg["value"], "")
        bad = copy.deepcopy(selection); bad["artifact_ids"] = [second["candidate_id"]]
        with self.assertRaises(ValueError):
            resolve_first_generation(view, bad)
        missing = copy.deepcopy(selection); missing["artifact_ids"] = ["GTC_000000_000000_000001_0000000000000000"]
        with self.assertRaises(ValueError):
            resolve_first_generation(view, missing)
        unresolved = copy.deepcopy(selection); unresolved.update(status="unresolved", artifact_ids=[], response_turn_id="", target_prompt_id="")
        _, _, no_tfg = resolve_first_generation(view, unresolved)
        self.assertEqual(no_tfg["status"], "unresolved")
        family1 = deterministic_family_identity(data["case_id"], [first])[0]
        family2 = deterministic_family_identity(data["case_id"], [copy.deepcopy(first)])[0]
        self.assertEqual(family1, family2)

    def test_stage_c_v2_uses_v4_prompt_and_v5_record_without_api(self):
        data = normalized([("user", "make it"),
                           ("assistant", "```python\nprint(1)\n```")])
        view = build_v2_model_view(data)
        item = view["generated_technical_content_candidates"][0]

        class Client:
            def __init__(self): self.calls = []
            def invoke(self, prompt, payload, schema_name, schema):
                self.calls.append((prompt, copy.deepcopy(payload)))
                if len(self.calls) == 1:
                    value = {"status": "complete", "family_label": "print",
                             "artifact_ids": [item["candidate_id"]],
                             "response_turn_id": "turn_000001",
                             "target_prompt_id": "turn_000000",
                             "candidate_artifact_ids": [item["candidate_id"]],
                             "rationale": "first", "ambiguity_reason": ""}
                else:
                    value = {"status": "complete", "context_supplied": [],
                             "specificity_supplied": [], "verification_supplied": [],
                             "failure_reason": ""}
                return value, {"response_id": f"offline-{len(self.calls)}",
                               "returned_model": "offline-test", "usage": {}}

        client = Client()
        config = StageCModelConfig(None, None, "offline-test", "standard", "medium")
        record = extract_stage_c(ROOT, data["case_id"], view, client, config,
                                 input_ref="/tmp/stage_c_model_view_v2.json")
        self.assertEqual(record["extraction_version"], "conversation-extraction-v5")
        self.assertEqual(record["model_provenance"]["pass_1_prompt_version"],
                         "dir-stage-c-first-generation-v4")
        self.assertIn("generated_technical_content_candidates", client.calls[0][0])
        self.assertEqual(client.calls[1][1]["admissible_prior_turns"],
                         [view["visible_turns"][0]])

    def test_real_case_fixtures_do_not_modify_canonical_files(self):
        expectations = {
            "CASE_AADA2C787EEE": ("turn_000005", "structured_xml_markup", None),
            "CASE_5A3A043A5011": ("turn_000003", "source_code", None),
            "CASE_E8F12807DBDC": ("turn_000003", "source_code", None),
            "CASE_BD3DEF3FC202": ("turn_000003", "shell_sequence", "ARTIFACT_000003_001"),
        }
        for case_id, (turn_id, kind, legacy) in expectations.items():
            path = ROOT / "cases/conversations" / case_id / "normalized_conversation.json"
            before = hashlib.sha256(path.read_bytes()).hexdigest()
            view = build_v2_model_view(json.loads(path.read_text()))
            matching = [item for item in view["generated_technical_content_candidates"]
                        if item["source_response_id"] == turn_id]
            self.assertTrue(matching, case_id)
            self.assertEqual(matching[0]["kind"], kind)
            self.assertEqual(matching[0]["legacy_artifact_id"], legacy)
            self.assertTrue(all(item["candidate_id"].startswith("GTC_") for item in matching))
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), before)


if __name__ == "__main__":
    unittest.main()
