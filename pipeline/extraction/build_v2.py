#!/usr/bin/env python3
"""Build one offline Stage B V2 model view from an existing normalized record."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from developer_intent.generated_technical_content import build_v2_model_view  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="Noncanonical destination used for reviewed V2 materialization")
    args = parser.parse_args()
    source = ROOT / "cases/conversations" / args.case_id / "normalized_conversation.json"
    if not source.is_file():
        raise SystemExit(f"Normalized conversation not found: {source}")
    destination = args.output_dir / args.case_id / "stage_c_model_view_v2.json"
    if destination.exists():
        raise SystemExit(f"Refusing to overwrite: {destination}")
    view = build_v2_model_view(json.loads(source.read_text(encoding="utf-8")))
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(view, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                           encoding="utf-8")
    print(destination)


if __name__ == "__main__":
    main()
