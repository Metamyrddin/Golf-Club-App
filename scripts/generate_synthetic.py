#!/usr/bin/env python3
"""Write a labelled synthetic cohort as JSONL.

Examples
--------
    python scripts/generate_synthetic.py --n 10000 --out data/synthetic_profiles.jsonl
    python scripts/generate_synthetic.py --n 50 --out data/sample_profiles.jsonl

The fitting rules are imported from the application. If you change a rule,
regenerate the file. Do not hand-edit labels.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.synthetic import generate  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate labelled synthetic golfer profiles.")
    parser.add_argument("--n", type=int, default=10000, help="Row count, 8000–15000 recommended.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=ROOT / "data" / "synthetic_profiles.jsonl")
    args = parser.parse_args()
    if args.n < 1:
        raise SystemExit("--n must be positive")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    rows = generate(args.n, seed=args.seed)
    with args.out.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")
    flexes: dict[str, int] = {}
    for row in rows:
        flex = row["label"]["flex"]
        flexes[flex] = flexes.get(flex, 0) + 1
    print(f"Wrote {len(rows)} profiles to {args.out}")
    print("Flex mix:", dict(sorted(flexes.items())))


if __name__ == "__main__":
    main()
