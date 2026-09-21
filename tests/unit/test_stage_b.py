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

from developer_intent.screening import case_id  # noqa: E402
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

    def test_explicit_case_selection_and_fresh_persistence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            linkage = self.linkage()
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
