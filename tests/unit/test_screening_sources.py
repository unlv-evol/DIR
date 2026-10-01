"""Offline source, HTTP, and configuration checks for pilot screening."""

import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from developer_intent.screening_chatgpt import parse_share, retrieve_share, share_id
from developer_intent.screening_config import load_config
from developer_intent.screening_github import pr_identity, retrieve_pr
from developer_intent.screening_http import FetchResult, HttpClient


SHARE = "https://chatgpt.com/share/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
PR = "https://github.com/owner/repo/pull/7"


class FakeHttp:
    def __init__(self, answers):
        self.answers = answers
        self.calls = []
        self.cache_dir = Path(tempfile.gettempdir())

    def get(self, url, **kwargs):
        self.calls.append(url)
        return self.answers.get(url, FetchResult("not_found", note="HTTP 404"))


class ShareTests(unittest.TestCase):
    def payload(self, first_time=1704067200):
        return {"title": "Example", "current_node": "a2", "create_time": 1,
                "mapping": {
                    "root": {"parent": None, "message": None},
                    "u1": {"parent": "root", "message": {"author": {"role": "user"},
                           "content": {"parts": ["one two"]}, "create_time": first_time}},
                    "a2": {"parent": "u1", "message": {"author": {"role": "assistant"},
                           "content": {"parts": ["three four five"]}}}}}

    def test_ordered_turns_and_timestamp(self):
        parsed = parse_share(json.dumps(self.payload()).encode())
        self.assertEqual([t["role"] for t in parsed["turns"]], ["user", "assistant"])
        self.assertEqual(sum(t["role"] == "user" for t in parsed["turns"]), 1)
        self.assertEqual(sum(len(t["text"].split()) for t in parsed["turns"]), 5)
        self.assertEqual(parsed["precision"], "timestamp")
        self.assertEqual(parsed["tool_trace"], [])
        self.assertEqual(len(parsed["records"]), 3)
        self.assertIn("mapping", parsed["raw_conversation"])

    def test_date_only_and_missing_first_prompt_time(self):
        value = self.payload("2024-01-01")
        self.assertEqual(parse_share(json.dumps(value).encode())["precision"], "date")
        value = self.payload(None)
        parsed = parse_share(json.dumps(value).encode())
        self.assertEqual(parsed["start"], "")
        self.assertEqual(parsed["temporal_status"], "unresolved")

    def test_html_and_unsupported_page(self):
        html = '<script id="__NEXT_DATA__" type="application/json">' + json.dumps(self.payload()) + '</script>'
        self.assertEqual(parse_share(html.encode())["title"], "Example")
        with self.assertRaises(ValueError):
            parse_share(b"<html>visible text only</html>")

    def test_react_router_flattened_share_page(self):
        table = [{"_1": 2, "_3": 4}, "mapping", {"_5": 6}, "current_node", "node",
                 "node", {"_7": 8, "_9": 10}, "parent", None, "message",
                 {"_11": 12, "_13": 14, "_15": 16}, "author", {"_17": 18},
                 "content", {"_19": 20}, "create_time", "2024-01-01",
                 "role", "user", "parts", [21], "hello world"]
        html = "<script>window.__reactRouterContext.streamController.enqueue(" + json.dumps(json.dumps(table)) + ");</script>"
        parsed = parse_share(html.encode())
        self.assertEqual(parsed["turns"], [{"role": "user", "text": "hello world"}])
        self.assertEqual(parsed["precision"], "date")

    def test_tool_directed_assistant_messages_are_not_visible_turns(self):
        data = {"messages": [
            {"role": "user", "content": {"parts": ["find this"]}, "create_time": "2024-01-01"},
            {"role": "assistant", "recipient": "browser",
             "content": {"content_type": "code", "text": "search()"}},
            {"role": "tool", "content": {"content_type": "tool_result"}},
            {"role": "assistant", "recipient": "all", "content": {"parts": ["found it"]}},
            {"role": "assistant", "recipient": "all", "content": {"parts": ["here is more"]}},
        ]}
        parsed = parse_share(json.dumps(data).encode())
        self.assertEqual(parsed["turns"], [
            {"role": "user", "text": "find this"},
            {"role": "assistant", "text": "found it"},
            {"role": "assistant", "text": "here is more"},
        ])
        self.assertEqual(sum(len(t["text"].split()) for t in parsed["turns"]), 7)
        self.assertEqual([event["event_index"] for event in parsed["tool_trace"]], [1, 2])
        self.assertEqual(len(parsed["records"]), 5)
        self.assertEqual(parsed["tool_trace"][0]["record"]["message"]["recipient"], "browser")

    def test_multiple_tool_calls_and_failure_preserve_chronology(self):
        messages = [
            {"role": "user", "content": {"parts": ["User A"]}, "create_time": "2024-01-01"},
            {"role": "assistant", "recipient": "browser", "content": {"content_type": "code", "text": "first()"}},
            {"role": "tool", "content": {"content_type": "result", "text": "failure"}},
            {"role": "assistant", "recipient": "browser", "content": {"content_type": "code", "text": "retry()"}},
            {"role": "tool", "content": {"content_type": "result", "text": "success"}},
            {"role": "assistant", "recipient": "all", "content": {"parts": ["Assistant B"]}},
            {"role": "user", "content": {"parts": ["User C"]}},
        ]
        parsed = parse_share(json.dumps({"messages": messages}).encode())
        self.assertEqual([turn["text"] for turn in parsed["turns"]], ["User A", "Assistant B", "User C"])
        self.assertEqual([event["event_index"] for event in parsed["tool_trace"]], [1, 2, 3, 4])
        self.assertEqual(parsed["records"][2]["message"]["content"]["text"], "failure")
        self.assertEqual(len(parsed["raw_conversation"]["messages"]), 7)

    def test_mixed_visible_text_and_tool_part(self):
        messages = [
            {"role": "user", "content": {"parts": ["question"]}, "create_time": "2024-01-01"},
            {"role": "assistant", "recipient": "all", "content": {"parts": [
                "I will check", {"content_type": "tool_call", "recipient": "browser", "arguments": "search"},
                {"content_type": "text", "text": "and report back"}]}},
        ]
        parsed = parse_share(json.dumps({"messages": messages}).encode())
        self.assertEqual(parsed["turns"][1]["text"], "I will check\nand report back")
        self.assertEqual(sum(len(t["text"].split()) for t in parsed["turns"]), 7)
        self.assertEqual(parsed["tool_trace"][0]["event_index"], 1)
        self.assertEqual(parsed["tool_trace"][0]["part_index"], 1)
        self.assertEqual(parsed["tool_trace"][0]["part"]["recipient"], "browser")

    def test_pa30_shaped_tool_trace(self):
        messages = [
            None,
            {"role": "system", "content": {"parts": ["internal"]}},
            {"role": "user", "content": {"parts": ["request"]}, "create_time": "2024-01-01"},
        ]
        for index in range(6):
            messages.append({"role": "assistant", "recipient": "browser",
                             "content": {"content_type": "code", "text": f"search({index})"}})
            messages.append({"role": "tool", "content": {"content_type": "result", "text": f"result {index}"}})
        messages.extend({"role": "tool", "content": {"content_type": "result", "text": "quote"}}
                        for _ in range(3))
        messages.extend([
            {"role": "assistant", "recipient": "all", "content": {"parts": ["first answer"]}},
            {"role": "assistant", "recipient": "all", "content": {"parts": ["second answer"]}},
        ])
        parsed = parse_share(json.dumps({"messages": messages}).encode())
        self.assertEqual([turn["text"] for turn in parsed["turns"]],
                         ["request", "first answer", "second answer"])
        self.assertEqual(len(parsed["records"]), 20)
        self.assertEqual(len(parsed["tool_trace"]), 15)
        self.assertEqual(len(parsed["other_records"]), 2)
        self.assertEqual(sum(len(turn["text"].split()) for turn in parsed["turns"]), 5)

    def test_inaccessible_is_not_empty_conversation(self):
        http = FakeHttp({})
        result = retrieve_share(SHARE, http)
        self.assertFalse(result["complete"])
        self.assertEqual(result["retrieval_status"], "not_found")
        self.assertEqual(result["parsing_status"], "not_attempted")
        self.assertEqual(result["turns"], [])
        self.assertEqual(share_id(SHARE), "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

    def test_with_source_contract_on_success_and_no_body(self):
        canonical = SHARE
        successful_source = FetchResult(
            "retrieved_public", json.dumps(self.payload()).encode(), canonical, 200,
            retrieved_at="2024-01-02T00:00:00+00:00", content_type="application/json")
        result_only = retrieve_share(SHARE, FakeHttp({canonical: successful_source}))
        self.assertIsInstance(result_only, dict)
        result, source = retrieve_share(
            SHARE, FakeHttp({canonical: successful_source}), with_source=True)
        self.assertEqual(result["parsing_status"], "parsed")
        self.assertIs(source, successful_source)

        failure = FetchResult("network_failure", note="URLError")
        result_only = retrieve_share(SHARE, FakeHttp({canonical: failure}))
        self.assertIsInstance(result_only, dict)
        self.assertEqual(result_only["retrieval_status"], "network_failure")
        self.assertEqual(result_only["notes"], "URLError")
        result, source = retrieve_share(
            SHARE, FakeHttp({canonical: failure}), with_source=True)
        self.assertEqual(result["retrieval_status"], "network_failure")
        self.assertEqual(result["notes"], "URLError")
        self.assertIsNone(source)


class GitHubTests(unittest.TestCase):
    def pr_payload(self):
        return {"html_url": PR, "number": 7, "state": "closed", "created_at": "2024-01-01T00:00:00Z",
                "closed_at": None, "merged_at": None, "additions": 3, "deletions": 2,
                "changed_files": 1, "commits": 11, "user": {"login": "author"},
                "base": {"ref": "main", "sha": "base"}, "head": {"ref": "topic", "sha": "head"}}

    def test_success_and_measurements(self):
        base = "https://api.github.com/repos/owner/repo/pulls/7"
        http = FakeHttp({base: FetchResult("retrieved_public", json.dumps(self.pr_payload()).encode()),
                         base + "/files?per_page=100&page=1": FetchResult(
                             "retrieved_public", json.dumps([{"filename": "a.py", "additions": 3, "deletions": 2}]).encode())})
        result = retrieve_pr(PR, http)
        self.assertEqual(pr_identity(PR), ("owner", "repo", 7))
        self.assertEqual(result["retrieval_status"], "retrieved_public")
        self.assertEqual(result["pr"]["commits"], 11)
        self.assertEqual(result["pr"]["changed_files"], 1)
        self.assertEqual(sum(f["additions"] + f["deletions"] for f in result["files"]), 5)

    def test_failures_and_malformed(self):
        base = "https://api.github.com/repos/owner/repo/pulls/7"
        for status in ("not_found", "forbidden", "authentication_required", "rate_limited"):
            self.assertEqual(retrieve_pr(PR, FakeHttp({base: FetchResult(status)}))["retrieval_status"], status)
        self.assertEqual(retrieve_pr(PR, FakeHttp({base: FetchResult("retrieved_public", b"[]")}))
                         ["retrieval_status"], "malformed_response")

    def test_verified_repository_rename_and_unverified_mismatch(self):
        base = "https://api.github.com/repos/owner/repo/pulls/7"
        file_url = base + "/files?per_page=100&page=1"
        payload = self.pr_payload()
        payload["html_url"] = "https://github.com/new-owner/new-repo/pull/7"
        payload["base"]["repo"] = {"id": 123, "full_name": "new-owner/new-repo"}
        final_url = "https://api.github.com/repositories/123/pulls/7"
        files = FetchResult("retrieved_public", b'[{"filename":"a.py","additions":3,"deletions":2}]')
        http = FakeHttp({base: FetchResult("retrieved_public", json.dumps(payload).encode(), final_url),
                         file_url: files})
        result = retrieve_pr(PR, http)
        self.assertEqual(result["retrieval_status"], "retrieved_public")
        self.assertEqual(result["pr"]["source_url"], PR)
        self.assertEqual(result["pr"]["canonical_url"], payload["html_url"])
        self.assertTrue(result["pr"]["redirect_verified"])
        for bad_url in ("", "https://api.github.com/repositories/999/pulls/7",
                        "https://api.github.com/repositories/123/pulls/8"):
            bad = FakeHttp({base: FetchResult("retrieved_public", json.dumps(payload).encode(), bad_url)})
            self.assertEqual(retrieve_pr(PR, bad)["retrieval_status"], "malformed_response")


class HttpAndConfigTests(unittest.TestCase):
    def test_http_cache_and_token_only_in_request(self):
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): return None
            def read(self): return b'{"ok":true}'
            def geturl(self): return "https://api.github.com/test"

        calls = []
        def open_request(request, timeout):
            calls.append(request.get_header("Authorization"))
            return Response()

        with tempfile.TemporaryDirectory() as directory:
            client = HttpClient(Path(directory), opener=open_request)
            first = client.get("https://api.github.com/test", token="secret")
            second = client.get("https://api.github.com/test", token="secret")
            self.assertEqual(first.status, "retrieved_authenticated")
            self.assertTrue(second.from_cache)
            self.assertEqual(calls, ["Bearer secret"])
            for path in Path(directory).iterdir():
                self.assertNotIn("secret", path.read_text())

    def test_http_statuses_and_retry(self):
        for code, headers, status in ((404, {}, "not_found"), (403, {}, "forbidden"),
                                      (401, {}, "authentication_required"),
                                      (403, {"X-RateLimit-Remaining": "0"}, "rate_limited")):
            calls = []
            def failing(request, timeout):
                calls.append(1)
                raise HTTPError(request.full_url, code, "failure", headers, io.BytesIO())
            with tempfile.TemporaryDirectory() as directory:
                result = HttpClient(Path(directory), retries=1, sleep=lambda _: None,
                                    opener=failing).get("https://github.com/test")
            self.assertEqual(result.status, status)
            self.assertEqual(len(calls), 2 if status == "rate_limited" else 1)

    def test_config_precedence_defaults_and_redaction(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".env").write_text("GITHUB_TOKEN=secret\nDIR_HTTP_TIMEOUT=15\n")
            config = load_config(root, environ={"DIR_HTTP_TIMEOUT": "20"})
            self.assertEqual(config.timeout, 20)
            self.assertEqual(config.retries, 3)
            self.assertEqual(config.github_token, "secret")
            self.assertNotIn("secret", config.safe_report())
            self.assertIsNone(load_config(root, env_file=root / "missing", environ={}).github_token)


if __name__ == "__main__":
    unittest.main()
