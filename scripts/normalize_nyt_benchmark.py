#!/usr/bin/env python3
# ruff: noqa: E402
"""Normalize the local public NYT Connections benchmark into board-level artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.scoring.benchmark_audit import normalize_public_benchmark


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=ROOT / "data" / "external" / "nyt_connections_public" / "raw",
        help="Directory containing local raw benchmark files.",
    )
    parser.add_argument(
        "--normalized-dir",
        type=Path,
        default=ROOT / "data" / "external" / "nyt_connections_public" / "normalized",
        help="Directory where normalized artifacts should be written.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = normalize_public_benchmark(
        raw_dir=args.raw_dir,
        normalized_dir=args.normalized_dir,
    )
    print(json.dumps(result.manifest.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    main()
