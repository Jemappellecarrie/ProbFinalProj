#!/usr/bin/env python3
# ruff: noqa: E402
"""Run one deterministic final-quality acceptance batch and benchmark audit."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config.settings import Settings
from app.schemas.evaluation_models import FinalQualityBatchConfig
from app.scoring.benchmark_audit import normalize_public_benchmark, run_quality_audit
from app.services.final_quality_acceptance_service import FinalQualityAcceptanceService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Deterministic output directory for the run bundle.",
    )
    parser.add_argument("--num-requests", type=int, default=200)
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--candidate-pool-limit", type=int, default=10)
    parser.add_argument("--base-seed", type=int, default=17)
    parser.add_argument("--save-traces", action="store_true")
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=ROOT / "data" / "external" / "nyt_connections_public" / "raw",
    )
    parser.add_argument(
        "--normalized-dir",
        type=Path,
        default=ROOT / "data" / "external" / "nyt_connections_public" / "normalized",
    )
    parser.add_argument(
        "--audit-dir",
        type=Path,
        default=None,
        help="Optional audit output directory. Defaults to <output-dir>/benchmark_audit.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = Settings(demo_mode=False)
    service = FinalQualityAcceptanceService(settings)
    run = service.run_batch(
        FinalQualityBatchConfig(
            num_requests=args.num_requests,
            output_dir=str(args.output_dir),
            demo_mode=False,
            save_traces=args.save_traces,
            top_k_size=args.top_k,
            base_seed=args.base_seed,
            candidate_pool_limit=args.candidate_pool_limit,
        )
    )

    if not (args.normalized_dir / "boards_v1.jsonl").exists():
        normalize_public_benchmark(
            raw_dir=args.raw_dir, normalized_dir=args.normalized_dir
        )
    audit_dir = args.audit_dir or (args.output_dir / "benchmark_audit")
    report = run_quality_audit(
        run_dir=args.output_dir,
        normalized_dir=args.normalized_dir,
        reports_dir=audit_dir,
    )
    shutil.copy2(
        audit_dir / "quality_audit_report.json",
        args.output_dir / "quality_audit_report.json",
    )
    shutil.copy2(
        audit_dir / "quality_audit_report.md",
        args.output_dir / "quality_audit_report.md",
    )

    print(
        json.dumps(
            {
                "output_dir": str(args.output_dir),
                "summary_file": run.output_files["summary"],
                "funnel_report_file": run.output_files["funnel_report"],
                "audit_report_file": str(args.output_dir / "quality_audit_report.json"),
                "generated_top_k_count": report.generated_top_k_count,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
