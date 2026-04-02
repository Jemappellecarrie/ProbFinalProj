#!/usr/bin/env python3
# ruff: noqa: E402
"""Build a human-readable release summary bundle from one evaluation run."""

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

EXPECTED_ARTIFACTS = [
    "config.json",
    "summary.json",
    "accepted.json",
    "rejected.json",
    "top_k.json",
    "calibration_summary.json",
    "style_summary.json",
    "mechanism_mix_summary.json",
    "threshold_diagnostics.json",
    "traces.json",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-dir",
        type=str,
        default=None,
        help="Evaluation run directory. Defaults to the latest run under data/processed/eval_runs.",
    )
    parser.add_argument(
        "--output-json",
        type=str,
        default="release_summary.json",
        help="Output filename for the machine-readable release summary.",
    )
    parser.add_argument(
        "--output-markdown",
        type=str,
        default="release_summary.md",
        help="Output filename for the human-readable release summary.",
    )
    return parser.parse_args()


def _load_json(path: Path) -> object:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _latest_run_dir(settings: Settings) -> Path:
    run_dirs = [path for path in settings.eval_runs_dir.iterdir() if path.is_dir()]
    if not run_dirs:
        raise FileNotFoundError(
            f"No evaluation runs found under {settings.eval_runs_dir}. Run scripts/evaluate_batch.py first."
        )
    return max(run_dirs, key=lambda path: path.stat().st_mtime)


def _artifact_inventory(run_dir: Path) -> dict[str, dict[str, object]]:
    inventory: dict[str, dict[str, object]] = {}
    for filename in EXPECTED_ARTIFACTS:
        path = run_dir / filename
        inventory[filename] = {
            "path": str(path),
            "present": path.exists(),
        }
    return inventory


def build_release_summary(run_dir: Path) -> dict[str, object]:
    summary = _load_json(run_dir / "summary.json")
    top_k = _load_json(run_dir / "top_k.json")
    accepted = _load_json(run_dir / "accepted.json")
    rejected = _load_json(run_dir / "rejected.json")
    calibration_summary = _load_json(run_dir / "calibration_summary.json")
    threshold_diagnostics = _load_json(run_dir / "threshold_diagnostics.json")

    ranked_puzzles = top_k.get("ranked_puzzles", []) if isinstance(top_k, dict) else []
    diagnostics = (
        threshold_diagnostics if isinstance(threshold_diagnostics, list) else []
    )

    return {
        "run_id": summary["run_id"],
        "source_run_dir": str(run_dir),
        "acceptance": {
            "total_generated": summary["total_generated"],
            "accepted_count": summary["accepted_count"],
            "rejected_count": summary["rejected_count"],
            "acceptance_rate": summary["acceptance_rate"],
        },
        "top_k_overview": [
            {
                "rank": record["rank"],
                "puzzle_id": record["puzzle_id"],
                "verification_decision": record.get("verification_decision"),
                "overall_score": record["score_breakdown"]["overall"],
                "group_labels": record["group_labels"],
                "mechanism_mix_summary": record["mechanism_mix_summary"],
                "style_archetype": record.get("style_archetype"),
                "style_alignment_score": record.get("style_alignment_score"),
            }
            for record in ranked_puzzles[:3]
        ],
        "generator_mix": summary["generator_mix"],
        "calibration": {
            "target_version": calibration_summary["target_version"],
            "accepted_puzzle_count": calibration_summary["accepted"]["puzzle_count"],
            "rejected_puzzle_count": calibration_summary["rejected"]["puzzle_count"],
            "top_k_puzzle_count": calibration_summary["top_k"]["puzzle_count"],
            "threshold_diagnostic_count": len(diagnostics),
            "warning_codes": [
                diagnostic["code"]
                for diagnostic in diagnostics
                if diagnostic.get("severity") == "warning"
            ],
        },
        "artifact_inventory": _artifact_inventory(run_dir),
        "record_counts": {
            "accepted_records": len(accepted) if isinstance(accepted, list) else 0,
            "rejected_records": len(rejected) if isinstance(rejected, list) else 0,
            "top_k_records": len(ranked_puzzles),
        },
        "notes": [
            "Release summary is a deterministic synthesis of persisted evaluation artifacts.",
            "It is intended for grading/demo review and does not replace the raw JSON artifacts.",
        ],
    }


def _markdown_release_summary(report: dict[str, object]) -> str:
    acceptance = report["acceptance"]
    calibration = report["calibration"]
    lines = [
        "# Release Summary",
        "",
        f"- Run ID: `{report['run_id']}`",
        f"- Source Run Dir: `{report['source_run_dir']}`",
        (
            f"- Acceptance: {acceptance['accepted_count']} accepted / "
            f"{acceptance['total_generated']} generated "
            f"({acceptance['acceptance_rate']:.3f} acceptance rate)"
        ),
        f"- Calibration Target: `{calibration['target_version']}`",
        f"- Threshold Diagnostics: {calibration['threshold_diagnostic_count']}",
        "",
        "## Top K",
    ]

    if report["top_k_overview"]:
        for record in report["top_k_overview"]:
            lines.extend(
                [
                    (
                        f"- Rank {record['rank']}: `{record['puzzle_id']}` "
                        f"({record['verification_decision']}, score {record['overall_score']:.4f})"
                    ),
                    f"  Labels: {', '.join(record['group_labels'])}",
                    f"  Mix: {json.dumps(record['mechanism_mix_summary'], sort_keys=True)}",
                    (
                        f"  Style: archetype={record['style_archetype']}, "
                        f"alignment={record['style_alignment_score']}"
                    ),
                ]
            )
    else:
        lines.append("- No ranked puzzles were present in the run.")

    lines.extend(
        [
            "",
            "## Artifacts",
        ]
    )
    for filename, details in report["artifact_inventory"].items():
        status = "present" if details["present"] else "missing"
        lines.append(f"- `{filename}`: {status} (`{details['path']}`)")

    lines.extend(
        [
            "",
            "## Notes",
            "- Release summary is derived from persisted artifacts, not from a second generation pass.",
            "- Raw evaluation JSON remains the source of truth for detailed scoring and trace inspection.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    settings = Settings()
    run_dir = (
        Path(args.run_dir) if args.run_dir is not None else _latest_run_dir(settings)
    )
    if not run_dir.exists():
        raise FileNotFoundError(f"Run directory does not exist: {run_dir}")

    report = build_release_summary(run_dir)
    output_json_path = run_dir / args.output_json
    output_markdown_path = run_dir / args.output_markdown

    with output_json_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    output_markdown_path.write_text(_markdown_release_summary(report), encoding="utf-8")

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
