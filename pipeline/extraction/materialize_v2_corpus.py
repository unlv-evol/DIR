#!/usr/bin/env python3
"""Materialize and report the complete offline Stage B V2 corpus."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from developer_intent.stage_b_v2_corpus import (  # noqa: E402
    build_corpus_report, validate_report, write_reports,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--materialize", action="store_true",
                        help="Create missing canonical V2 views; never overwrite")
    parser.add_argument("--validate-only", action="store_true",
                        help="Validate existing V2 views without writing reports")
    args = parser.parse_args()
    if args.materialize == args.validate_only:
        parser.error("Choose exactly one of --materialize or --validate-only")
    report = build_corpus_report(ROOT, materialize=args.materialize)
    validate_report(report)
    if args.materialize:
        paths = write_reports(ROOT, report)
        print("reports:", *(str(path) for path in paths), sep="\n")
    print(f"V2 packages: {report['corpus']['valid_v2_files']}/122 valid")
    print(f"V1 exact mappings: {report['legacy_mapping']['exact_legacy_mappings']}/"
          f"{report['legacy_mapping']['total_v1_candidates']}")


if __name__ == "__main__":
    main()
