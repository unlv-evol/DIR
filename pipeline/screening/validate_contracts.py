"""Validate already-generated Stage A CSV artifacts; never retrieves sources."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from developer_intent.stage_a_contracts import (  # noqa: E402
    validate_correspondence_review, validate_stage_a_outputs)
from developer_intent.screening import read_source  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--screened", type=Path, required=True)
    parser.add_argument("--eligible", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--reviews-dir", type=Path)
    parser.add_argument("--source", type=Path,
                        default=ROOT / "data/raw/final_analysis_dataset_from_patchprompt_study.csv")
    args = parser.parse_args()
    screened, eligible, mapping = validate_stage_a_outputs(
        args.screened, args.eligible, args.mapping)
    reviews = 0
    if args.reviews_dir is not None:
        source_by_case = {row["Case ID"].strip(): row for row in read_source(args.source)}
        for path in sorted(args.reviews_dir.glob("*.json")):
            review = json.loads(path.read_text(encoding="utf-8"))
            source_case_id = next((row["source_case_id"] for row in screened
                                   if row["case_id"] == path.stem), None)
            if source_case_id is None:
                raise ValueError(f"Review is outside screened scope: {path.name}")
            validate_correspondence_review(review, source_by_case[source_case_id])
            reviews += 1
    print(f"Valid: screened={len(screened)}, eligible={len(eligible)}, "
          f"mapping={len(mapping)}, reviews={reviews}")


if __name__ == "__main__":
    main()
