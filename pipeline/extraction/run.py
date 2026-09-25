"""Prepare one Protocol v5 Stage B conversation package by neutral DIR Case ID."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from developer_intent.screening import read_source  # noqa: E402
from developer_intent.screening_config import load_config  # noqa: E402
from developer_intent.screening_http import HttpClient  # noqa: E402
from developer_intent.stage_b import (check_new_outputs, output_paths,  # noqa: E402
                                      persist_stage_b, prepare_stage_b,
                                      select_linkage)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-id", help="Explicit neutral DIR Case ID, e.g. CASE_<hash>")
    parser.add_argument("--source", type=Path,
                        default=ROOT / "data/raw/final_analysis_dataset_from_patchprompt_study.csv")
    parser.add_argument("--screened-manifest", type=Path,
                        help="Current v5 Stage A manifest; require scientific eligibility and ready_for_stage_b")
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--timeout", type=float)
    parser.add_argument("--retries", type=int)
    parser.add_argument("--refresh", action="store_true",
                        help="Re-fetch HTTP source; never overwrites existing Stage B outputs")
    parser.add_argument("--live", action="store_true", help="Permit public ChatGPT retrieval")
    parser.add_argument("--check-config", action="store_true", help="Print safe configuration only")
    args = parser.parse_args()
    config = load_config(ROOT, cache_dir=args.cache_dir, timeout=args.timeout,
                         retries=args.retries)
    if args.check_config:
        print(config.safe_report())
        print("Stage B output roots: cases/manifests/linkage, cases/raw, cases/conversations")
        return
    if not args.case_id or not args.live:
        parser.error("Stage B preparation requires --case-id and --live")
    old_cache = (ROOT / "data/intermediate/screening/cache").resolve()
    current_cache = old_cache / "current"
    resolved_cache = config.cache_dir.resolve()
    if (resolved_cache == old_cache or (old_cache in resolved_cache.parents
                                        and resolved_cache != current_cache
                                        and current_cache not in resolved_cache.parents)):
        parser.error("Protocol v5 cannot write into the legacy screening cache")
    try:
        screened_rows = None
        if args.screened_manifest is not None:
            with args.screened_manifest.open(newline="", encoding="utf-8") as stream:
                screened_rows = list(csv.DictReader(stream))
        linkage = select_linkage(read_source(args.source), args.case_id, screened_rows)
        paths = output_paths(ROOT, args.case_id)
        check_new_outputs(paths)  # fail before network access
        http = HttpClient(config.cache_dir / "http", config.timeout, config.retries)
        prepared = prepare_stage_b(linkage, http, refresh=args.refresh)
        persist_stage_b(ROOT, prepared)
    except (ValueError, FileExistsError) as exc:
        parser.error(str(exc))
    print(f"Stage B {args.case_id}: {prepared['status']['stage_b_status']}")
    for name, path in paths.items():
        if path.exists():
            print(f"{name}: {path}")


if __name__ == "__main__":
    main()
