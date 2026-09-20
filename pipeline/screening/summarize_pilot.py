"""Validate the reviewed pilot manifest and refresh selection_summary.md."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from developer_intent.pilot_selection import (  # noqa: E402
    pilot_selection_summary, read_pilot_manifest,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--screened", type=Path, default=ROOT / "cases/manifests/screened_cases.csv")
    parser.add_argument("--pilot", type=Path, default=ROOT / "cases/manifests/pilot_cases.csv")
    parser.add_argument("--summary", type=Path, default=ROOT / "cases/manifests/selection_summary.md")
    args = parser.parse_args()
    with args.screened.open(newline="", encoding="utf-8") as stream:
        screened = list(csv.DictReader(stream))
    selected = read_pilot_manifest(args.pilot)
    section = pilot_selection_summary(screened, selected, args.pilot)
    prior = args.summary.read_text(encoding="utf-8")
    before = prior.split("\n## Pilot selection\n", 1)[0].rstrip()
    before = before.replace("Screening only; no pilot cases selected.\n", "")
    args.summary.write_text(before + "\n\n" + section, encoding="utf-8")
    print(f"Validated {len(selected)} pilot cases and refreshed {args.summary}")


if __name__ == "__main__":
    main()
