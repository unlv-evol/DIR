import csv
import hashlib
import json
import unittest
from pathlib import Path

from developer_intent.stage_d_analysis import (
    CATEGORICAL_FIELDS,
    ELIGIBILITY,
    OUTPUT_DIR,
    REVIEWER_A,
    REVIEWER_B,
    calculate_agreement,
    cohens_kappa,
    generate_analysis,
    provenance_census,
    sha256,
    validate_reviews,
)
from developer_intent.stage_d import MANIFEST, STAGE_C_AUTHORITY

ROOT = Path(__file__).resolve().parents[2]


class StageDAgreementAnalysisTests(unittest.TestCase):
    def test_completed_workbooks_are_complete_aligned_and_controlled(self):
        rows_a, rows_b = validate_reviews(ROOT)
        self.assertEqual(len(rows_a), 33)
        self.assertEqual([row["case_id"] for row in rows_a],
                         [row["case_id"] for row in rows_b])
        self.assertTrue(all(row[field] for row in rows_a + rows_b
                            for field in CATEGORICAL_FIELDS))

    def test_expected_agreement_and_disagreement_inventory(self):
        rows_a, rows_b = validate_reviews(ROOT)
        agreement, _, disagreements = calculate_agreement(rows_a, rows_b)
        by_field = {row["field"]: row for row in agreement}
        expected = {
            "first_generation_correct": (33, "100.00", "NA"),
            "target_prompt_correct": (33, "100.00", "NA"),
            "boundary_tFG_correct": (30, "90.91", "0.000000"),
            "context_extraction": (33, "100.00", "NA"),
            "specificity_extraction": (33, "100.00", "NA"),
            "verification_extraction": (33, "100.00", "NA"),
            "missing_information": (32, "96.97", "0.000000"),
            "post_boundary_leakage": (33, "100.00", "NA"),
            "overall_extraction": (29, "87.88", "-0.047619"),
        }
        self.assertEqual(sum(int(row["agreements"]) for row in agreement), 289)
        self.assertEqual(len(disagreements), 8)
        self.assertEqual({row["case_id"] for row in disagreements}, {
            "CASE_188C69620856", "CASE_522F0F296F37",
            "CASE_AD8C4F13A90B", "CASE_EE7F13CD9FB7",
        })
        for field, (matches, percentage, kappa) in expected.items():
            self.assertEqual((int(by_field[field]["agreements"]),
                              by_field[field]["exact_agreement_percent"],
                              by_field[field]["cohens_kappa"]),
                             (matches, percentage, kappa))

    def test_kappa_undefined_and_uncertain_is_an_observed_category(self):
        self.assertIsNone(cohens_kappa(["yes"] * 4, ["yes"] * 4))
        self.assertAlmostEqual(cohens_kappa(
            ["yes", "uncertain", "no", "uncertain"],
            ["yes", "uncertain", "yes", "no"],
        ), 0.2727272727272727)

    def test_supplementary_provenance_census_is_reproduced(self):
        census = provenance_census(ROOT)
        self.assertEqual(census["eligible_cases"], 111)
        self.assertEqual(census["total_items"], 480)
        self.assertEqual(census["by_provenance"], {
            "assistant_only": 13, "both": 3, "developer_only": 464,
        })
        self.assertEqual(census["assistant_supported_items"], 16)
        self.assertEqual(census["assistant_supported_cases"], [
            "CASE_34CAAE296942", "CASE_6C65BC36BF60",
            "CASE_EE7F13CD9FB7", "CASE_F7BED13B8119",
        ])
        self.assertEqual(census["by_category_and_provenance"]["specificity"].get(
            "assistant_only", 0), 0)
        self.assertEqual(census["by_category_and_provenance"]["verification"].get(
            "assistant_only", 0), 0)

    def test_generation_is_deterministic_and_preserves_inputs(self):
        protected = [ROOT / REVIEWER_A, ROOT / REVIEWER_B, ROOT / MANIFEST,
                     ROOT / STAGE_C_AUTHORITY, ROOT / ELIGIBILITY]
        with (ROOT / ELIGIBILITY).open(newline="") as stream:
            eligibility_rows = list(csv.DictReader(stream))
        protected.extend(ROOT / row["stage_c_authoritative_record"]
                         for row in eligibility_rows
                         if row["final_scientific_eligibility"] == "eligible")
        before = {path: sha256(path) for path in protected}
        first = generate_analysis(ROOT)
        first_outputs = {
            path: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (ROOT / OUTPUT_DIR).iterdir() if path.is_file()
        }
        second = generate_analysis(ROOT)
        second_outputs = {
            path: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (ROOT / OUTPUT_DIR).iterdir() if path.is_file()
        }
        self.assertEqual(first, second)
        self.assertEqual(first_outputs, second_outputs)
        self.assertEqual(before, {path: sha256(path) for path in protected})
        manifest = json.loads((ROOT / OUTPUT_DIR / "analysis_manifest.json").read_text())
        self.assertEqual(manifest["results"]["pooled_exact_agreement_percent"], 97.31)


if __name__ == "__main__":
    unittest.main()
