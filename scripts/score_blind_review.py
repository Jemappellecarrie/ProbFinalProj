#!/usr/bin/env python3
# ruff: noqa: E402
"""Score completed blind review forms and compute the publishable-rate gate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.scoring.blind_review import score_blind_review


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--answer-key",
        type=Path,
        required=True,
        help="Path to blind_review_key.json.",
    )
    parser.add_argument(
        "--review-file",
        dest="review_files",
        type=Path,
        action="append",
        default=[],
        help="Completed reviewer CSV or JSON file. Repeat for multiple reviewers.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT
        / "data"
        / "external"
        / "nyt_connections_public"
        / "review_packets",
        help="Directory where scoring outputs should be written.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = score_blind_review(
        answer_key_path=args.answer_key,
        review_paths=args.review_files,
        output_dir=args.output_dir,
    )
    print(json.dumps(summary.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    main()
