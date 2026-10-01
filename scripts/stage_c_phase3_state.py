#!/usr/bin/env python3
"""Inspect resumable Stage C V2 coverage for the Stage-B-ready corpus."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STAGE_B = ROOT / "cases/manifests/stage_b_summary.csv"
HELD = {
    "CASE_27C861787A74",
    "CASE_488C3B9CF30B",
    "CASE_F9321AC6C899",
}


def ready_case_ids() -> list[str]:
    with STAGE_B.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    case_ids = sorted(
        row["case_id"] for row in rows
        if row.get("ready_for_stage_c", "").lower() == "true"
    )
    if len(case_ids) != 122 or len(set(case_ids)) != 122:
        raise SystemExit(
            f"Systemic corpus error: expected 122 unique Stage-B-ready cases, "
            f"found {len(case_ids)} rows and {len(set(case_ids))} unique IDs"
        )
    return case_ids


def output_paths(case_id: str) -> list[Path]:
    case_dir = ROOT / "cases/conversations" / case_id
    return sorted(
        path for path in case_dir.glob("stage_c_extraction_v5*.json")
        if not path.name.endswith(".diagnostic.json")
    )


def load_record(path: Path) -> dict | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def case_state(case_id: str) -> dict[str, str | bool]:
    paths = output_paths(case_id)
    if not paths:
        return {
            "case_id": case_id,
            "accounted": False,
            "disposition": "remaining_never_run_v2",
            "status": "not_run",
            "output": "",
            "diagnostic": "",
        }

    canonical = ROOT / "cases/conversations" / case_id / "stage_c_extraction_v5.json"
    ordered = ([canonical] if canonical in paths else []) + [p for p in paths if p != canonical]
    records = [(path, load_record(path)) for path in ordered]
    complete = next(
        ((path, record) for path, record in records
         if record and record.get("status", {}).get("stage_c_status") == "complete"),
        None,
    )
    unresolved = next(
        ((path, record) for path, record in records
         if record and record.get("status", {}).get("stage_c_status") == "unresolved"),
        None,
    )
    selected = complete or unresolved or records[0]
    path, record = selected
    status = (record or {}).get("status", {}).get("stage_c_status", "invalid_record")

    if complete:
        disposition = "complete_validated"
    elif unresolved:
        disposition = "scientifically_unresolved"
    elif case_id in HELD:
        disposition = "pending_controlled_resolution"
    elif status == "failed":
        reason = (record or {}).get("status", {}).get("failure_reason", "")
        disposition = (
            "infrastructure_failed"
            if "InvocationFailure" in reason or "APIConnectionError" in reason
            else "validation_failed"
        )
    else:
        disposition = "blocked"

    diagnostic = path.with_suffix(".diagnostic.json")
    return {
        "case_id": case_id,
        "accounted": True,
        "disposition": disposition,
        "status": status,
        "output": path.relative_to(ROOT).as_posix(),
        "diagnostic": diagnostic.relative_to(ROOT).as_posix() if diagnostic.exists() else "",
    }


def inventory() -> list[dict[str, str | bool]]:
    return [case_state(case_id) for case_id in ready_case_ids()]


def print_summary(rows: list[dict[str, str | bool]]) -> None:
    accounted = sum(bool(row["accounted"]) for row in rows)
    counts = Counter(str(row["disposition"]) for row in rows if row["accounted"])
    print(f"Stage-B-ready: {len(rows)}")
    print(f"Stage C V2 accounted for: {accounted}")
    print(f"Remaining: {len(rows) - accounted}")
    for name in (
        "complete_validated", "scientifically_unresolved", "validation_failed",
        "infrastructure_failed", "pending_controlled_resolution", "blocked",
    ):
        print(f"{name}: {counts[name]}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--remaining", action="store_true")
    group.add_argument("--summary", action="store_true")
    group.add_argument("--accounted-count", action="store_true")
    group.add_argument("--status")
    group.add_argument("--validate-coverage", action="store_true")
    args = parser.parse_args()
    rows = inventory()

    if args.remaining:
        for row in rows:
            if not row["accounted"]:
                print(row["case_id"])
    elif args.summary:
        print_summary(rows)
    elif args.accounted_count:
        print(sum(bool(row["accounted"]) for row in rows))
    elif args.status:
        match = next((row for row in rows if row["case_id"] == args.status), None)
        if match is None:
            raise SystemExit(f"Case is not in the Stage-B-ready corpus: {args.status}")
        print(json.dumps(match, sort_keys=True))
    else:
        print_summary(rows)
        unaccounted = [str(row["case_id"]) for row in rows if not row["accounted"]]
        if unaccounted:
            raise SystemExit(
                f"Coverage incomplete: {len(unaccounted)} unaccounted cases: "
                + ", ".join(unaccounted)
            )
        print("Coverage validation passed: 122/122 accounted for; unaccounted=0")


if __name__ == "__main__":
    main()
