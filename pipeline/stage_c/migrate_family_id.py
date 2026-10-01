"""Deterministically migrate one immutable Stage C v2 result to the v3 identity contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from developer_intent.stage_c import migrate_v2_record, persist_stage_c  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-id", required=True)
    args = parser.parse_args()
    case_dir = ROOT / "cases/conversations" / args.case_id
    source = case_dir / "stage_c_extraction.json"
    package_path = case_dir / "stage_c_model_view.json"
    output = case_dir / "stage_c_extraction_v3.json"
    try:
        record = json.loads(source.read_text(encoding="utf-8"))
        package = json.loads(package_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        parser.error(f"Cannot read migration input: {exc}")
    migrated = migrate_v2_record(
        record, package, source_record_ref=source.relative_to(ROOT).as_posix())
    persist_stage_c(output, migrated)
    print(f"migrated: {args.case_id}")
    print(f"family_id: {migrated['first_generation']['family_id']}")
    print(f"output: {output}")


if __name__ == "__main__":
    main()
