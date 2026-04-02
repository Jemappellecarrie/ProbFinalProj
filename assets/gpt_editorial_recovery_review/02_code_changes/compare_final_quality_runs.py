#!/usr/bin/env python3
# ruff: noqa: E402
"""Compare two final-quality acceptance runs and emit before/after artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.policy_snapshot import diff_policy_snapshots
from app.scoring.final_quality_comparison import write_before_after_funnel_comparison


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _editorial_recovery_summary(
    *,
    before_funnel: dict,
    after_funnel: dict,
    before_audit: dict,
    after_audit: dict,
    before_run: Path,
    after_run: Path,
) -> dict:
    return {
        "before_run": str(before_run),
        "after_run": str(after_run),
        "before_unique_board_count": before_funnel.get("unique_board_count"),
        "after_unique_board_count": after_funnel.get("unique_board_count"),
        "before_unique_family_count": before_funnel.get("unique_family_count"),
        "after_unique_family_count": after_funnel.get("unique_family_count"),
        "before_top_k_unique_count": before_funnel.get("top_k_unique_count"),
        "after_top_k_unique_count": after_funnel.get("top_k_unique_count"),
        "before_top_k_unique_family_count": before_funnel.get(
            "top_k_unique_family_count"
        ),
        "after_top_k_unique_family_count": after_funnel.get(
            "top_k_unique_family_count"
        ),
        "before_formulaic_board_rate": before_funnel.get("formulaic_board_rate"),
        "after_formulaic_board_rate": after_funnel.get("formulaic_board_rate"),
        "before_repeated_family_rate": before_funnel.get("repeated_family_rate"),
        "after_repeated_family_rate": after_funnel.get("repeated_family_rate"),
        "before_top_editorial_family_share": before_funnel.get(
            "top_editorial_family_share"
        ),
        "after_top_editorial_family_share": after_funnel.get(
            "top_editorial_family_share"
        ),
        "before_generated_top_k_count": before_audit.get("generated_top_k_count"),
        "after_generated_top_k_count": after_audit.get("generated_top_k_count"),
        "before_accepted_high_confidence": before_audit.get("accepted_high_confidence"),
        "after_accepted_high_confidence": after_audit.get("accepted_high_confidence"),
        "before_accepted_borderline": before_audit.get("accepted_borderline"),
        "after_accepted_borderline": after_audit.get("accepted_borderline"),
        "top_k_still_single_family_dominated": (
            float(after_funnel.get("top_editorial_family_share", 0.0) or 0.0) >= 0.5
        ),
    }


def _editorial_recovery_markdown(summary: dict) -> str:
    lines = [
        "# Before/After Editorial Recovery Summary",
        "",
        f"- before_run: `{summary['before_run']}`",
        f"- after_run: `{summary['after_run']}`",
        f"- unique_board_count: {summary['before_unique_board_count']} -> {summary['after_unique_board_count']}",
        f"- unique_family_count: {summary['before_unique_family_count']} -> {summary['after_unique_family_count']}",
        f"- top_k_unique_count: {summary['before_top_k_unique_count']} -> {summary['after_top_k_unique_count']}",
        (
            "- top_k_unique_family_count: "
            f"{summary['before_top_k_unique_family_count']} -> {summary['after_top_k_unique_family_count']}"
        ),
        (
            "- formulaic_board_rate: "
            f"{summary['before_formulaic_board_rate']} -> {summary['after_formulaic_board_rate']}"
        ),
        (
            "- repeated_family_rate: "
            f"{summary['before_repeated_family_rate']} -> {summary['after_repeated_family_rate']}"
        ),
        (
            "- top_editorial_family_share: "
            f"{summary['before_top_editorial_family_share']} -> {summary['after_top_editorial_family_share']}"
        ),
        (
            "- generated_top_k_count: "
            f"{summary['before_generated_top_k_count']} -> {summary['after_generated_top_k_count']}"
        ),
        (
            "- accepted_high_confidence: "
            f"{summary['before_accepted_high_confidence']} -> {summary['after_accepted_high_confidence']}"
        ),
        (
            "- accepted_borderline: "
            f"{summary['before_accepted_borderline']} -> {summary['after_accepted_borderline']}"
        ),
        (
            "- top_k_still_single_family_dominated: "
            f"{summary['top_k_still_single_family_dominated']}"
        ),
    ]
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before-run", type=Path, required=True)
    parser.add_argument("--after-run", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    before_funnel = _load_json(args.before_run / "funnel_report.json")
    after_funnel = _load_json(args.after_run / "funnel_report.json")
    before_policy = _load_json(args.before_run / "policy_snapshot.json")
    after_policy = _load_json(args.after_run / "policy_snapshot.json")
    before_audit = _load_json(args.before_run / "quality_audit_report.json")
    after_audit = _load_json(args.after_run / "quality_audit_report.json")

    write_before_after_funnel_comparison(
        before_report=before_funnel,
        after_report=after_funnel,
        output_json=args.output_dir / "before_after_funnel_comparison.json",
        output_markdown=args.output_dir / "before_after_funnel_comparison.md",
    )
    calibration_diff = diff_policy_snapshots(before_policy, after_policy)
    (args.output_dir / "calibration_diff.json").write_text(
        json.dumps(calibration_diff, indent=2),
        encoding="utf-8",
    )
    calibration_summary = {
        "before_run": str(args.before_run),
        "after_run": str(args.after_run),
        "policy_changed": calibration_diff["changed"],
        "policy_changes": calibration_diff["changes"],
        "before_top_k_unique_count": before_funnel.get("top_k_unique_count"),
        "after_top_k_unique_count": after_funnel.get("top_k_unique_count"),
        "before_generated_top_k_count": before_audit.get("generated_top_k_count"),
        "after_generated_top_k_count": after_audit.get("generated_top_k_count"),
    }
    (args.output_dir / "calibration_before_after_summary.json").write_text(
        json.dumps(calibration_summary, indent=2),
        encoding="utf-8",
    )
    (args.output_dir / "calibration_pass_notes.md").write_text(
        "\n".join(
            [
                "# Calibration Pass Notes",
                "",
                "- This summary compares the persisted pre-calibration and post-calibration run artifacts.",
                "- The JSON diff is limited to changed policy knobs only.",
                "- Use the funnel comparison to verify whether unique top-board yield improved.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    editorial_summary = _editorial_recovery_summary(
        before_funnel=before_funnel,
        after_funnel=after_funnel,
        before_audit=before_audit,
        after_audit=after_audit,
        before_run=args.before_run,
        after_run=args.after_run,
    )
    (args.output_dir / "before_after_editorial_recovery_summary.json").write_text(
        json.dumps(editorial_summary, indent=2),
        encoding="utf-8",
    )
    (args.output_dir / "before_after_editorial_recovery_summary.md").write_text(
        _editorial_recovery_markdown(editorial_summary),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "output_dir": str(args.output_dir),
                "funnel_comparison": str(
                    args.output_dir / "before_after_funnel_comparison.json"
                ),
                "calibration_diff": str(args.output_dir / "calibration_diff.json"),
                "calibration_summary": str(
                    args.output_dir / "calibration_before_after_summary.json"
                ),
                "editorial_recovery_summary": str(
                    args.output_dir / "before_after_editorial_recovery_summary.json"
                ),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
