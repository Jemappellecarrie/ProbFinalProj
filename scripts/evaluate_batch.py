#!/usr/bin/env python3
"""Run an offline batch evaluation and persist accepted/rejected/top-k artifacts."""

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
from app.schemas.evaluation_models import BatchEvaluationConfig
from app.services.evaluation_service import EvaluationService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--num-puzzles", type=int, default=10, help="Number of puzzles to evaluate.")
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Optional output directory. Defaults to data/processed/eval_runs/<run_id>.",
    )
    parser.add_argument("--base-seed", type=int, default=17, help="Base seed for deterministic runs.")
    parser.add_argument("--top-k", type=int, default=5, help="Number of top accepted puzzles to keep.")
    parser.add_argument(
        "--no-traces",
        action="store_true",
        help="Skip saving generation traces in the evaluation artifacts.",
    )
    parser.set_defaults(demo_mode=True)
    parser.add_argument(
        "--demo-mode",
        dest="demo_mode",
        action="store_true",
        help="Run in demo mode.",
    )
    parser.add_argument(
        "--no-demo-mode",
        dest="demo_mode",
        action="store_false",
        help="Disable demo mode. This path remains intentionally unimplemented.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    service = EvaluationService(Settings())
    config = BatchEvaluationConfig(
        num_puzzles=args.num_puzzles,
        output_dir=args.output_dir,
        demo_mode=args.demo_mode,
        save_traces=not args.no_traces,
        top_k_size=args.top_k,
        base_seed=args.base_seed,
    )
    run = service.evaluate_batch(config)
    print(json.dumps(run.summary.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    main()
