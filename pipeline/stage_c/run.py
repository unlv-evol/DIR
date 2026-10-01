"""Run one Protocol v5 Stage C two-pass conversation extraction."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from developer_intent.stage_c import (OpenAIStageCClient, canonical_hash, extract_stage_c,  # noqa: E402
                                      failed_record, persist_stage_c)
from developer_intent.stage_c_config import load_stage_c_config  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-id", help="One neutral DIR Case ID, e.g. CASE_<hash>")
    parser.add_argument("--live", action="store_true",
                        help="Authorize two independent OpenAI Responses API calls for one case")
    parser.add_argument("--check-config", action="store_true",
                        help="Print non-secret effective configuration; make no API call")
    args = parser.parse_args()
    config = load_stage_c_config(ROOT)
    if args.check_config:
        print(config.safe_report())
        return
    if not args.case_id or not args.live:
        parser.error("Stage C extraction requires --case-id and explicit --live authorization")
    if not config.structurally_valid:
        parser.error("Stage C model configuration is invalid or DIR_STAGE_C_MODEL is missing")
    if not config.api_key:
        parser.error("OPENAI_API_KEY is missing")
    input_path = ROOT / "cases/conversations" / args.case_id / "stage_c_model_view.json"
    output_path = ROOT / "cases/conversations" / args.case_id / "stage_c_extraction_v3.json"
    if output_path.exists():
        parser.error(f"Stage C output exists; no overwrite: {output_path}")
    try:
        package = json.loads(input_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        parser.error(f"Cannot read Stage C input: {exc}")
    input_ref = input_path.relative_to(ROOT).as_posix()
    try:
        record = extract_stage_c(ROOT, args.case_id, package, OpenAIStageCClient(config),
                                 config, input_ref=input_ref)
    except Exception as exc:  # preserve an explicit failure without silently repairing it
        detail = f"{type(exc).__name__}: {exc}"
        if config.api_key:
            detail = detail.replace(config.api_key, "[REDACTED]")
        record = failed_record(args.case_id, input_ref, canonical_hash(package), config,
                               detail, package=package)
    persist_stage_c(output_path, record)
    print(f"Stage C {args.case_id}: {record['status']['stage_c_status']}")
    print(f"output: {output_path}")


if __name__ == "__main__":
    main()
