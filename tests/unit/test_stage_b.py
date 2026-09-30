"""Offline Stage B retriever integration, persistence, and isolation."""

import base64
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "pipeline/extraction"))

from developer_intent.screening import SCREENING_SCHEMA_VERSION, case_id  # noqa: E402
from developer_intent.screening_http import FetchResult, HttpClient  # noqa: E402
from developer_intent.stage_b import (check_new_outputs, output_paths,  # noqa: E402
                                      persist_stage_b, prepare_stage_b,
                                      select_linkage)

SHARE_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
SHARE = "https://chatgpt.com/share/" + SHARE_ID
CANONICAL = SHARE
PR = "https://github.com/owner/repo/pull/7"


def source_row():
    return {"Case ID": "PA-1", "Outcome_Class": "PA", "PR_Link": PR,
            "Conversation_Link": SHARE}


def body():
    messages = [
        {"role": "user", "create_time": "2024-01-01", "content": {"parts": ["do work"]}},
        {"role": "assistant", "recipient": "browser", "content": {"content_type": "code", "text": "search"}},
        {"role": "tool", "content": {"content_type": "result", "text": "source result"}},
        {"role": "assistant", "create_time": "2024-01-02T00:00:00Z",
         "content": {"parts": ["```python\nprint(1)\n```"]}},
        {"role": "user", "content": {"parts": ["later turn"]}},
    ]
    return json.dumps({"messages": messages}).encode()


class MockHttp:
    def __init__(self, cache_dir, answer):
        self.cache_dir = cache_dir
        self.answer = answer
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append(url)
        return self.answer


class StageBTests(unittest.TestCase):
    def linkage(self):
        return select_linkage([source_row()], case_id("PA-1"))

    def screened(self, **changes):
        row = {"screening_schema_version": SCREENING_SCHEMA_VERSION,
               "methodology_version": "dir-tfg-v2",
               "case_id": case_id("PA-1"), "source_case_id": "PA-1",
               "Outcome_Class": "PA", "pr_url": PR, "conversation_url": SHARE,
               "canonical_pr_url": PR,
               "eligibility_status": "pending_resolution", "exclusion_reason": "",
               "pending_reason": ("first_generation_boundary_identifiable_unresolved;"
                                  "historical_state_reconstructible_unresolved"),
               "source_linkage_status": "established", "pr_conversation_match": "yes",
               "conversation_available": "yes", "temporal_anchor_available": "yes",
               "duplicate_status": "unique", "project_history_accessible": "yes",
               "case_integrity_status": "ok",
               "first_generation_boundary_identifiable": "unresolved",
               "historical_state_reconstructible": "unresolved",
               "stage_b_readiness_status": "ready_for_stage_b",
               "stage_b_readiness_reason": "pending_only_stage_c_tfg_deferred"}
        row.update(changes)
        return row

    def test_production_stage_b_accepts_only_explicitly_ready_pending_status(self):
        pending = self.screened()
        linkage = select_linkage([source_row()], case_id("PA-1"), [pending])
        self.assertEqual(linkage["linkage_version"], "case-linkage-v2")
        self.assertEqual(linkage["stage_a_eligibility_status"], "pending_resolution")
        self.assertEqual(linkage["stage_b_readiness_status"], "ready_for_stage_b")
        self.assertEqual(linkage["canonical_pr_url"], PR)
        self.assertEqual(linkage["source_linkage_status"], "established")
        self.assertEqual(linkage["pr_conversation_match"], "yes")
        self.assertEqual(
            linkage["stage_a_screening_record_ref"],
            f"cases/manifests/screened_PA_PN_cases.csv#case_id={case_id('PA-1')}")
        self.assertEqual(
            linkage["correspondence_review_ref"],
            f"cases/manifests/correspondence_reviews/{case_id('PA-1')}.json")
        eligible = self.screened(eligibility_status="eligible", pending_reason="",
                                 first_generation_boundary_identifiable="yes",
                                 historical_state_reconstructible="yes",
                                 stage_b_readiness_reason="scientifically_eligible")
        linkage = select_linkage([source_row()], case_id("PA-1"), [eligible])
        self.assertEqual(linkage["stage_a_eligibility_status"], "eligible")
        arbitrary = self.screened(pending_reason="project_history_accessible_unresolved",
                                  project_history_accessible="unresolved")
        with self.assertRaisesRegex(ValueError, "inconsistent"):
            select_linkage([source_row()], case_id("PA-1"), [arbitrary])
        unresolved_correspondence = self.screened(
            pending_reason="pr_conversation_match_unresolved",
            pr_conversation_match="unresolved")
        with self.assertRaisesRegex(ValueError, "inconsistent"):
            select_linkage([source_row()], case_id("PA-1"),
                           [unresolved_correspondence])
        excluded_ready = self.screened(eligibility_status="excluded",
                                       exclusion_reason="duplicate_case")
        with self.assertRaisesRegex(ValueError, "inconsistent"):
            select_linkage([source_row()], case_id("PA-1"), [excluded_ready])

    def test_explicit_case_selection_and_fresh_persistence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            linkage = self.linkage()
            self.assertEqual(output_paths(root, linkage["case_id"])["linkage"],
                             root / "cases/manifests/linkage" / f"{linkage['case_id']}.json")
            source = FetchResult("retrieved_public", body(), CANONICAL, 200,
                                 retrieved_at="2024-01-03T00:00:00+00:00",
                                 content_type="application/json")
            http = MockHttp(root / "cache", source)
            prepared = prepare_stage_b(linkage, http)
            self.assertEqual(http.calls, [CANONICAL])
            self.assertEqual(prepared["status"]["stage_b_status"], "complete")
            paths = persist_stage_b(root, prepared)
            self.assertEqual(set(paths), {"linkage", "source_archive", "normalized",
                                          "model_view", "status"})
            archive = json.loads(paths["source_archive"].read_text())
            normalized = json.loads(paths["normalized"].read_text())
            model = json.loads(paths["model_view"].read_text())
            self.assertEqual(base64.b64decode(archive["source_payload_base64"]), body())
            self.assertEqual(archive["retrieved_at"], source.retrieved_at)
            self.assertEqual(archive["source_url"], SHARE)
            self.assertEqual(archive["final_url"], CANONICAL)
            self.assertEqual(archive["content_type"], "application/json")
            self.assertEqual(archive["source_origin"], "fresh")
            self.assertEqual([t["event_index"] for t in normalized["visible_turns"]],
                             [0, 3, 4])
            self.assertEqual(len(normalized["records"]), 5)
            self.assertEqual(normalized["records"][3]["message"]["content"]["parts"][0],
                             "```python\nprint(1)\n```")
            self.assertEqual(normalized["visible_turns"][-1]["text"], "later turn")
            self.assertEqual(normalized["artifact_candidates"][0]["source_record_index"], 3)
            self.assertEqual(model["case_id"], linkage["case_id"])
            self.assertEqual(model["start"], "2024-01-01")
            self.assertEqual(model["precision"], "date")
            self.assertFalse(any("tfg" in key.lower() or "first_generation" in key.lower()
                                 for key in model))
            self.assertEqual(prepared["status"]["stage_a_eligibility_status"],
                             linkage["stage_a_eligibility_status"])
            self.assertNotIn(PR, paths["model_view"].read_text())
            self.assertNotIn("owner/repo", paths["model_view"].read_text())
            self.assertNotIn('"Outcome_Class"', paths["model_view"].read_text())
            self.assertEqual(json.loads(paths["status"].read_text())["stage_b_status"],
                             "complete")
            with self.assertRaises(FileExistsError):
                check_new_outputs(paths)
            with self.assertRaises(FileExistsError):
                persist_stage_b(root, prepared)

    def test_cached_response_without_old_timestamp_is_not_backdated(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cached = FetchResult("retrieved_public", body(), CANONICAL, 200,
                                 from_cache=True, content_type="application/json")
            prepared = prepare_stage_b(self.linkage(), MockHttp(root / "cache", cached))
            self.assertEqual(prepared["status"]["stage_b_status"], "complete")
            self.assertEqual(prepared["archive"]["retrieved_at"], "")
            self.assertEqual(prepared["archive"]["retrieval_time_status"],
                             "unknown_legacy_cache")
            self.assertEqual(prepared["archive"]["source_origin"], "cached")

    def test_normalization_failure_preserves_archive_without_complete_view(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = FetchResult("retrieved_public", b"<html>unsupported</html>",
                                 CANONICAL, 200, retrieved_at="2024-01-03T00:00:00Z")
            prepared = prepare_stage_b(self.linkage(), MockHttp(root / "cache", source))
            self.assertEqual(prepared["status"]["stage_b_status"], "normalization_failed")
            paths = persist_stage_b(root, prepared)
            self.assertTrue(paths["source_archive"].exists())
            self.assertFalse(paths["normalized"].exists())
            self.assertFalse(paths["model_view"].exists())
            self.assertNotEqual(json.loads(paths["status"].read_text())["stage_b_status"],
                                "complete")

    def test_project_identity_in_conversation_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = body().replace(b"do work", PR.encode())
            source = FetchResult("retrieved_public", payload, CANONICAL, 200,
                                 retrieved_at="2024-01-03T00:00:00Z")
            prepared = prepare_stage_b(self.linkage(), MockHttp(root / "cache", source))
            self.assertEqual(prepared["status"]["stage_b_status"], "validation_failed")
            paths = persist_stage_b(root, prepared)
            self.assertTrue(paths["source_archive"].exists())
            self.assertTrue(paths["normalized"].exists())
            self.assertFalse(paths["model_view"].exists())

    def test_http_client_records_fresh_time_and_preserves_it_in_cache(self):
        class Response:
            status = 200
            headers = {"Content-Type": "application/json", "Set-Cookie": "private"}
            def __enter__(self): return self
            def __exit__(self, *args): return None
            def read(self): return body()
            def geturl(self): return CANONICAL

        with tempfile.TemporaryDirectory() as directory:
            client = HttpClient(Path(directory), opener=lambda request, timeout: Response())
            first = client.get(CANONICAL, token="secret")
            second = client.get(CANONICAL, token="secret")
            self.assertTrue(first.retrieved_at)
            self.assertEqual(second.retrieved_at, first.retrieved_at)
            self.assertTrue(second.from_cache)
            for path in Path(directory).iterdir():
                self.assertNotIn("secret", path.read_text())
                self.assertNotIn("private", path.read_text())

    def test_old_http_cache_metadata_keeps_unknown_retrieval_time(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            key = hashlib.sha256((CANONICAL + "|public").encode()).hexdigest()
            (root / f"{key}.body").write_bytes(body())
            (root / f"{key}.json").write_text(json.dumps({
                "status": "retrieved_public", "final_url": CANONICAL,
                "http_status": 200}))
            fetch = HttpClient(root, opener=lambda *args, **kwargs: self.fail(
                "Old cache entry should not trigger a request")).get(CANONICAL)
            self.assertTrue(fetch.from_cache)
            self.assertEqual(fetch.retrieved_at, "")


if __name__ == "__main__":
    unittest.main()
