#!/usr/bin/env python3
"""Run or inspect the frozen eight-case Post-Stage-C v2 pilot."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from developer_intent.post_stage_c_v2_live import (  # noqa: E402
    load_live_config, output_paths, preflight, run_pilot, safe_config_report,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-config", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    rows, _, _ = preflight(ROOT)
    config = load_live_config(ROOT)
    if args.check_config:
        print(json.dumps(safe_config_report(config), indent=2, sort_keys=True)); return 0
    if args.dry_run:
        cases = [{**row, "planned_outputs": output_paths(row["case_id"]),
                  "scientific_result": "not_executed"} for row in rows]
        print(json.dumps({"config": safe_config_report(config), "cases": cases}, indent=2)); return 0
    results = run_pilot(ROOT, config)
    print(json.dumps({"attempted": len(results),
                      "provider_requests": sum(r["provider_requests"] for r in results),
                      "git_remote_operations": sum(r["git_operations"] for r in results)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
