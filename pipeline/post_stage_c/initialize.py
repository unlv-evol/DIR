#!/usr/bin/env python3
"""Initialize the offline Post-Stage-C eligibility and proposed pilot manifests."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from developer_intent.post_stage_c import (  # noqa: E402
    ELIGIBILITY_FIELDS, PILOT_FIELDS, initialize_eligibility_rows, select_pilot, write_csv,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    rows = initialize_eligibility_rows(ROOT)
    pilot = select_pilot(ROOT, rows)
    if not args.validate_only:
        write_csv(ROOT / "cases/manifests/post_stage_c_eligibility.csv", ELIGIBILITY_FIELDS, rows)
        write_csv(ROOT / "cases/manifests/post_stage_c_reconstruction_pilot.csv", PILOT_FIELDS, pilot)
    print(f"eligibility_rows={len(rows)}")
    print(f"pilot_rows={len(pilot)}")
    print("network_calls=0 acquisition_calls=0")


if __name__ == "__main__":
    main()
