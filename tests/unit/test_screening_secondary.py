import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from developer_intent.screening_secondary import secondary_characteristics  # noqa: E402


class SecondaryCharacteristicsTests(unittest.TestCase):
    def test_positive_signals_preserve_turn_and_literal_cue(self):
        conversation = {"complete": True, "turns": [
            {"role": "user", "text": "Please fix the error in src/app.py; see https://example.org/log.\n"
                                     "```python\nassert result == 1\n```"},
            {"role": "assistant", "text": "A reply with an unrelated URL."},
            {"role": "user", "text": "Does `process()` pass the test?"},
        ]}
        result = secondary_characteristics(conversation)
        self.assertEqual(result["conversation_turn_pattern"], "multiple_developer_prompts")
        for field in ("prompt_identifier_signal", "prompt_file_path_signal",
                      "prompt_code_fragment_signal", "prompt_error_log_signal",
                      "prompt_test_assertion_signal", "prompt_url_signal"):
            self.assertEqual(result[field], "detected")
        evidence = json.loads(result["secondary_characteristics_evidence"])
        self.assertEqual(evidence["prompt_url_signal"]["developer_turn"], 1)
        self.assertEqual(result["generated_artifact_pattern_status"], "not_assessed")
        self.assertEqual(result["share_link_contributor_role_status"], "not_assessed")
        self.assertEqual(result["help_seeking_context_status"], "not_assessed")

    def test_unavailable_and_not_detected_are_distinct(self):
        missing = secondary_characteristics(None)
        self.assertEqual(missing["prompt_url_signal"], "unavailable")
        self.assertEqual(missing["conversation_turn_pattern"], "unavailable")
        self.assertEqual(missing["help_seeking_context_cues"], "")
        plain = secondary_characteristics({"complete": True, "turns": [
            {"role": "user", "text": "Hello there"},
            {"role": "assistant", "text": "https://example.org/a.py"},
        ]})
        self.assertEqual(plain["prompt_url_signal"], "not_detected_by_rule")
        self.assertEqual(plain["prompt_file_path_signal"], "not_detected_by_rule")
        self.assertEqual(plain["conversation_turn_pattern"], "single_developer_prompt")
        self.assertEqual(plain["help_seeking_context_cues"], "[]")


if __name__ == "__main__":
    unittest.main()
