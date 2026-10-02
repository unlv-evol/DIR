from __future__ import annotations

import csv
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from developer_intent.post_stage_c_v2 import read_csv
from developer_intent.post_stage_c_v2_live import execute_case, output_paths, preflight, run_pilot

ROOT = Path(__file__).resolve().parents[2]


def provider(row, *, status="success", created_at="2023-01-01T00:00:00Z"):
    body = {"number": int(row["pr_number"]), "created_at": created_at,
            "base": {"sha": "e" * 40}, "merged": True, "diff_url": "forbidden"}
    return {"status": status, "http_status": 200 if status == "success" else 503,
            "body": json.dumps(body).encode() if status == "success" else b"",
            "retrieved_at": "2026-10-02T00:00:00+00:00", "final_url": "mock"}


def b2_archive(root, case_id, audit):
    from developer_intent.post_stage_c_v2_live import _claim
    return [_claim(case_id, "B4", "a" * 40, "archive.json", "2023-01-01T00:00:00Z",
                   "at_or_before", "established", "unresolved",
                   rule="archived_pr_commit_membership_lead", inputs=["archive.json"])]


class PostStageCV2LiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.eligibility = {r["case_id"]: r for r in read_csv(ROOT / "cases/manifests/post_stage_c_eligibility.csv")}
        cls.audit = {r["case_id"]: r for r in read_csv(ROOT / "cases/manifests/post_stage_c_historical_target_audit.csv")}

    def test_current_metadata_and_fetchability_do_not_select_target(self):
        row = self.eligibility["CASE_97AFC2022473"]
        with tempfile.TemporaryDirectory() as directory:
            result = execute_case(Path(directory), row, self.audit[row["case_id"]],
                                  {"github_token": None, "timeout": 1, "transport_retries": 0},
                                  get=lambda *args: provider(row, created_at=self.audit[row["case_id"]]["pr_created_at"]), archive_loader=lambda *args: [],
                                  relationship_probe=lambda *args, **kwargs: self.fail("unexpected Git probe"),
                                  materializer=lambda *args, **kwargs: self.fail("unexpected materialization"))
        self.assertEqual(result["record"]["target_identity_status"], "unresolved")
        self.assertEqual(result["record"]["historical_state_reconstructible"], "unresolved")
        self.assertEqual(result["git_operations"], 0)
        self.assertEqual(result["record"]["evidence_claims"][0]["evidence_level"], "B5")

    def test_valid_b2_derivation_then_materialization(self):
        row = self.eligibility["CASE_97AFC2022473"]
        probe = lambda *args, **kwargs: {"status": "validated", "remote_operations": 1,
            "requested_sha": "a" * 40, "parent_sha": "b" * 40,
            "tree_sha": "c" * 40, "commit_time": "2023-01-01T00:00:00Z"}
        material = lambda *args, **kwargs: {"status": "validated", "remote_operations": 1,
            "object_type": "commit", "tree_sha": "d" * 40, "deterministic_repeat": True}
        with tempfile.TemporaryDirectory() as directory:
            result = execute_case(Path(directory), row, self.audit[row["case_id"]],
                                  {"github_token": None, "timeout": 1, "transport_retries": 0},
                                  get=lambda *args: provider(row, created_at=self.audit[row["case_id"]]["pr_created_at"]), archive_loader=b2_archive,
                                  relationship_probe=probe, materializer=material)
        self.assertEqual(result["record"]["authoritative_R_i_tFG"], "b" * 40)
        self.assertEqual(result["record"]["historical_state_reconstructible"], "yes")
        self.assertEqual(result["git_operations"], 2)

    def test_post_tfg_pr_does_not_block_independent_b2(self):
        row = self.eligibility["CASE_85AD863F8290"]
        def late(*args):
            return provider(row, created_at=self.audit[row["case_id"]]["pr_created_at"])
        probe = lambda *args, **kwargs: {"status": "validated", "remote_operations": 1,
            "requested_sha": "a" * 40, "parent_sha": "b" * 40,
            "tree_sha": "c" * 40, "commit_time": "2023-01-01T00:00:00Z"}
        material = lambda *args, **kwargs: {"status": "validated", "remote_operations": 1,
            "object_type": "commit", "tree_sha": "d" * 40, "deterministic_repeat": True}
        with tempfile.TemporaryDirectory() as directory:
            result = execute_case(Path(directory), row, self.audit[row["case_id"]],
                                  {"github_token": None, "timeout": 1, "transport_retries": 0},
                                  get=late, archive_loader=b2_archive,
                                  relationship_probe=probe, materializer=material)
        self.assertEqual(result["record"]["pr"]["existed_by_tFG"], "no")
        self.assertEqual(result["record"]["historical_state_reconstructible"], "yes")

    def test_materialization_failure_is_operational_unresolved(self):
        row = self.eligibility["CASE_97AFC2022473"]
        probe = lambda *args, **kwargs: {"status": "validated", "remote_operations": 1,
            "requested_sha": "a" * 40, "parent_sha": "b" * 40,
            "tree_sha": "c" * 40, "commit_time": "2023-01-01T00:00:00Z"}
        failed = lambda *args, **kwargs: {"status": "transport_failed", "remote_operations": 1,
            "object_type": "", "tree_sha": "", "deterministic_repeat": False}
        with tempfile.TemporaryDirectory() as directory:
            result = execute_case(Path(directory), row, self.audit[row["case_id"]],
                                  {"github_token": None, "timeout": 1, "transport_retries": 0},
                                  get=lambda *args: provider(row, created_at=self.audit[row["case_id"]]["pr_created_at"]), archive_loader=b2_archive,
                                  relationship_probe=probe, materializer=failed)
        self.assertEqual(result["record"]["historical_state_reconstructible"], "unresolved")
        self.assertEqual(result["record"]["operational_reason"], "transport_failed")

    def _root(self, directory: str) -> Path:
        root = Path(directory)
        for relative in ("cases/manifests/post_stage_c_reconstruction_pilot_v2.csv",
                         "cases/manifests/post_stage_c_eligibility.csv",
                         "cases/manifests/post_stage_c_historical_target_audit.csv",
                         "cases/manifests/stage_c_post_resolution_authority.csv"):
            target = root / relative; target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)
        for row in self.eligibility.values():
            source = ROOT / row["stage_c_authoritative_record"]
            target = root / row["stage_c_authoritative_record"]
            target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, target)
        return root

    def test_resume_marks_only_safely_persisted_cases_and_skips_completed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._root(directory)
            calls = []
            def fake_execute(root_, eligibility, audit, config, **deps):
                calls.append(eligibility["case_id"])
                paths = output_paths(eligibility["case_id"])
                for path in paths.values():
                    target = root_ / path; target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text("{}\n")
                if len(calls) == 2:
                    raise RuntimeError("controlled interruption")
                return {"case_id": eligibility["case_id"], "provider_requests": 0,
                        "git_operations": 0, "paths": paths}
            import developer_intent.post_stage_c_v2_live as live
            original = live.execute_case; live.execute_case = fake_execute
            try:
                with self.assertRaises(RuntimeError):
                    run_pilot(root, {"github_token": None, "timeout": 1, "transport_retries": 0})
            finally:
                live.execute_case = original
            rows = read_csv(root / "cases/manifests/post_stage_c_reconstruction_pilot_v2.csv")
            self.assertEqual(rows[0]["executed"], "true")
            self.assertEqual(rows[1]["executed"], "false")
            self.assertEqual(calls[:2], ["CASE_97AFC2022473", "CASE_F93FFAA22B9B"])

    def test_preflight_is_read_only_and_exact(self):
        rows, _, _ = preflight(ROOT)
        self.assertEqual(len(rows), 8)
        self.assertTrue(all(r["executed"] == "false" for r in rows))


if __name__ == "__main__":
    unittest.main()
