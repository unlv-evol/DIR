#!/usr/bin/env python3
"""Run or check the frozen eight-case Post-Stage-C reconstruction pilot."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from developer_intent.post_stage_c_live import (  # noqa: E402
    load_live_config, preflight, run_pilot, safe_config_report,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-config", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    config = load_live_config(ROOT)
    pilot, _ = preflight(ROOT)
    print(json.dumps({**safe_config_report(config), "pilot_cases": [r["case_id"] for r in pilot],
                      "network_calls": 0}, indent=2))
    if args.check_config or args.dry_run:
        return
    results = run_pilot(ROOT, config)
    print(json.dumps({"attempted": len(results),
                      "provider_requests": sum(r["provider_requests"] for r in results),
                      "git_remote_operations": 0}, indent=2))


if __name__ == "__main__":
    main()
