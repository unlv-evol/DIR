#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from developer_intent.stage_d import (SEED, generate_sample, prepare_review,
                                      prepare_review_html, repository_remote, validate)


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage D sampling and review preparation")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check-config", action="store_true")
    action.add_argument("--generate-sample", action="store_true")
    action.add_argument("--prepare-review", action="store_true")
    action.add_argument("--prepare-review-html", action="store_true")
    action.add_argument("--validate", action="store_true")
    args = parser.parse_args()
    if args.check_config:
        print(json.dumps({"random_seed": SEED, "repository_remote": repository_remote(ROOT),
                          "sample": 33, "PA": 20, "PN": 13}, indent=2))
    elif args.generate_sample:
        print(json.dumps({"generated_sample": len(generate_sample(ROOT)), "random_seed": SEED}, indent=2))
    elif args.prepare_review:
        prepare_review(ROOT)
        print(json.dumps({"reviewer_packages_prepared": 2, "cases_per_reviewer": 33}, indent=2))
    elif args.prepare_review_html:
        print(json.dumps(prepare_review_html(ROOT), indent=2))
    else:
        print(json.dumps(validate(ROOT), indent=2))


if __name__ == "__main__":
    main()
