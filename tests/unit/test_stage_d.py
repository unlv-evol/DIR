import csv
import copy
import hashlib
import html
import json
import tempfile
import unittest
from pathlib import Path

from developer_intent.stage_d import (ELIGIBILITY, JUDGMENT_FIELDS, MANIFEST,
                                      REVIEW_FIELDS, SAMPLE_COUNTS, STAGE_C_AUTHORITY,
                                      eligible_population, generate_sample,
                                      prepare_review, prepare_review_html,
                                      render_review_html, sample_population, sha256,
                                      validate, validate_workbook)

ROOT = Path(__file__).resolve().parents[2]


class StageDTests(unittest.TestCase):
    def test_authoritative_population_and_deterministic_sample(self):
        population = eligible_population(ROOT)
        self.assertEqual({key: len(value) for key, value in population.items()}, {"PA": 68, "PN": 43})
        first = sample_population(ROOT)
        second = sample_population(ROOT)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 33)
        self.assertEqual(len({row["case_id"] for row in first}), 33)
        self.assertEqual({key: sum(row["stratum"] == key for row in first) for key in SAMPLE_COUNTS}, SAMPLE_COUNTS)

    def test_generated_packages_are_blinded_blank_and_boundary_safe(self):
        generate_sample(ROOT)
        prepare_review(ROOT)
        result = validate(ROOT)
        self.assertEqual(result["sample"], 33)
        packages = []
        for reviewer in ("A", "B"):
            with (ROOT / f"cases/stage_d/reviewer_{reviewer}/stage_d_review.csv").open(newline="") as stream:
                reader = csv.DictReader(stream); rows = list(reader)
                self.assertEqual(tuple(reader.fieldnames), REVIEW_FIELDS)
            self.assertEqual(len(REVIEW_FIELDS), 15)
            self.assertEqual(len(rows), 33)
            self.assertTrue(all(not row[field] for row in rows for field in JUDGMENT_FIELDS))
            packages.append([row["case_id"] for row in rows])
            for row in rows:
                record = json.loads((ROOT / row["case_details"]).read_text())
                self.assertEqual(record["case_id"], row["case_id"])
                linkage = json.loads((ROOT / f"cases/manifests/linkage/{row['case_id']}.json").read_text())
                self.assertEqual(record["source_links"], {
                    "conversation_url": linkage["conversation_url"], "pr_url": linkage["pr_url"]})
                self.assertEqual(row["conversation_url"], record["source_links"]["conversation_url"])
                self.assertEqual(row["pr_url"], record["source_links"]["pr_url"])
                cutoff = record["first_generation_response"]["event_index"]
                self.assertTrue(all(turn["event_index"] < cutoff for turn in record["pre_boundary_conversation"]))
                serialized = json.dumps(record)
                for forbidden in ("Outcome_Class", "reconstruction_status", "historical_observability",
                                  "final_scientific_eligibility", "post_stage_c", "post_c_resolution"):
                    self.assertNotIn(forbidden, serialized)
        self.assertEqual(packages[0], packages[1])
        with (ROOT / "cases/stage_d/reviewer_A/stage_d_review.csv").open(newline="") as stream:
            a_rows = list(csv.DictReader(stream))
        with (ROOT / "cases/stage_d/reviewer_B/stage_d_review.csv").open(newline="") as stream:
            b_rows = list(csv.DictReader(stream))
        self.assertEqual([(r["conversation_url"], r["pr_url"]) for r in a_rows],
                         [(r["conversation_url"], r["pr_url"]) for r in b_rows])

    def test_selected_artifacts_resolve_exactly_from_authoritative_model_view(self):
        generate_sample(ROOT)
        prepare_review(ROOT)
        with (ROOT / MANIFEST).open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        reviewer_artifacts = []
        for row in rows:
            source = json.loads((ROOT / row["stage_c_record"]).read_text())
            view = json.loads((ROOT / source["input"]["stage_b_model_view_ref"]).read_text())
            candidates = {item["candidate_id"]: item for item in view["generated_technical_content_candidates"]}
            a = json.loads((ROOT / row["reviewer_a_evidence_path"]).read_text())
            b = json.loads((ROOT / row["reviewer_b_evidence_path"]).read_text())
            resolved_a = a["first_generation"]["family"]["artifacts"]
            resolved_b = b["first_generation"]["family"]["artifacts"]
            refs = source["first_generation"]["artifact_refs"]
            self.assertEqual(resolved_a, resolved_b)
            self.assertEqual([item["artifact_id"] for item in resolved_a], refs)
            for artifact in resolved_a:
                upstream = candidates[artifact["artifact_id"]]
                self.assertEqual(artifact["content"], upstream["raw_text"])
                self.assertEqual(artifact["source_response_id"], upstream["source_response_id"])
                self.assertEqual(artifact["source_response_id"], source["first_generation"]["response_turn_id"])
                self.assertEqual(artifact["artifact_type"], upstream["kind"])
                self.assertEqual(artifact.get("language"), upstream.get("fence_language"))
            reviewer_artifacts.extend(resolved_a)
        self.assertEqual(len(reviewer_artifacts), 61)

    def test_upstream_hashes_are_preserved(self):
        eligibility = sha256(ROOT / ELIGIBILITY)
        authority = sha256(ROOT / STAGE_C_AUTHORITY)
        generate_sample(ROOT)
        self.assertEqual(sha256(ROOT / ELIGIBILITY), eligibility)
        self.assertEqual(sha256(ROOT / STAGE_C_AUTHORITY), authority)
        with (ROOT / MANIFEST).open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertTrue(all(row["eligibility_source_sha256"] == eligibility for row in rows))
        self.assertTrue(all(row["stage_c_authority_sha256"] == authority for row in rows))

    def test_frozen_xlsx_instruments_match_canonical_csvs(self):
        self.assertEqual(validate_workbook(ROOT, "A"), {"rows": 33, "columns": 15, "dropdowns": 9})
        self.assertEqual(validate_workbook(ROOT, "B"), {"rows": 33, "columns": 15, "dropdowns": 9})

    def test_html_packages_exactly_render_reviewer_safe_json(self):
        result = prepare_review_html(ROOT)
        self.assertEqual(result, {"reviewer_A": 33, "reviewer_B": 33})
        for reviewer in ("A", "B"):
            with (ROOT / f"cases/stage_d/reviewer_{reviewer}/stage_d_review.csv").open(newline="") as stream:
                rows = list(csv.DictReader(stream))
            html_paths = sorted((ROOT / f"cases/stage_d/reviewer_{reviewer}/cases").glob("*.html"))
            self.assertEqual(len(html_paths), 33)
            self.assertEqual({path.stem for path in html_paths}, {row["case_id"] for row in rows})
            for row in rows:
                record = json.loads((ROOT / row["case_details"]).read_text())
                rendered = (ROOT / row["case_details"]).with_suffix(".html").read_text()
                self.assertEqual(rendered, render_review_html(record))
                self.assertNotIn("<script", rendered.lower())
                self.assertNotIn("/Users/", rendered)
                self.assertIn("only the pre-boundary conversation", rendered)
                self.assertIn("PR content is inadmissible", rendered)
                conversation = rendered[rendered.index('<section id="pre-boundary-conversation">'):]
                self.assertEqual(
                    [conversation.index(f'data-turn-id="{turn["turn_id"]}"')
                     for turn in record["pre_boundary_conversation"]],
                    sorted(conversation.index(f'data-turn-id="{turn["turn_id"]}"')
                           for turn in record["pre_boundary_conversation"]),
                )
                for artifact in record["first_generation"]["family"]["artifacts"]:
                    exact = f'<code>{html.escape(artifact["content"], quote=True)}</code>'
                    self.assertIn(exact, rendered)
                for category in ("Context", "Specificity", "Verification"):
                    for item in record["stage_c_extraction"][category]:
                        self.assertIn(html.escape(item["normalized_text"], quote=True), rendered)
                        for span in item["evidence_spans"]:
                            self.assertIn(html.escape(span, quote=True), rendered)

    def test_html_generation_is_deterministic_and_does_not_modify_authorities(self):
        protected = [ROOT / MANIFEST, ROOT / STAGE_C_AUTHORITY]
        for reviewer in ("A", "B"):
            directory = ROOT / f"cases/stage_d/reviewer_{reviewer}"
            protected.append(directory / "stage_d_review.csv")
            protected.extend(sorted((directory / "cases").glob("*.json")))
        before = {path: sha256(path) for path in protected}
        prepare_review_html(ROOT)
        first = {path: sha256(path) for path in ROOT.glob("cases/stage_d/reviewer_*/cases/*.html")}
        prepare_review_html(ROOT)
        second = {path: sha256(path) for path in ROOT.glob("cases/stage_d/reviewer_*/cases/*.html")}
        self.assertEqual(first, second)
        self.assertEqual(len(first), 66)
        self.assertEqual(before, {path: sha256(path) for path in protected})

    def test_html_renderer_escapes_dynamic_content_and_rejects_unsafe_urls(self):
        source = json.loads(next((ROOT / "cases/stage_d/reviewer_A/cases").glob("*.json")).read_text())
        record = copy.deepcopy(source)
        malicious = '<script>alert("stage-d")</script>&'
        record["target_prompt"]["text"] = malicious
        record["first_generation"]["family"]["artifacts"][0]["content"] = malicious
        rendered = render_review_html(record)
        self.assertNotIn(malicious, rendered)
        self.assertIn(html.escape(malicious, quote=True), rendered)
        record["source_links"]["conversation_url"] = "javascript:alert(1)"
        with self.assertRaisesRegex(ValueError, "unsafe source URL"):
            render_review_html(record)
