#!/usr/bin/env python3
# ruff: noqa: E402
"""Build a deterministic blind review packet mixing generated and benchmark boards."""

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
from app.scoring.blind_review import build_blind_review_packet


def _latest_run_dir(settings: Settings) -> Path:
    run_dirs = [path for path in settings.eval_runs_dir.iterdir() if path.is_dir()]
    if not run_dirs:
        raise FileNotFoundError(
            f"No evaluation runs found under {settings.eval_runs_dir}. Run scripts/evaluate_batch.py first."
        )
    return max(run_dirs, key=lambda path: path.stat().st_mtime)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=None,
        help="Evaluation run directory. Defaults to the latest run under data/processed/eval_runs.",
    )
    parser.add_argument(
        "--normalized-dir",
        type=Path,
        default=ROOT / "data" / "external" / "nyt_connections_public" / "normalized",
        help="Directory containing normalized benchmark artifacts.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT
        / "data"
        / "external"
        / "nyt_connections_public"
        / "review_packets",
        help="Directory where the packet, key, and instructions should be written.",
    )
    parser.add_argument(
        "--generated-count", type=int, default=10, help="Generated board sample size."
    )
    parser.add_argument(
        "--benchmark-count", type=int, default=10, help="Benchmark board sample size."
    )
    parser.add_argument(
        "--seed", type=int, default=17, help="Deterministic packet seed."
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = Settings()
    run_dir = args.run_dir if args.run_dir is not None else _latest_run_dir(settings)
    bundle = build_blind_review_packet(
        run_dir=run_dir,
        normalized_dir=args.normalized_dir,
        output_dir=args.output_dir,
        generated_count=args.generated_count,
        benchmark_count=args.benchmark_count,
        seed=args.seed,
    )
    print(json.dumps(bundle.output_files, indent=2))


if __name__ == "__main__":
    main()
