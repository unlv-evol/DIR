"""Offline tests for the historical PatchTrack sharing fallback."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from developer_intent.screening_archive import archive_fallback


SHARE = "https://chat.openai.com/share/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
PR = "https://github.com/owner/repo/pull/7"


def row(sid="PA-1", pr=PR):
    return {"Case ID": sid, "PR_Link": pr, "Conversation_Link": SHARE}


def sharing(html=True, answer="response"):
    conversation = {"current_node": "a", "mapping": {
        "u": {"parent": None, "message": {"author": {"role": "user"},
              "create_time": 1704067200, "content": {"parts": ["request"]}}},
        "a": {"parent": "u", "message": {"author": {"role": "assistant"},
              "content": {"parts": [answer]}}}}}
    page = (f"<!-- {SHARE} --><script id=\"__NEXT_DATA__\">"
            + json.dumps(conversation) + "</script>") if html else ""
    return {"URL": SHARE, "Status": 200, "DateOfConversation": None,
            "Conversations": [{"Prompt": "request", "Answer": answer}], "HTMLContent": page}


class ArchiveTests(unittest.TestCase):
    def write_archive(self, directory, members):
        path = Path(directory) / "historical.zip"
        with ZipFile(path, "w") as bundle:
            for name, sources in members.items():
                bundle.writestr(name, json.dumps({"Sources": sources}))
        return path

    def test_recovery_requires_pr_and_share_and_preserves_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            source = {"URL": PR, "ChatgptSharing": [sharing()]}
            archive = self.write_archive(directory, {"early.json": [source], "later.json": [source]})
            results = archive_fallback(archive, [row(), row("PA-2", "https://github.com/other/repo/pull/7")])
        recovered = results["PA-1"]
        self.assertEqual(recovered["status"], "recovered")
        self.assertEqual(recovered["conversation"]["start"], "2024-01-01T00:00:00+00:00")
        self.assertEqual([turn["text"] for turn in recovered["conversation"]["turns"]],
                         ["request", "response"])
        self.assertEqual(len(recovered["matching_members"]), 2)
        self.assertIn("archive_sha256", recovered["conversation"]["archive_provenance"])
        self.assertEqual(results["PA-2"]["status"], "pr_mismatch")

    def test_summary_only_stays_unresolved(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = self.write_archive(directory, {"manual.json": [
                {"URL": PR, "ChatgptSharing": [sharing(html=False)]}]})
            result = archive_fallback(archive, [row()])["PA-1"]
        self.assertEqual(result["status"], "summary_only_unresolved")
        self.assertEqual(result["leads"][0]["turns"][0], {"role": "user", "text": "request"})
        self.assertNotIn("conversation", result)

    def test_conflicting_html_snapshots_are_not_selected(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = self.write_archive(directory, {
                "early.json": [{"URL": PR, "ChatgptSharing": [sharing(answer="first")]}],
                "later.json": [{"URL": PR, "ChatgptSharing": [sharing(answer="different")]}],
            })
            result = archive_fallback(archive, [row()])["PA-1"]
        self.assertEqual(result["status"], "conflicting_snapshots")
        self.assertNotIn("conversation", result)


if __name__ == "__main__":
    unittest.main()
