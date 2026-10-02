#!/usr/bin/env python3
"""Zero-acquisition preflight and future entry point for the frozen v2 pilot."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from developer_intent.post_stage_c_v2 import (  # noqa: E402
    ACQUISITION_RECORD_VERSION, BOUNDARY_RECORD_VERSION, FROZEN_CASES,
    PILOT_MANIFEST_VERSION, RECONSTRUCTION_CONTRACT_VERSION, pilot_rows,
)


def config() -> dict:
    retries = int(os.environ.get("DIR_POST_C_TRANSPORT_RETRIES", "2"))
    if retries < 0 or retries > 2:
        raise ValueError("Transport retries must be between zero and two")
    return {"contract": RECONSTRUCTION_CONTRACT_VERSION,
            "acquisition_record": ACQUISITION_RECORD_VERSION,
            "boundary_record": BOUNDARY_RECORD_VERSION,
            "transport_retries": retries, "execution_mode": "sequential",
            "network_during_check_or_dry_run": False}


def validate_plan(rows: list[dict[str, str]]) -> None:
    if tuple(row["case_id"] for row in rows) != FROZEN_CASES or len(rows) != 8:
        raise ValueError("The v2 pilot must contain the frozen eight cases in order")
    if any(row["executed"] != "false" for row in rows):
        raise ValueError("The prepared v2 pilot must be unexecuted")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-config", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    rows = pilot_rows(ROOT); validate_plan(rows)
    if args.check_config:
        print(json.dumps(config(), indent=2, sort_keys=True)); return 0
    if args.dry_run:
        print(json.dumps({"config": config(), "cases": rows}, indent=2)); return 0
    raise SystemExit("Live v2 acquisition is not authorized at this checkpoint; use --check-config or --dry-run")


if __name__ == "__main__":
    raise SystemExit(main())
