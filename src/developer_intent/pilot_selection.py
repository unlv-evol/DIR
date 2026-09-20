"""Validate a reviewed pilot manifest and describe its observed diversity."""

from __future__ import annotations

import csv
import hashlib
from collections import Counter
from pathlib import Path
from statistics import median

from .screening_secondary import SECONDARY_FIELDS

SELECTION_FIELDS = (
    "case_id", "source_case_id", "study_role", "C_score", "S_score", "V_score",
    "developer_prompts", "changed_files", "changed_lines", "conversation_words",
    "pr_commits", *SECONDARY_FIELDS, "selection_characteristics", "selection_rationale",
)
COPIED_FIELDS = tuple(field for field in SELECTION_FIELDS
                      if field not in {"study_role", "selection_characteristics", "selection_rationale"})


def read_pilot_manifest(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != list(SELECTION_FIELDS):
            raise ValueError("Pilot manifest columns do not match the documented selection record")
        return list(reader)


def validate_pilot_manifest(screened: list[dict], selected: list[dict]) -> None:
    """Reject stale, ineligible, duplicate, or unsupported selection records."""
    by_id = {row["case_id"]: row for row in screened}
    if len(by_id) != len(screened):
        raise ValueError("Screening manifest has duplicate case IDs")
    if not selected:
        raise ValueError("Pilot manifest is empty")
    seen = set()
    for row in selected:
        case_id = row["case_id"]
        if case_id in seen:
            raise ValueError(f"Duplicate pilot selection: {case_id}")
        seen.add(case_id)
        source = by_id.get(case_id)
        if source is None or source["screening_eligible"] != "true":
            raise ValueError(f"Pilot case is absent or not confirmed eligible: {case_id}")
        if row["study_role"] != "pilot_development":
            raise ValueError(f"Incorrect study role for {case_id}")
        if not row["selection_characteristics"].strip() or not row["selection_rationale"].strip():
            raise ValueError(f"Missing selection observations or rationale for {case_id}")
        for field in COPIED_FIELDS:
            if row[field] != str(source[field]):
                raise ValueError(f"Pilot selection has stale {field} for {case_id}")


def _measure(rows: list[dict], field: str) -> str:
    values = sorted(int(row[field]) for row in rows)
    return f"min {values[0]}, median {median(values):g}, max {values[-1]}"


def pilot_selection_summary(screened: list[dict], selected: list[dict],
                            manifest_path: Path) -> str:
    validate_pilot_manifest(screened, selected)
    eligible = [row for row in screened if row["screening_eligible"] == "true"]
    digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    lines = ["## Pilot selection", "",
             f"Selected pilot/development cases: {len(selected)} of {len(eligible)} "
             "confirmed screening-eligible cases.",
             f"Pilot manifest SHA-256: `{digest}`.",
             "Selection uses reviewed C/S/V diversity and observed conversation/task "
             "characteristics; PA/PN outcome and downstream success are not selection signals.",
             "Generated-artifact and revision counts are deferred until raw extraction.", "",
             "### C/S/V distributions", "",
             "| Score | Eligible pool | Selected pilot |", "| --- | --- | --- |"]
    for field in ("C_score", "S_score", "V_score"):
        pool = dict(sorted(Counter(row[field] for row in eligible).items()))
        pilot = dict(sorted(Counter(row[field] for row in selected).items()))
        lines.append(f"| {field} | `{pool}` | `{pilot}` |")
    lines += ["", "### Joint C/S/V profiles in selected pilot", ""]
    profiles = Counter((row["C_score"], row["S_score"], row["V_score"])
                       for row in selected)
    lines += [f"- ({', '.join(profile)}): {count}"
              for profile, count in sorted(profiles.items())]
    lines += ["", "### Observed complexity", "",
              "| Measure | Eligible pool | Selected pilot |", "| --- | --- | --- |"]
    for field in ("changed_files", "changed_lines", "developer_prompts",
                  "conversation_words", "pr_commits"):
        lines.append(f"| {field} | {_measure(eligible, field)} | {_measure(selected, field)} |")
    lines += ["", f"Single-developer-prompt cases: "
              f"{sum(int(row['developer_prompts']) == 1 for row in selected)}; "
              f"multi-prompt cases: {sum(int(row['developer_prompts']) > 1 for row in selected)}.",
              "Case-level selection observations and rationales are recorded in "
              "`cases/manifests/pilot_cases.csv`.", ""]
    return "\n".join(lines)
