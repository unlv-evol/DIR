"""Offline Stage B retriever integration, persistence, and isolation."""

import base64
import csv
import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "pipeline/extraction"))

from developer_intent.screening import SCREENING_SCHEMA_VERSION, case_id  # noqa: E402
from developer_intent.screening_http import FetchResult, HttpClient  # noqa: E402
from developer_intent.stage_b import (check_new_outputs, output_paths,  # noqa: E402
                                      canonical_json_hash, existing_package_status,
                                      legacy_cache_paths,
                                      persist_stage_b, prepare_stage_b,
                                      prepare_stage_b_from_archived_http,
                                      prepare_stage_b_from_legacy,
                                      select_archived_http_response,
                                      semantic_model_hash,
                                      select_linkage)
from developer_intent.stage_b_corpus import (materialize_offline, run_offline_corpus,
                                             write_summary)  # noqa: E402

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


def next_data_body(payload=None):
    value = json.loads(payload or body())
    return ("<html><script id=\"__NEXT_DATA__\" type=\"application/json\">"
            + json.dumps(value) + "</script></html>")


def archive_document(*, pr=PR, share=SHARE, status=200, html=None,
                     conversations=None, access="2023-01-02 03:04:05"):
    sharing = {"URL": share, "Status": status,
               "DateOfAccess": access, "DateOfConversation": "January 1, 2023",
               "Conversations": [] if conversations is None else conversations}
    if html is not None:
        sharing["HTMLContent"] = html
    return {"Sources": [{"URL": pr, "ChatgptSharing": [sharing]}]}


def write_archive(path, members):
    with zipfile.ZipFile(path, "w") as bundle:
        for name, value in members:
            bundle.writestr(name, json.dumps(value))


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

    def test_no_body_retrieval_is_an_explicit_failure_not_an_unpacking_error(self):
        failure = FetchResult("not_found", note="HTTP 404")
        prepared = prepare_stage_b(
            self.linkage(), MockHttp(Path(tempfile.gettempdir()), failure))
        self.assertEqual(prepared["status"]["stage_b_status"], "retrieval_failed")
        self.assertEqual(prepared["status"]["retrieval_status"], "not_found")
        self.assertEqual(prepared["status"]["parsing_status"], "not_attempted")
        self.assertIsNone(prepared["archive"])
        self.assertIsNone(prepared["normalized"])
        self.assertIsNone(prepared["model_view"])

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

    def test_source_authored_administrative_strings_remain_conversation_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            values = ("owner/repo", PR, "https://github.com/owner/repo")
            for index, value in enumerate(values):
                with self.subTest(value=value):
                    payload = body().replace(b"do work", value.encode()).replace(
                        b"print(1)", b"print(1) # " + value.encode())
                    source = FetchResult("retrieved_public", payload, CANONICAL, 200,
                                         retrieved_at="2024-01-03T00:00:00Z")
                    prepared = prepare_stage_b(self.linkage(), MockHttp(root / "cache", source))
                    self.assertEqual(prepared["status"]["stage_b_status"], "complete")
                    self.assertEqual(prepared["model_view"]["visible_turns"][0]["text"], value)
                    self.assertIn(value, prepared["model_view"]["visible_turns"][1]["text"])

    def test_structural_administrative_injection_and_text_mutation_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            source = FetchResult("retrieved_public", body(), CANONICAL, 200,
                                 retrieved_at="2024-01-03T00:00:00Z")
            prepared = prepare_stage_b(self.linkage(), MockHttp(Path(directory), source))
            for key, value in (("repository", "owner/repo"), ("pr_url", PR),
                               ("Outcome_Class", "PA"), ("source_id", "PA-1")):
                altered = json.loads(json.dumps(prepared["model_view"]))
                altered[key] = value
                with self.subTest(key=key), self.assertRaises(ValueError):
                    from developer_intent.stage_b import validate_complete_package
                    validate_complete_package(prepared["linkage"], prepared["archive"],
                                              prepared["normalized"], altered)
            altered = json.loads(json.dumps(prepared["model_view"]))
            altered["visible_turns"][0]["text"] += " owner/repo"
            with self.assertRaises(ValueError):
                from developer_intent.stage_b import validate_complete_package
                validate_complete_package(prepared["linkage"], prepared["archive"],
                                          prepared["normalized"], altered)

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

    def write_legacy(self, root, *, payload=None, metadata=None):
        body_path, metadata_path, _ = legacy_cache_paths(root, SHARE)
        body_path.write_bytes(body() if payload is None else payload)
        metadata_path.write_text(json.dumps(metadata or {
            "status": "retrieved_public", "final_url": CANONICAL, "http_status": 200}))
        return body_path, metadata_path

    def test_legacy_import_records_v2_provenance_and_current_parser_output(self):
        with tempfile.TemporaryDirectory() as directory:
            legacy = Path(directory) / "legacy"; legacy.mkdir()
            body_path, metadata_path = self.write_legacy(legacy)
            prepared = prepare_stage_b_from_legacy(
                self.linkage(), legacy, imported_at="2026-09-30T12:00:00+00:00")
            archive = prepared["archive"]
            self.assertEqual(archive["archive_version"], "chatgpt-source-v2")
            self.assertEqual(archive["source_origin"], "legacy_cache_import")
            self.assertIsNone(archive["retrieved_at"])
            self.assertEqual(archive["retrieval_time_status"], "unknown_legacy_cache")
            self.assertEqual(archive["legacy_import"]["imported_at"],
                             "2026-09-30T12:00:00+00:00")
            self.assertEqual(archive["legacy_import"]["raw_body_sha256"],
                             hashlib.sha256(body()).hexdigest())
            self.assertEqual(archive["legacy_import"]["legacy_body_path"],
                             body_path.as_posix())
            self.assertEqual(archive["legacy_import"]["legacy_metadata_path"],
                             metadata_path.as_posix())
            self.assertEqual(prepared["status"]["stage_b_status"], "complete")
            self.assertEqual(len(prepared["model_view"]["artifact_candidates"]), 1)

    def test_legacy_import_rejects_missing_raw_or_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            legacy = Path(directory)
            with self.assertRaisesRegex(ValueError, "body is missing"):
                prepare_stage_b_from_legacy(self.linkage(), legacy)
            body_path, _, _ = legacy_cache_paths(legacy, SHARE); body_path.write_bytes(body())
            with self.assertRaisesRegex(ValueError, "metadata is missing"):
                prepare_stage_b_from_legacy(self.linkage(), legacy)

    def test_legacy_import_rejects_bad_metadata_identity_and_body(self):
        variants = [
            ({"status": "forbidden", "final_url": CANONICAL, "http_status": 200}, "status"),
            ({"status": "retrieved_public", "final_url": CANONICAL, "http_status": 404}, "HTTP"),
            ({"status": "retrieved_public", "final_url":
              "https://chatgpt.com/share/bbbbbbbb-cccc-dddd-eeee-ffffffffffff",
              "http_status": 200}, "identity"),
        ]
        for metadata, message in variants:
            with self.subTest(message=message), tempfile.TemporaryDirectory() as directory:
                legacy = Path(directory); self.write_legacy(legacy, metadata=metadata)
                with self.assertRaisesRegex(ValueError, message):
                    prepare_stage_b_from_legacy(self.linkage(), legacy)
        with tempfile.TemporaryDirectory() as directory:
            legacy = Path(directory); self.write_legacy(legacy, payload=b"not a conversation")
            with self.assertRaisesRegex(ValueError, "malformed"):
                prepare_stage_b_from_legacy(self.linkage(), legacy)

    def test_legacy_import_rejects_incomplete_parser_result_and_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            legacy = Path(directory); self.write_legacy(legacy)
            with patch("developer_intent.stage_b.parse_share",
                       return_value={"complete": False, "records": []}):
                with self.assertRaisesRegex(ValueError, "incomplete"):
                    prepare_stage_b_from_legacy(self.linkage(), legacy)
            with self.assertRaisesRegex(ValueError, "equivalence hash mismatch"):
                prepare_stage_b_from_legacy(self.linkage(), legacy,
                                            expected_model_view_sha256="0" * 64)

    def test_legacy_import_persists_standard_artifacts_and_preserves_valid_package(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); legacy=root/"legacy"; legacy.mkdir(); self.write_legacy(legacy)
            prepared=prepare_stage_b_from_legacy(self.linkage(), legacy)
            paths=persist_stage_b(root, prepared)
            self.assertTrue(all(path.exists() for path in paths.values()))
            self.assertEqual(existing_package_status(root, self.linkage()["case_id"]),
                             "existing_valid")
            row=materialize_offline(root, self.linkage(), root/"current", legacy)
            self.assertEqual(row["stage_b_package_status"], "existing_valid")

    def test_archived_http_selects_earliest_valid_with_deterministic_tie_break(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "archive.zip"
            invalid = archive_document(status=404, html=next_data_body())
            first = archive_document(html=next_data_body())
            # A second exact match at the same timestamp exercises source-index ordering.
            first["Sources"].append(first["Sources"][0].copy())
            later = archive_document(html=next_data_body())
            write_archive(archive, [
                ("20230101_000000_pr_sharings.json", invalid),
                ("20230102_000000_pr_sharings.json", first),
                ("20230103_000000_pr_sharings.json", later),
            ])
            selected = select_archived_http_response(self.linkage(), archive)
            self.assertEqual(selected["selected"]["archive_member"],
                             "20230102_000000_pr_sharings.json")
            self.assertEqual(selected["selected"]["source_index"], 0)
            self.assertEqual(len(selected["qualifying_candidates"]), 3)
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                select_archived_http_response(
                    self.linkage(), archive, expected_archive_sha256="0" * 64)

    def test_archived_http_requires_identity_status_html_and_current_parser(self):
        wrong_share = "https://chatgpt.com/share/bbbbbbbb-cccc-dddd-eeee-ffffffffffff"
        variants = [
            (archive_document(pr="https://github.com/other/repo/pull/7",
                              html=next_data_body()), "PR"),
            (archive_document(share=wrong_share, html=next_data_body()), "share"),
            (archive_document(status=404, html=next_data_body()), "status"),
            (archive_document(), "missing HTMLContent"),
            (archive_document(html="", conversations=[{"Prompt": "x", "Answer": "y"}]),
             "Conversations cannot substitute"),
        ]
        for document, label in variants:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                archive = Path(directory) / "archive.zip"
                write_archive(archive, [("20230101_000000_pr_sharings.json", document)])
                # A nearby screening-evidence object is intentionally ignored.
                (Path(directory) / "evidence.json").write_text(json.dumps({
                    "conversation": {"complete": True, "turns": [{"role": "user"}]}}))
                with self.assertRaisesRegex(ValueError, "No qualifying"):
                    select_archived_http_response(self.linkage(), archive)
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "archive.zip"
            write_archive(archive, [("20230101_000000_pr_sharings.json",
                                     archive_document(html=next_data_body()))])
            with patch("developer_intent.stage_b.parse_share",
                       return_value={"complete": False, "records": []}) as parser:
                with self.assertRaisesRegex(ValueError, "No qualifying"):
                    select_archived_http_response(self.linkage(), archive)
                parser.assert_called_once()

    def test_archived_http_v3_provenance_package_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); archive_path = root / "archive.zip"
            document = archive_document(html=next_data_body())
            write_archive(archive_path, [("20230101_000000_pr_sharings.json", document)])
            with patch("developer_intent.stage_b.retrieve_share") as network_path:
                prepared = prepare_stage_b_from_archived_http(
                    self.linkage(), archive_path,
                    imported_at="2026-09-30T12:00:00+00:00")
                network_path.assert_not_called()
            archive = prepared["archive"]; provenance = archive["archived_http_import"]
            member_bytes = zipfile.ZipFile(archive_path).read(
                "20230101_000000_pr_sharings.json")
            self.assertEqual(archive["archive_version"], "chatgpt-source-v3")
            self.assertEqual(archive["source_origin"], "archived_http_response")
            self.assertIsNone(archive["retrieved_at"])
            self.assertEqual(archive["retrieval_time_status"],
                             "unknown_archive_timezone")
            self.assertEqual(provenance["DateOfAccess_raw"], "2023-01-02 03:04:05")
            self.assertEqual(provenance["imported_at"], "2026-09-30T12:00:00+00:00")
            self.assertEqual(provenance["archive_sha256"],
                             hashlib.sha256(archive_path.read_bytes()).hexdigest())
            self.assertEqual(provenance["archive_member_sha256"],
                             hashlib.sha256(member_bytes).hexdigest())
            self.assertEqual(provenance["embedded_content_sha256"],
                             hashlib.sha256(next_data_body().encode()).hexdigest())
            self.assertEqual(provenance["embedded_field"], "HTMLContent")
            self.assertEqual(prepared["status"]["package_validation_status"], "validated")
            self.assertEqual(prepared["status"]["semantic_projection_sha256"],
                             semantic_model_hash(prepared["model_view"]))
            paths = persist_stage_b(root, prepared)
            self.assertTrue(all(path.exists() for path in paths.values()))
            with self.assertRaises(FileExistsError):
                persist_stage_b(root, prepared)
            altered = json.loads(json.dumps(prepared["archive"]))
            altered["archived_http_import"]["embedded_content_sha256"] = "0" * 64
            from developer_intent.stage_b import validate_complete_package
            with self.assertRaisesRegex(ValueError, "provenance"):
                validate_complete_package(prepared["linkage"], altered,
                                          prepared["normalized"], prepared["model_view"])

    def test_real_archived_http_controls_have_equal_semantic_projection(self):
        archive = ROOT / "data/raw/allPullRequestSharings.zip"
        for case in ("CASE_193801513E85", "CASE_C482978A9FE9"):
            with self.subTest(case=case):
                linkage = json.loads((ROOT / "cases/manifests/linkage" / f"{case}.json").read_text())
                prepared = prepare_stage_b_from_archived_http(
                    linkage, archive, imported_at="2026-09-30T12:00:00+00:00")
                existing = json.loads((ROOT / "cases/conversations" / case /
                                       "stage_c_model_view.json").read_text())
                self.assertEqual(semantic_model_hash(prepared["model_view"]),
                                 semantic_model_hash(existing))

    def test_offline_materialization_never_uses_derived_evidence_or_network(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); current=root/"current"; legacy=root/"legacy"
            current.mkdir(); legacy.mkdir()
            (root/"evidence.json").write_text(json.dumps({"conversation": {"complete": True}}))
            row=materialize_offline(root, self.linkage(), current, legacy)
            self.assertEqual(row["stage_b_package_status"], "unresolved_no_source")

    def test_offline_corpus_selects_only_ready_and_summary_reconciles(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); legacy=root/"legacy"; current=root/"current"
            legacy.mkdir(); current.mkdir(); self.write_legacy(legacy)
            ready=self.screened(); blocked=self.screened(case_id="CASE_FFFFFFFFFFFF",
                source_case_id="PA-2", stage_b_readiness_status="blocked",
                stage_b_readiness_reason="conversation_unavailable")
            rows=run_offline_corpus(root,[source_row()],[ready,blocked],current,legacy,"screened.csv")
            self.assertEqual(len(rows),1); self.assertEqual(rows[0]["ready_for_stage_c"],"true")
            csv_path=root/"summary.csv"; md_path=root/"summary.md"
            write_summary(csv_path,md_path,rows)
            with csv_path.open() as stream:
                self.assertEqual(len(list(csv.DictReader(stream))),1)
            self.assertIn("Total Stage-A-ready cases: 1",md_path.read_text())


if __name__ == "__main__":
    unittest.main()
