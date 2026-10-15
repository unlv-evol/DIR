"""Reproducible Stage D agreement analysis from independent XLSX reviews."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import zipfile
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree

from .stage_d import JUDGMENT_FIELDS, MANIFEST, REVIEW_FIELDS, SEED, STAGE_C_AUTHORITY, read_csv

ANALYSIS_VERSION = "stage-d-inter-reviewer-agreement-v1"
REVIEWER_A = Path("cases/stage_d/reviewer_A/stage_d_review_completed.xlsx")
REVIEWER_B = Path("cases/stage_d/reviewer_B/stage_d_review.xlsx")
OUTPUT_DIR = Path("cases/stage_d/analysis")
ELIGIBILITY = Path("cases/manifests/post_stage_c_eligibility.csv")
CATEGORICAL_FIELDS = JUDGMENT_FIELDS[:9]
FIELD_LABELS = {
    "first_generation_correct": "First-generation identification",
    "target_prompt_correct": "Target prompt",
    "boundary_tFG_correct": "tFG boundary",
    "context_extraction": "Context",
    "specificity_extraction": "Specificity",
    "verification_extraction": "Verification",
    "missing_information": "Missing information",
    "post_boundary_leakage": "Post-boundary leakage",
    "overall_extraction": "Overall extraction",
}
CONTROLLED_VALUES = {
    "first_generation_correct": ("yes", "no", "uncertain"),
    "target_prompt_correct": ("yes", "no", "uncertain"),
    "boundary_tFG_correct": ("yes", "no", "uncertain"),
    "context_extraction": ("correct", "partially_correct", "incorrect", "uncertain"),
    "specificity_extraction": ("correct", "partially_correct", "incorrect", "uncertain"),
    "verification_extraction": ("correct", "partially_correct", "incorrect", "uncertain"),
    "missing_information": ("none", "context", "specificity", "verification", "multiple", "uncertain"),
    "post_boundary_leakage": ("no", "yes", "uncertain"),
    "overall_extraction": ("correct", "needs_correction", "uncertain"),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _children(element: ElementTree.Element, name: str) -> list[ElementTree.Element]:
    return [child for child in element.iter() if _local(child.tag) == name]


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    return ["".join(node.text or "" for node in item.iter() if _local(node.tag) == "t")
            for item in _children(root, "si")]


def read_review_workbook(path: Path) -> list[dict[str, str]]:
    """Read the Review sheet without recalculation or workbook mutation."""
    with zipfile.ZipFile(path) as archive:
        strings = _shared_strings(archive)
        workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
        sheet = next((node for node in _children(workbook, "sheet")
                      if node.attrib.get("name") == "Review"), None)
        if sheet is None:
            raise ValueError(f"Review sheet absent: {path}")
        relationship_id = next((value for key, value in sheet.attrib.items()
                                if _local(key) == "id"), "")
        relationships = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        target = next((node.attrib["Target"] for node in _children(relationships, "Relationship")
                       if node.attrib.get("Id") == relationship_id), "")
        target = target.lstrip("/")
        if not target.startswith("xl/"):
            target = "xl/" + target
        xml = ElementTree.fromstring(archive.read(target))
        cells: dict[str, str] = {}
        for cell in _children(xml, "c"):
            address = cell.attrib["r"]
            value_node = next((node for node in cell if _local(node.tag) == "v"), None)
            value = "" if value_node is None or value_node.text is None else value_node.text
            if cell.attrib.get("t") == "s" and value:
                value = strings[int(value)]
            elif cell.attrib.get("t") == "inlineStr":
                value = "".join(node.text or "" for node in cell.iter()
                                if _local(node.tag) == "t")
            cells[address] = value
    headers = tuple(cells.get(f"{chr(65 + index)}1", "") for index in range(15))
    if headers != REVIEW_FIELDS:
        raise ValueError(f"unexpected Review columns: {path}")
    rows = [{field: cells.get(f"{chr(65 + index)}{row_number}", "")
             for index, field in enumerate(REVIEW_FIELDS)} for row_number in range(2, 35)]
    extra = [address for address, value in cells.items()
             if value and re.fullmatch(r"[A-O](?:3[5-9]|[4-9]\d+)", address)]
    if extra:
        raise ValueError(f"unexpected populated review rows: {path}:{extra}")
    return rows


def validate_reviews(root: Path) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    rows_a = read_review_workbook(root / REVIEWER_A)
    rows_b = read_review_workbook(root / REVIEWER_B)
    for reviewer, rows in (("A", rows_a), ("B", rows_b)):
        ids = [row["case_id"] for row in rows]
        if len(ids) != 33 or len(set(ids)) != 33 or any(not value for value in ids):
            raise ValueError(f"Reviewer {reviewer} does not contain 33 unique cases")
        for row in rows:
            for field in CATEGORICAL_FIELDS:
                if row[field] not in CONTROLLED_VALUES[field]:
                    raise ValueError(
                        f"Reviewer {reviewer} invalid {field} for {row['case_id']}: {row[field]!r}"
                    )
    if [row["case_id"] for row in rows_a] != [row["case_id"] for row in rows_b]:
        raise ValueError("reviewers differ in case identity or order")
    manifest = sorted(read_csv(root / MANIFEST), key=lambda row: int(row["reviewer_order"]))
    strata = Counter(row["stratum"] for row in manifest)
    if (len(manifest) != 33 or strata != {"PA": 20, "PN": 13}
            or {row["random_seed"] for row in manifest} != {str(SEED)}
            or {row["population_size"] for row in manifest} != {"111"}):
        raise ValueError("frozen sampling design differs from the Stage D contract")
    if [row["case_id"] for row in rows_a] != [row["case_id"] for row in manifest]:
        raise ValueError("completed reviewer order differs from the frozen sampling manifest")
    for row_a, row_b in zip(rows_a, rows_b):
        if (row_a["conversation_url"], row_a["pr_url"]) != (row_b["conversation_url"], row_b["pr_url"]):
            raise ValueError(f"reviewer source identity differs: {row_a['case_id']}")
    for reviewer, expected in (("A", rows_a), ("B", rows_b)):
        completed_csv = root / f"cases/stage_d/reviewer_{reviewer}/stage_d_review_completed.csv"
        if completed_csv.exists() and read_csv(completed_csv) != expected:
            raise ValueError(f"completed Reviewer {reviewer} CSV differs from XLSX")
    return rows_a, rows_b


def cohens_kappa(values_a: list[str], values_b: list[str]) -> float | None:
    if len(values_a) != len(values_b) or not values_a:
        raise ValueError("kappa requires equal nonempty paired observations")
    count = len(values_a)
    observed = sum(a == b for a, b in zip(values_a, values_b)) / count
    categories = sorted(set(values_a) | set(values_b))
    counts_a, counts_b = Counter(values_a), Counter(values_b)
    expected = sum((counts_a[value] / count) * (counts_b[value] / count)
                   for value in categories)
    if math.isclose(1.0 - expected, 0.0, abs_tol=1e-15):
        return None
    return (observed - expected) / (1.0 - expected)


def calculate_agreement(rows_a: list[dict[str, str]], rows_b: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    agreement, distributions, disagreements = [], [], []
    for field in CATEGORICAL_FIELDS:
        values_a = [row[field] for row in rows_a]
        values_b = [row[field] for row in rows_b]
        matches = sum(a == b for a, b in zip(values_a, values_b))
        kappa = cohens_kappa(values_a, values_b)
        agreement.append({
            "field": field, "field_label": FIELD_LABELS[field],
            "paired_judgments": str(len(values_a)), "agreements": str(matches),
            "disagreements": str(len(values_a) - matches),
            "exact_agreement_percent": f"{matches / len(values_a) * 100:.2f}",
            "cohens_kappa": "NA" if kappa is None else f"{kappa:.6f}",
            "kappa_status": "undefined_single_identical_category" if kappa is None else "defined",
        })
        for reviewer, values in (("A", values_a), ("B", values_b)):
            counts = Counter(values)
            for category in CONTROLLED_VALUES[field]:
                distributions.append({
                    "field": field, "field_label": FIELD_LABELS[field],
                    "reviewer": reviewer, "category": category,
                    "count": str(counts[category]),
                    "percentage": f"{counts[category] / len(values) * 100:.2f}",
                })
        for row_a, row_b in zip(rows_a, rows_b):
            if row_a[field] != row_b[field]:
                disagreements.append({
                    "case_id": row_a["case_id"], "field": field,
                    "field_label": FIELD_LABELS[field],
                    "reviewer_a_judgment": row_a[field],
                    "reviewer_b_judgment": row_b[field],
                    "reviewer_a_correction_notes": row_a["correction_notes"],
                    "reviewer_b_correction_notes": row_b["correction_notes"],
                    "reviewer_a_reviewer_notes": row_a["reviewer_notes"],
                    "reviewer_b_reviewer_notes": row_b["reviewer_notes"],
                    "reviewer_safe_evidence_path": row_a["case_details"],
                })
    return agreement, distributions, disagreements


def provenance_census(root: Path) -> dict[str, object]:
    """Reproduce the supplementary authorship census from authoritative records."""
    eligible = [row for row in read_csv(root / ELIGIBILITY)
                if row["final_scientific_eligibility"] == "eligible"]
    role_counts = Counter()
    category_counts: dict[str, Counter[str]] = {
        category: Counter() for category in ("context", "specificity", "verification")
    }
    assistant_cases: set[str] = set()
    total = 0
    for ledger_row in eligible:
        record = json.loads((root / ledger_row["stage_c_authoritative_record"]).read_text())
        for category in category_counts:
            for item in record[f"{category}_supplied"]:
                roles = set(item["source_roles"])
                provenance = ("both" if {"user", "assistant"}.issubset(roles)
                              else "assistant_only" if "assistant" in roles
                              else "developer_only" if "user" in roles else "other")
                role_counts[provenance] += 1
                category_counts[category][provenance] += 1
                total += 1
                if "assistant" in roles:
                    assistant_cases.add(ledger_row["case_id"])
    return {
        "eligible_cases": len(eligible),
        "total_items": total,
        "by_provenance": dict(sorted(role_counts.items())),
        "by_category_and_provenance": {
            category: dict(sorted(counts.items()))
            for category, counts in category_counts.items()
        },
        "assistant_supported_items": role_counts["assistant_only"] + role_counts["both"],
        "assistant_supported_cases": sorted(assistant_cases),
    }


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=tuple(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _agreement_report(agreement: list[dict[str, str]], disagreements: list[dict[str, str]]) -> str:
    table = "\n".join(
        f"| {row['field_label']} | {row['agreements']}/{row['paired_judgments']} "
        f"({row['exact_agreement_percent']}%) | {row['disagreements']} | {row['cohens_kappa']} |"
        for row in agreement
    )
    cases = ", ".join(sorted({row["case_id"] for row in disagreements}))
    paired = sum(int(row["paired_judgments"]) for row in agreement)
    matches = sum(int(row["agreements"]) for row in agreement)
    pooled = matches / paired * 100
    return f"""# Stage D inter-reviewer agreement

## Design and inputs

Stage D sampled 33 of 111 scientifically eligible cases by proportional PA/PN-stratified random sampling without replacement: 20 of 68 PA and 13 of 43 PN, using seed `{SEED}`. Both PhD reviewers independently assessed the same cases in the same frozen order with PA/PN and downstream outcomes concealed. The analysis reads the original completed workbooks directly and does not use adjudicated judgments.

Nine categorical fields yield 297 paired judgments. `uncertain` is retained as an observed category. Free-text notes are preserved in the disagreement inventory and excluded from agreement calculations.

## Field-level results

| Field | Exact agreement | Disagreements | Cohen's kappa |
|---|---:|---:|---:|
{table}

Cohen's kappa is unweighted because the judgments are treated as nominal categories. `NA` means kappa is mathematically undefined because both reviewers assigned the same single category to all 33 cases; it is not replaced by 1.0. Kappa values of zero or slightly below zero in highly imbalanced fields do not contradict high exact agreement: expected agreement from the marginal distributions is already very high.

## Pooled descriptive result

There were {matches} agreements among {paired} paired categorical judgments ({pooled:.2f}%), with {len(disagreements)} field-level disagreements across {len(set(row['case_id'] for row in disagreements))} cases: {cases}. This pooled percentage describes judgments, not the percentage of cases with complete agreement, and it does not replace field-specific reliability estimates.

## Interpretation and limits

Independent agreement was complete for first-generation identification, target prompt, Context, Specificity, Verification, and post-boundary leakage. Disagreements concerned three `tFG` boundary judgments, one missing-information judgment, and four overall-extraction judgments. Subsequent joint findings and decisions are documented separately and never enter these calculations.

Stage D directly measures judgments on extraction correctness, missing information, leakage, and boundary selection. It does not contain a dedicated categorical field isolating provenance correctness. The supplementary provenance audit therefore cannot be interpreted as 480 manually validated items: independent Stage D review covered 33 sampled cases.

## Reproduction

```text
python3 -B pipeline/stage_d/run_agreement.py
```
"""


def _adjudication_findings() -> str:
    return """# Stage D adjudication findings

These findings were established jointly after the two independent reviews. They are separate from, and were not used in, inter-reviewer agreement calculations.

## Initial disagreement scope

The independent records contain eight categorical disagreements across `CASE_188C69620856`, `CASE_EE7F13CD9FB7`, `CASE_AD8C4F13A90B`, and `CASE_522F0F296F37`. Their original judgments and notes remain unchanged in the source workbooks and are reproduced in `reviewer_disagreements.csv`.

## Suspected omitted artifact

For `CASE_522F0F296F37`, Reviewer A questioned whether an additional shell artifact involving `MD5_PATH` had been omitted. Joint review established that this material was already supplied in the developer prompt and was not newly generated by the assistant. The selected first-generation artifact family was correct; the suspected omission was not an extraction error.

## Timestamp concerns

The reviewers examined the cutoff timestamps questioned for `CASE_188C69620856` and `CASE_AD8C4F13A90B`. The recorded values use ISO 8601 extended format, and conversion to the applicable local timezones confirmed consistency. No timestamp correction was required. `CASE_EE7F13CD9FB7` retains its original boundary disagreement; no additional case-specific explanation is asserted beyond the available adjudication evidence.

## Assistant-supported Context

For `CASE_EE7F13CD9FB7`, the questioned assistant-authored Context support occurred before `tFG` and therefore belonged to the admissible pre-boundary conversation under the established conversation-state policy. Subsequent manual inspection separately identified `CASE_6C65BC36BF60` as another case with assistant-supported Context. It was not one of the four original disagreement cases.

## Supplementary corpus-wide provenance audit

A separate read-only audit of all 111 eligible cases reproduced 480 authoritative C/S/V items: 464 developer-only, 13 assistant-only, and three citing both roles. Sixteen assistant-supported items occur across four cases—`CASE_34CAAE296942`, `CASE_6C65BC36BF60`, `CASE_EE7F13CD9FB7`, and `CASE_F7BED13B8119`—and all are Context. No Specificity or Verification item cites assistant evidence.

This corpus-wide audit is supplementary methodological evidence, not part of the original 33-case agreement calculation and not evidence that all 480 items received Stage D human validation.
"""


def _adjudication_decisions() -> str:
    return """# Stage D adjudication decisions

These decisions follow the joint findings and do not overwrite either reviewer's independent annotations.

1. **Artifact identification:** Retain the original first-generation artifact identification for `CASE_522F0F296F37`; no correction is required.
2. **Temporal boundary:** Accept the verified first-generation cutoff timestamps; no timestamp correction is required based on the adjudicated concerns.
3. **Context extraction:** Retain assistant-supported Context evidence when it occurs before `tFG` and satisfies the existing content and provenance requirements.
4. **Evidence policy:** Retain the conversation-state C/S/V methodology. Developer and assistant turns before `tFG` remain admissible. No developer-origin-only restriction is introduced, and the primary construct is unchanged.
5. **Stage C authority:** Preserve all authoritative Stage C extraction records; these adjudicated concerns require no Stage C modification.
6. **Independent-review integrity:** Preserve both original reviewer records, their disagreements, and explanatory notes. Future refinements must be separately documented and versioned.

Consequently, this analysis changes neither the Stage D sample nor Stage C, Post-C, eligibility, Stage E, or Stage F artifacts.
"""


def generate_analysis(root: Path) -> dict[str, object]:
    rows_a, rows_b = validate_reviews(root)
    agreement, distributions, disagreements = calculate_agreement(rows_a, rows_b)
    output = root / OUTPUT_DIR
    output.mkdir(parents=True, exist_ok=True)
    paths = {
        "agreement": output / "inter_reviewer_agreement.csv",
        "disagreements": output / "reviewer_disagreements.csv",
        "distributions": output / "reviewer_category_distributions.csv",
        "report": output / "inter_reviewer_agreement.md",
        "findings": output / "adjudication_findings.md",
        "decisions": output / "adjudication_decisions.md",
    }
    _write_csv(paths["agreement"], agreement)
    _write_csv(paths["disagreements"], disagreements)
    _write_csv(paths["distributions"], distributions)
    paths["report"].write_text(_agreement_report(agreement, disagreements), encoding="utf-8")
    paths["findings"].write_text(_adjudication_findings(), encoding="utf-8")
    paths["decisions"].write_text(_adjudication_decisions(), encoding="utf-8")
    manifest_path = output / "analysis_manifest.json"
    pooled_pairs = sum(int(row["paired_judgments"]) for row in agreement)
    pooled_agreements = sum(int(row["agreements"]) for row in agreement)
    provenance = provenance_census(root)
    manifest = {
        "analysis_version": ANALYSIS_VERSION, "analysis_date": "2026-10-15",
        "method": {"matching_key": "case_id", "categorical_fields": list(CATEGORICAL_FIELDS),
                   "uncertain_handling": "retained_as_observed_category",
                   "agreement": "exact_pairwise_agreement",
                   "cohens_kappa": "unweighted_nominal; NA when 1-expected_agreement is zero",
                   "free_text": "preserved_in_disagreement_inventory_not_scored"},
        "inputs": {str(REVIEWER_A): sha256(root / REVIEWER_A),
                   str(REVIEWER_B): sha256(root / REVIEWER_B),
                   str(MANIFEST): sha256(root / MANIFEST),
                   str(STAGE_C_AUTHORITY): sha256(root / STAGE_C_AUTHORITY),
                   str(ELIGIBILITY): sha256(root / ELIGIBILITY)},
        "design": {"eligible_population": 111, "PA_population": 68, "PN_population": 43,
                   "sample": 33, "PA_sample": 20, "PN_sample": 13, "seed": SEED,
                   "paired_categorical_judgments": pooled_pairs},
        "results": {"agreements": pooled_agreements, "disagreements": len(disagreements),
                    "disagreement_cases": sorted({row["case_id"] for row in disagreements}),
                    "pooled_exact_agreement_percent": round(pooled_agreements / pooled_pairs * 100, 2)},
        "supplementary_provenance_audit": provenance,
        "implementation": {
            "library": str(Path("src/developer_intent/stage_d_analysis.py")),
            "runner": str(Path("pipeline/stage_d/run_agreement.py")),
        },
        "outputs": {str(path.relative_to(root)): sha256(path) for path in paths.values()},
        "manifest_self_hash": "omitted_to_avoid_recursive_self-reference",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest
