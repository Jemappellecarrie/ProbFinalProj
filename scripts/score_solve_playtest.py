#!/usr/bin/env python3
# ruff: noqa: E402
"""Score completed solve-playtest response files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.scoring.solve_playtest import score_solve_playtest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet-key", type=Path, required=True)
    parser.add_argument(
        "--response-file",
        dest="response_files",
        type=Path,
        action="append",
        default=[],
        help="Completed CSV or JSON response file. Repeat as needed.",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    results = score_solve_playtest(
        packet_key_path=args.packet_key,
        response_paths=args.response_files,
        output_dir=args.output_dir,
    )
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
