#!/usr/bin/env python3
# ruff: noqa: E402
"""Run the demo generation pipeline from the command line."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config.settings import Settings
from app.schemas.api import PuzzleGenerationRequest
from app.services.generation_service import GenerationService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=17, help="Deterministic demo seed.")
    parser.add_argument(
        "--no-trace",
        action="store_true",
        help="Disable generation trace output in the response payload.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    service = GenerationService(Settings())
    payload = service.generate_puzzle(
        PuzzleGenerationRequest(
            seed=args.seed,
            include_trace=not args.no_trace,
            developer_mode=not args.no_trace,
        )
    )
    print(json.dumps(payload.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    main()
