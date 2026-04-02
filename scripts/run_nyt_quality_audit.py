#!/usr/bin/env python3
# ruff: noqa: E402
"""Run the NYT benchmark quality audit against one generated evaluation run."""

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
from app.scoring.benchmark_audit import normalize_public_benchmark, run_quality_audit


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
        "--raw-dir",
        type=Path,
        default=ROOT / "data" / "external" / "nyt_connections_public" / "raw",
        help="Raw benchmark directory used if normalized artifacts do not exist yet.",
    )
    parser.add_argument(
        "--normalized-dir",
        type=Path,
        default=ROOT / "data" / "external" / "nyt_connections_public" / "normalized",
        help="Directory containing normalized benchmark artifacts.",
    )
    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=ROOT / "data" / "external" / "nyt_connections_public" / "reports",
        help="Directory for quality audit outputs.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = Settings()
    run_dir = args.run_dir if args.run_dir is not None else _latest_run_dir(settings)
    if not (args.normalized_dir / "boards_v1.jsonl").exists():
        normalize_public_benchmark(
            raw_dir=args.raw_dir, normalized_dir=args.normalized_dir
        )
    report = run_quality_audit(
        run_dir=run_dir,
        normalized_dir=args.normalized_dir,
        reports_dir=args.reports_dir,
    )
    print(json.dumps(report.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    main()
