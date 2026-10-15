#!/usr/bin/env python3
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from developer_intent.stage_d_analysis import generate_analysis


if __name__ == "__main__":
    print(json.dumps(generate_analysis(ROOT)["results"], indent=2))
