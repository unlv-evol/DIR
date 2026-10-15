#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from developer_intent.stage_e import freeze, stage_d_closure, verify, write_stage_d_closure


def main() -> None:
    parser = argparse.ArgumentParser(description="Freeze and verify Stage E records")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--audit-stage-d", action="store_true")
    action.add_argument("--freeze", action="store_true")
    action.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.audit_stage_d:
        result = write_stage_d_closure(ROOT)
    elif args.freeze:
        result = freeze(ROOT)
    else:
        result = verify(ROOT)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
