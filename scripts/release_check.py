#!/usr/bin/env python3
# ruff: noqa: E402
"""Run the Stage 4 release-candidate validation checks."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BACKEND_PYTHON = ROOT / "backend" / ".venv" / "bin" / "python"
DEFAULT_OUTPUT_DIR = (
    ROOT / "data" / "processed" / "release_validation" / "stage4_release_check"
)
PYTHON_CHECK_PATHS = [
    "backend/app/services/evaluation_service.py",
    "backend/tests",
    "scripts",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--backend-python",
        type=str,
        default=str(
            DEFAULT_BACKEND_PYTHON
            if DEFAULT_BACKEND_PYTHON.exists()
            else sys.executable
        ),
        help="Python executable to use for backend checks and scripts.",
    )
    parser.add_argument(
        "--npm",
        type=str,
        default="npm",
        help="npm executable for frontend checks.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(DEFAULT_OUTPUT_DIR),
        help="Output directory for the non-demo evaluation smoke run.",
    )
    parser.add_argument("--num-puzzles", type=int, default=2, help="Smoke batch size.")
    parser.add_argument("--top-k", type=int, default=1, help="Smoke batch top-k size.")
    parser.add_argument(
        "--skip-lint",
        action="store_true",
        help="Skip Ruff lint and format checks.",
    )
    parser.add_argument(
        "--skip-backend-tests",
        action="store_true",
        help="Skip backend pytest validation.",
    )
    parser.add_argument(
        "--skip-frontend",
        action="store_true",
        help="Skip frontend build validation.",
    )
    parser.add_argument(
        "--skip-demo-smoke",
        action="store_true",
        help="Skip the lightweight demo generation smoke command.",
    )
    parser.add_argument(
        "--skip-nondemo-eval",
        action="store_true",
        help="Skip the non-demo batch evaluation smoke command and release-summary build.",
    )
    return parser.parse_args()


def _run_step(
    *,
    step_name: str,
    cmd: list[str],
    cwd: Path = ROOT,
    env: dict[str, str] | None = None,
) -> dict[str, object]:
    print(f"[release-check] {step_name}: {shlex.join(cmd)}")
    completed = subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"{step_name} failed with exit code {completed.returncode}.")
    return {"step": step_name, "command": cmd}


def main() -> None:
    args = parse_args()
    backend_python = args.backend_python
    npm = args.npm
    output_dir = Path(args.output_dir)
    output_dir.parent.mkdir(parents=True, exist_ok=True)

    completed_steps: list[dict[str, object]] = []

    if not args.skip_lint:
        completed_steps.append(
            _run_step(
                step_name="ruff_check",
                cmd=[
                    backend_python,
                    "-m",
                    "ruff",
                    "check",
                    *PYTHON_CHECK_PATHS,
                ],
            )
        )
        completed_steps.append(
            _run_step(
                step_name="ruff_format_check",
                cmd=[
                    backend_python,
                    "-m",
                    "ruff",
                    "format",
                    "--check",
                    *PYTHON_CHECK_PATHS,
                ],
            )
        )

    if not args.skip_backend_tests:
        completed_steps.append(
            _run_step(
                step_name="backend_tests",
                cmd=[backend_python, "-m", "pytest", "backend/tests", "-q"],
            )
        )

    if not args.skip_demo_smoke:
        completed_steps.append(
            _run_step(
                step_name="demo_generation_smoke",
                cmd=[
                    backend_python,
                    "scripts/run_demo_generation.py",
                    "--seed",
                    "17",
                    "--no-trace",
                ],
            )
        )

    if not args.skip_frontend:
        completed_steps.append(
            _run_step(
                step_name="frontend_build",
                cmd=[npm, "run", "build"],
                cwd=ROOT / "frontend",
            )
        )

    artifact_paths: dict[str, str] = {}
    if not args.skip_nondemo_eval:
        nondemo_env = {**os.environ, "CONNECTIONS_DEMO_MODE": "false"}
        completed_steps.append(
            _run_step(
                step_name="nondemo_batch_evaluation",
                cmd=[
                    backend_python,
                    "scripts/evaluate_batch.py",
                    "--num-puzzles",
                    str(args.num_puzzles),
                    "--top-k",
                    str(args.top_k),
                    "--output-dir",
                    str(output_dir),
                    "--no-traces",
                    "--no-demo-mode",
                ],
                env=nondemo_env,
            )
        )
        completed_steps.append(
            _run_step(
                step_name="build_release_summary",
                cmd=[
                    backend_python,
                    "scripts/build_release_summary.py",
                    "--run-dir",
                    str(output_dir),
                ],
                env=nondemo_env,
            )
        )

        expected_paths = [
            output_dir / "summary.json",
            output_dir / "top_k.json",
            output_dir / "calibration_summary.json",
            output_dir / "release_summary.json",
            output_dir / "release_summary.md",
        ]
        missing = [str(path) for path in expected_paths if not path.exists()]
        if missing:
            raise RuntimeError(
                "Release validation finished but expected artifacts were missing: "
                + ", ".join(missing)
            )
        artifact_paths = {path.name: str(path) for path in expected_paths}

    print(
        json.dumps(
            {
                "status": "ok",
                "output_dir": str(output_dir),
                "completed_steps": completed_steps,
                "artifacts": artifact_paths,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
