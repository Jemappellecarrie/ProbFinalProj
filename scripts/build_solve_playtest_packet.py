#!/usr/bin/env python3
# ruff: noqa: E402
"""Build deterministic solve-playtest packets for human testers."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.scoring.solve_playtest import build_solve_playtest_packet


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument(
        "--normalized-dir",
        type=Path,
        default=ROOT / "data" / "external" / "nyt_connections_public" / "normalized",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--tester-count", type=int, default=5)
    parser.add_argument("--boards-per-tester", type=int, default=4)
    parser.add_argument("--seed", type=int, default=17)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    packet = build_solve_playtest_packet(
        run_dir=args.run_dir,
        normalized_dir=args.normalized_dir,
        output_dir=args.output_dir,
        tester_count=args.tester_count,
        boards_per_tester=args.boards_per_tester,
        seed=args.seed,
    )
    print(json.dumps(packet, indent=2))


if __name__ == "__main__":
    main()
