"""Restricted Stage A correspondence evidence packet tests."""

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from developer_intent.correspondence_evidence import (  # noqa: E402
    DOWNSTREAM_USE, EVIDENCE_POLICY, FORBIDDEN_KEYS, prepare_review_evidence)
from developer_intent.correspondence_workflow import (  # noqa: E402
    REVIEW_CSV_FIELDS, import_review_csv, review_rows)
from developer_intent.screening import screen_rows  # noqa: E402
from developer_intent.stage_a_contracts import validate_correspondence_evidence  # noqa: E402

PR = "https://github.com/acme/repo/pull/1"
SHARE = "https://chatgpt.com/share/b7853f70-84b8-477b-9879-a93a51215f81"


def source():
    return {"Case ID": "PA-1", "Outcome_Class": "PA", "PR_Link": PR,
            "Conversation_Link": SHARE, "Context": "1", "Specificity": "2",
            "Verification": "0"}


def evidence():
    return {
        "pr": {"html_url": PR, "number": 1, "base_sha": "a" * 40},
        "files": [],
        "conversation": {"url": SHARE, "start": "2024-01-01", "precision": "date",
                         "complete": True,
                         "turns": [{"role": "user", "text": "convert request URL"},
                                   {"role": "assistant", "text": "secret answer"}]},
        "history_access": {"judgment": "yes", "mechanism": "git_fetch_commit_object",
                           "repository": "acme/repo", "object": "a" * 40,
                           "status": "commit_object_retrieved", "source": "PR base_sha",
                           "reason": ""},
        "processability": {"source": "fixture", "conversation_available": "yes",
                           "first_generation_boundary_identifiable": "yes",
                           "project_history_accessible": "yes",
                           "historical_state_reconstructible": "yes"},
    }


def completed(row):
    row = dict(row)
    row.update({
        "pr_conversation_match": "yes",
        "pr_conversation_match_source": "restricted_stage_a_manual_review",
        "pr_conversation_match_reviewer": "reviewer-1",
        "pr_conversation_match_timestamp": "2026-09-29T00:00:00Z",
        "pr_conversation_match_version": "review-v1",
        "pr_conversation_match_evidence_ref": row["permitted_evidence_ref"],
        "pr_conversation_match_reason": "Exact share reference and matching task context",
    })
    return row


class CorrespondenceEvidenceTests(unittest.TestCase):
    def prepare(self, root: Path):
        evidence_dir = root / "evidence"
        evidence_dir.mkdir()
        (evidence_dir / "PA-1.json").write_text(json.dumps(evidence()))
        automated = screen_rows([source()], evidence_dir)
        review = root / "review.csv"
        with review.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=REVIEW_CSV_FIELDS,
                                    lineterminator="\n")
            writer.writeheader()
            writer.writerow(completed(review_rows(automated)[0]))
        archive = root / "archive"
        archive.mkdir()
        payload = [{
            "Type": "pull request", "URL": PR, "State": "MERGED",
            "Additions": 10, "ChatgptSharing": [{
                "URL": SHARE, "DateOfAccess": "2024-01-02 00:00:00",
                "Mention": {"MentionedURL": PR + "#discussion_r1",
                            "MentionedProperty": "reviews.body",
                            "MentionedAuthor": "developer",
                            "MentionedText": SHARE + " task context",
                            "MentionedPath": "src/request.ts"},
                "Conversations": [{"Prompt": "convert request URL",
                                   "Answer": "prohibited answer"}],
            }],
        }]
        (archive / "snapshot.json").write_text(json.dumps(payload))
        packets = root / "cases/manifests/correspondence_evidence"
        ready = root / "ready.csv"
        counts = prepare_review_evidence(review, [source()], archive, evidence_dir,
                                         packets, ready, root)
        return automated, packets, ready, counts

    def test_packet_is_restricted_and_importable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            automated, packets, ready, counts = self.prepare(root)
            self.assertEqual(counts, {"archive_exact_pair": 1})
            packet = json.loads(next(packets.glob("*.json")).read_text())
            validate_correspondence_evidence(packet)
            self.assertEqual(packet["policy"], EVIDENCE_POLICY)
            self.assertEqual(packet["downstream_use"], DOWNSTREAM_USE)
            self.assertEqual(packet["conversation_reference"]["developer_task_excerpts"],
                             ["convert request URL"])
            serialized = json.dumps(packet)
            self.assertNotIn("secret answer", serialized)
            self.assertNotIn("prohibited answer", serialized)
            self.assertFalse(FORBIDDEN_KEYS & set(packet))
            result = import_review_csv(ready, automated, [source()], root / "reviews", root)
            self.assertEqual(result["imported"], 1)
            canonical = json.loads(next((root / "reviews").glob("*.json")).read_text())
            changed_evidence = evidence()
            changed_evidence["correspondence_review"] = canonical
            (root / "evidence/PA-1.json").write_text(json.dumps(changed_evidence))
            screened_after_review = screen_rows([source()], root / "evidence")
            repeated = import_review_csv(ready, screened_after_review, [source()],
                                         root / "reviews", root)
            self.assertEqual(repeated["unchanged"], 1)

    def test_tampered_packet_fails_import(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            automated, packets, ready, _ = self.prepare(root)
            packet_path = next(packets.glob("*.json"))
            packet_path.write_text(packet_path.read_text() + " ")
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                import_review_csv(ready, automated, [source()], root / "reviews", root)

    def test_reviewer_attestation_is_not_upgraded_to_archive_support(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence_dir = root / "evidence"
            evidence_dir.mkdir()
            (evidence_dir / "PA-1.json").write_text(json.dumps(evidence()))
            automated = screen_rows([source()], evidence_dir)
            review = root / "review.csv"
            with review.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=REVIEW_CSV_FIELDS,
                                        lineterminator="\n")
                writer.writeheader()
                writer.writerow(completed(review_rows(automated)[0]))
            archive = root / "archive"
            archive.mkdir()
            packets = root / "cases/manifests/correspondence_evidence"
            counts = prepare_review_evidence(
                review, [source()], archive, evidence_dir, packets, root / "ready.csv", root)
            self.assertEqual(counts, {"reviewer_attestation_only": 1})
            packet = json.loads(next(packets.glob("*.json")).read_text())
            self.assertEqual(packet["archive_provenance"]["record_status"], "unavailable")


if __name__ == "__main__":
    unittest.main()
