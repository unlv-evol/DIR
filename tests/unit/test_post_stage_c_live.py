from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from developer_intent.post_stage_c import initialize_eligibility_rows, select_pilot
from developer_intent.post_stage_c_live import (
    FROZEN_CASES, execute_case, load_live_config, preflight, safe_config_report,
)

ROOT = Path(__file__).resolve().parents[2]


class PostStageCLiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = initialize_eligibility_rows(ROOT)

    def test_config_is_bounded_and_secret_free(self):
        config = load_live_config(ROOT, environ={"GITHUB_TOKEN": "secret",
                                                 "DIR_POST_C_TRANSPORT_RETRIES": "2"})
        report = safe_config_report(config)
        self.assertEqual(report["transport_retries"], 2)
        self.assertEqual(report["github_token"], "configured")
        self.assertNotIn("secret", json.dumps(report))
        self.assertFalse(report["outcome_inputs_enabled"])
        with self.assertRaises(ValueError):
            load_live_config(ROOT, environ={"DIR_POST_C_TRANSPORT_RETRIES": "3"})

    def test_repository_preflight_has_exact_frozen_population(self):
        pilot, eligibility = preflight(ROOT, require_unexecuted=False)
        self.assertEqual(tuple(r["case_id"] for r in pilot), FROZEN_CASES)
        self.assertTrue(all(case_id in eligibility for case_id in FROZEN_CASES))

    def test_current_metadata_remains_supporting_and_skips_git(self):
        source = next(r for r in self.rows if r["case_id"] == FROZEN_CASES[0])
        pilot = select_pilot(ROOT, self.rows)[0]
        payload = {"number": int(source["pr_number"]),
                   "created_at": "2023-12-11T20:48:11Z",
                   "updated_at": "2023-12-18T19:07:59Z",
                   "base": {"sha": "a" * 40}, "merged": True,
                   "diff_url": "PROHIBITED_NOT_PERSISTED"}

        def get(url, token, timeout):
            return {"status": "success", "http_status": 200,
                    "body": json.dumps(payload).encode(),
                    "retrieved_at": "2026-10-01T00:00:00+00:00", "final_url": url}

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority = ROOT / source["stage_c_authoritative_record"]
            destination = root / source["stage_c_authoritative_record"]
            destination.parent.mkdir(parents=True)
            shutil.copy2(authority, destination)
            result = execute_case(root, dict(source), dict(pilot),
                                  {"github_token": None, "timeout": 1,
                                   "transport_retries": 2}, get=get,
                                  sleep=lambda _: None)
            record = result["record"]
            self.assertEqual(result["git_operations"], 0)
            self.assertEqual(record["target_selection"]["identity_status"], "unresolved")
            self.assertEqual(record["historical_state_reconstructible"], "unresolved")
            self.assertEqual(record["object_validation"]["object_sha"], "")
            self.assertEqual(record["target_selection"]["historical_identity_evidence"][0]
                             ["evidence_level"], "level_4_present_day_pr_metadata")
            evidence = json.loads((root / "cases/reconstruction" / source["case_id"] /
                                   "evidence/current_pr_metadata_sanitized.json").read_text())
            self.assertNotIn("merged", evidence)
            self.assertNotIn("diff_url", evidence)

    def test_transient_retries_are_bounded_and_remain_unresolved(self):
        source = next(r for r in self.rows if r["case_id"] == FROZEN_CASES[0])
        pilot = select_pilot(ROOT, self.rows)[0]
        calls = []

        def get(url, token, timeout):
            calls.append(url)
            return {"status": "timed_out", "http_status": 0, "body": b"",
                    "retrieved_at": f"2026-10-01T00:00:0{len(calls)}+00:00",
                    "final_url": url}

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority = ROOT / source["stage_c_authoritative_record"]
            destination = root / source["stage_c_authoritative_record"]
            destination.parent.mkdir(parents=True)
            shutil.copy2(authority, destination)
            result = execute_case(root, dict(source), dict(pilot),
                                  {"github_token": None, "timeout": 1,
                                   "transport_retries": 2}, get=get,
                                  sleep=lambda _: None)
            self.assertEqual(len(calls), 3)
            self.assertEqual(len(result["record"]["attempts"]), 3)
            self.assertEqual(result["record"]["failure_category"], "timed_out")
            self.assertEqual(result["record"]["historical_state_reconstructible"],
                             "unresolved")


if __name__ == "__main__":
    unittest.main()
