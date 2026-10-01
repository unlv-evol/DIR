"""Prepare one Protocol v5 Stage B conversation package by neutral DIR Case ID."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from developer_intent.screening import read_source  # noqa: E402
from developer_intent.screening_config import load_config  # noqa: E402
from developer_intent.screening_http import HttpClient  # noqa: E402
from developer_intent.stage_b import (check_new_outputs, output_paths,  # noqa: E402
                                      PATCHTRACK_ARCHIVE_SHA256,
                                      existing_package_status, persist_stage_b, prepare_stage_b,
                                      prepare_stage_b_from_archived_http,
                                      prepare_stage_b_from_legacy, preserve_incomplete_outputs,
                                      select_linkage)
from developer_intent.stage_b_corpus import run_offline_corpus, write_summary  # noqa: E402
from developer_intent.source_corrections import apply_source_corrections  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-id", help="Explicit neutral DIR Case ID, e.g. CASE_<hash>")
    parser.add_argument("--source", type=Path,
                        default=ROOT / "data/raw/final_analysis_dataset_from_patchprompt_study.csv")
    parser.add_argument("--source-correction-dir", type=Path,
                        default=ROOT / "cases/manifests/source_linkage_corrections")
    parser.add_argument("--screened-manifest", type=Path,
                        help="Current Stage A manifest; requires validated ready_for_stage_b authorization")
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--timeout", type=float)
    parser.add_argument("--retries", type=int)
    parser.add_argument("--refresh", action="store_true",
                        help="Re-fetch HTTP source; never overwrites existing Stage B outputs")
    parser.add_argument("--live", action="store_true",
                        help="Permit public ChatGPT retrieval when a reusable cache entry is absent")
    parser.add_argument("--import-legacy-cache", action="store_true",
                        help="Offline import from the validated legacy raw cache; never use network")
    parser.add_argument("--import-archived-http", action="store_true",
                        help="Offline import of original HTMLContent from the replication ZIP")
    parser.add_argument("--archive-path", type=Path,
                        default=ROOT / "data/raw/allPullRequestSharings.zip")
    parser.add_argument("--legacy-cache-dir", type=Path,
                        default=ROOT / "data/intermediate/screening/cache/http")
    parser.add_argument("--expected-model-view-sha256",
                        help="Optional development cross-check for one imported case")
    parser.add_argument("--all-ready", action="store_true",
                        help="Process every ready_for_stage_b row deterministically")
    parser.add_argument("--offline", action="store_true",
                        help="For --all-ready, use existing/current/legacy sources without network")
    parser.add_argument("--summary-csv", type=Path,
                        default=ROOT / "cases/manifests/stage_b_summary.csv")
    parser.add_argument("--summary-md", type=Path,
                        default=ROOT / "cases/manifests/stage_b_summary.md")
    parser.add_argument("--check-config", action="store_true", help="Print safe configuration only")
    args = parser.parse_args()
    config = load_config(ROOT, cache_dir=args.cache_dir, timeout=args.timeout,
                         retries=args.retries)
    if args.check_config:
        print(config.safe_report())
        print("Stage B output roots: cases/manifests/linkage, cases/raw, cases/conversations")
        return
    if args.all_ready:
        if (args.case_id or not args.offline or args.live or args.import_legacy_cache
                or args.import_archived_http):
            parser.error("--all-ready requires --offline and cannot be combined with one-case modes")
        if args.screened_manifest is None:
            parser.error("--all-ready requires --screened-manifest")
        with args.screened_manifest.open(newline="", encoding="utf-8") as stream:
            screened_rows = list(csv.DictReader(stream))
        source = apply_source_corrections(read_source(args.source), args.source_correction_dir)
        try:
            manifest_ref = args.screened_manifest.resolve().relative_to(ROOT).as_posix()
        except ValueError:
            manifest_ref = str(args.screened_manifest.resolve())
        rows = run_offline_corpus(ROOT, source, screened_rows,
                                  config.cache_dir / "http", args.legacy_cache_dir,
                                  manifest_ref)
        write_summary(args.summary_csv, args.summary_md, rows)
        print(f"Stage B offline corpus rows: {len(rows)}")
        print(f"summary: {args.summary_csv}")
        return
    modes = sum((args.live, args.import_legacy_cache, args.import_archived_http))
    if not args.case_id or modes != 1:
        parser.error("Stage B requires --case-id with exactly one source mode")
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
        source = apply_source_corrections(read_source(args.source), args.source_correction_dir)
        manifest_ref = "cases/manifests/screened_PA_PN_cases.csv"
        if args.screened_manifest is not None:
            try:
                manifest_ref = args.screened_manifest.resolve().relative_to(ROOT).as_posix()
            except ValueError:
                manifest_ref = str(args.screened_manifest.resolve())
        linkage = select_linkage(source, args.case_id, screened_rows,
                                 screened_manifest_ref=manifest_ref)
        paths = output_paths(ROOT, args.case_id)
        state = existing_package_status(ROOT, args.case_id)
        if state == "existing_valid":
            parser.error(f"Existing valid Stage B package is preserved: {args.case_id}")
        if args.import_archived_http:
            prepared = prepare_stage_b_from_archived_http(
                linkage, args.archive_path,
                expected_archive_sha256=PATCHTRACK_ARCHIVE_SHA256)
        elif args.import_legacy_cache:
            prepared = prepare_stage_b_from_legacy(
                linkage, args.legacy_cache_dir,
                expected_model_view_sha256=args.expected_model_view_sha256)
        else:
            check_new_outputs(paths)  # fail before network access
            http = HttpClient(config.cache_dir / "http", config.timeout, config.retries)
            prepared = prepare_stage_b(linkage, http, refresh=args.refresh)
        if state == "incomplete":
            preserve_incomplete_outputs(ROOT, args.case_id)
        persist_stage_b(ROOT, prepared)
    except (ValueError, FileExistsError) as exc:
        parser.error(str(exc))
    print(f"Stage B {args.case_id}: {prepared['status']['stage_b_status']}")
    for name, path in paths.items():
        if path.exists():
            print(f"{name}: {path}")


if __name__ == "__main__":
    main()
