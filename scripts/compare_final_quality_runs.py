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


CORE_STYLE_DELTA_KEYS = [
    "style_alignment_score",
    "human_likeness_mean",
    "semantic_group_count",
    "unique_group_type_count",
    "wordplay_group_count",
    "theme_group_count",
    "phonetic_group_count",
    "surface_wordplay_score",
    "surface_wordplay_group_count",
    "formulaic_mix_score",
    "family_saturation",
    "family_repetition_risk",
]


def _generated_quality_buckets(audit: dict) -> dict[str, int]:
    return dict(audit.get("generated_quality_buckets", {}))


def _style_delta_subset(audit: dict) -> dict[str, dict]:
    sections = dict(audit.get("comparison_sections", {}))
    deltas = dict(sections.get("generated_vs_benchmark_style_delta_summary", {}))
    return {key: deltas.get(key, {}) for key in CORE_STYLE_DELTA_KEYS if key in deltas}


def _top_k_formulaic_dominated(funnel: dict) -> bool:
    return (
        float(funnel.get("top_editorial_family_share", 0.0) or 0.0) >= 0.5
        or float(funnel.get("balanced_mixed_board_rate", 0.0) or 0.0) >= 0.5
    )


def _editorial_recovery_summary(
    *,
    before_funnel: dict,
    after_funnel: dict,
    before_audit: dict,
    after_audit: dict,
    before_run: Path,
    after_run: Path,
) -> dict:
    before_quality = _generated_quality_buckets(before_audit)
    after_quality = _generated_quality_buckets(after_audit)
    return {
        "before_run": str(before_run),
        "after_run": str(after_run),
        "before_unique_board_count": before_funnel.get("unique_board_count"),
        "after_unique_board_count": after_funnel.get("unique_board_count"),
        "before_unique_family_count": before_funnel.get("unique_family_count"),
        "after_unique_family_count": after_funnel.get("unique_family_count"),
        "before_top_k_unique_count": before_funnel.get("top_k_unique_count"),
        "after_top_k_unique_count": after_funnel.get("top_k_unique_count"),
        "before_selected_unique_board_count": before_funnel.get("selected_unique_board_count"),
        "after_selected_unique_board_count": after_funnel.get("selected_unique_board_count"),
        "before_selected_unique_family_count": before_funnel.get("selected_unique_family_count"),
        "after_selected_unique_family_count": after_funnel.get("selected_unique_family_count"),
        "before_top_k_unique_family_count": before_funnel.get(
            "top_k_unique_family_count"
        ),
        "after_top_k_unique_family_count": after_funnel.get(
            "top_k_unique_family_count"
        ),
        "before_formulaic_board_rate": before_funnel.get("formulaic_board_rate"),
        "after_formulaic_board_rate": after_funnel.get("formulaic_board_rate"),
        "before_semantic_majority_board_rate": before_funnel.get("semantic_majority_board_rate"),
        "after_semantic_majority_board_rate": after_funnel.get("semantic_majority_board_rate"),
        "before_balanced_mixed_board_rate": before_funnel.get("balanced_mixed_board_rate"),
        "after_balanced_mixed_board_rate": after_funnel.get("balanced_mixed_board_rate"),
        "before_semantic_majority_winner_rate": before_funnel.get("semantic_majority_winner_rate"),
        "after_semantic_majority_winner_rate": after_funnel.get("semantic_majority_winner_rate"),
        "before_balanced_mixed_winner_rate": before_funnel.get("balanced_mixed_winner_rate"),
        "after_balanced_mixed_winner_rate": after_funnel.get("balanced_mixed_winner_rate"),
        "before_surface_wordplay_board_rate": before_funnel.get("surface_wordplay_board_rate"),
        "after_surface_wordplay_board_rate": after_funnel.get("surface_wordplay_board_rate"),
        "before_winner_surface_wordplay_rate": before_funnel.get("winner_surface_wordplay_rate"),
        "after_winner_surface_wordplay_rate": after_funnel.get("winner_surface_wordplay_rate"),
        "before_winner_semantic_group_count_mean": before_funnel.get(
            "winner_semantic_group_count_mean"
        ),
        "after_winner_semantic_group_count_mean": after_funnel.get(
            "winner_semantic_group_count_mean"
        ),
        "before_microtheme_plus_wordplay_cooccurrence_rate": before_funnel.get(
            "microtheme_plus_wordplay_cooccurrence_rate"
        ),
        "after_microtheme_plus_wordplay_cooccurrence_rate": after_funnel.get(
            "microtheme_plus_wordplay_cooccurrence_rate"
        ),
        "before_repeated_family_rate": before_funnel.get("repeated_family_rate"),
        "after_repeated_family_rate": after_funnel.get("repeated_family_rate"),
        "before_repeated_surface_wordplay_family_count": before_funnel.get(
            "repeated_surface_wordplay_family_count"
        ),
        "after_repeated_surface_wordplay_family_count": after_funnel.get(
            "repeated_surface_wordplay_family_count"
        ),
        "before_repeated_theme_family_count": before_funnel.get(
            "repeated_theme_family_count"
        ),
        "after_repeated_theme_family_count": after_funnel.get("repeated_theme_family_count"),
        "before_top_editorial_family_share": before_funnel.get(
            "top_editorial_family_share"
        ),
        "after_top_editorial_family_share": after_funnel.get(
            "top_editorial_family_share"
        ),
        "before_winner_family_repetition_rate": before_funnel.get("winner_family_repetition_rate"),
        "after_winner_family_repetition_rate": after_funnel.get("winner_family_repetition_rate"),
        "before_generated_top_k_count": before_audit.get("generated_top_k_count"),
        "after_generated_top_k_count": after_audit.get("generated_top_k_count"),
        "before_generated_quality_buckets": before_quality,
        "after_generated_quality_buckets": after_quality,
        "repeated_family_rate_reduction": (
            round(
                float(before_funnel.get("repeated_family_rate", 0.0) or 0.0)
                - float(after_funnel.get("repeated_family_rate", 0.0) or 0.0),
                4,
            )
        ),
        "before_style_metric_deltas_vs_benchmark": _style_delta_subset(before_audit),
        "after_style_metric_deltas_vs_benchmark": _style_delta_subset(after_audit),
        "before_style_metric_inflation_flags": before_audit.get(
            "comparison_sections", {}
        ).get("style_metric_inflation_flags", []),
        "after_style_metric_inflation_flags": after_audit.get(
            "comparison_sections", {}
        ).get("style_metric_inflation_flags", []),
        "before_benchmark_anchor_warnings": before_audit.get("comparison_sections", {}).get(
            "benchmark_anchor_warnings",
            [],
        ),
        "after_benchmark_anchor_warnings": after_audit.get("comparison_sections", {}).get(
            "benchmark_anchor_warnings",
            [],
        ),
        "top_k_still_single_family_dominated": _top_k_formulaic_dominated(after_funnel),
    }


def _editorial_recovery_markdown(summary: dict) -> str:
    lines = [
        "# Before/After Editorial Polish Summary",
        "",
        f"- before_run: `{summary['before_run']}`",
        f"- after_run: `{summary['after_run']}`",
        f"- unique_board_count: {summary['before_unique_board_count']} -> {summary['after_unique_board_count']}",
        f"- unique_family_count: {summary['before_unique_family_count']} -> {summary['after_unique_family_count']}",
        (
            "- selected_unique_board_count: "
            f"{summary['before_selected_unique_board_count']} -> {summary['after_selected_unique_board_count']}"
        ),
        (
            "- selected_unique_family_count: "
            f"{summary['before_selected_unique_family_count']} -> {summary['after_selected_unique_family_count']}"
        ),
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
            "- semantic_majority_board_rate: "
            f"{summary['before_semantic_majority_board_rate']} -> "
            f"{summary['after_semantic_majority_board_rate']}"
        ),
        (
            "- balanced_mixed_board_rate: "
            f"{summary['before_balanced_mixed_board_rate']} -> "
            f"{summary['after_balanced_mixed_board_rate']}"
        ),
        (
            "- semantic_majority_winner_rate: "
            f"{summary['before_semantic_majority_winner_rate']} -> "
            f"{summary['after_semantic_majority_winner_rate']}"
        ),
        (
            "- balanced_mixed_winner_rate: "
            f"{summary['before_balanced_mixed_winner_rate']} -> "
            f"{summary['after_balanced_mixed_winner_rate']}"
        ),
        (
            "- surface_wordplay_board_rate: "
            f"{summary['before_surface_wordplay_board_rate']} -> "
            f"{summary['after_surface_wordplay_board_rate']}"
        ),
        (
            "- winner_surface_wordplay_rate: "
            f"{summary['before_winner_surface_wordplay_rate']} -> "
            f"{summary['after_winner_surface_wordplay_rate']}"
        ),
        (
            "- winner_semantic_group_count_mean: "
            f"{summary['before_winner_semantic_group_count_mean']} -> "
            f"{summary['after_winner_semantic_group_count_mean']}"
        ),
        (
            "- microtheme_plus_wordplay_cooccurrence_rate: "
            f"{summary['before_microtheme_plus_wordplay_cooccurrence_rate']} -> "
            f"{summary['after_microtheme_plus_wordplay_cooccurrence_rate']}"
        ),
        (
            "- repeated_family_rate: "
            f"{summary['before_repeated_family_rate']} -> {summary['after_repeated_family_rate']}"
        ),
        (
            "- repeated_family_rate_reduction: "
            f"{summary['repeated_family_rate_reduction']}"
        ),
        (
            "- repeated_surface_wordplay_family_count: "
            f"{summary['before_repeated_surface_wordplay_family_count']} -> "
            f"{summary['after_repeated_surface_wordplay_family_count']}"
        ),
        (
            "- repeated_theme_family_count: "
            f"{summary['before_repeated_theme_family_count']} -> "
            f"{summary['after_repeated_theme_family_count']}"
        ),
        (
            "- top_editorial_family_share: "
            f"{summary['before_top_editorial_family_share']} -> {summary['after_top_editorial_family_share']}"
        ),
        (
            "- winner_family_repetition_rate: "
            f"{summary['before_winner_family_repetition_rate']} -> "
            f"{summary['after_winner_family_repetition_rate']}"
        ),
        (
            "- generated_top_k_count: "
            f"{summary['before_generated_top_k_count']} -> {summary['after_generated_top_k_count']}"
        ),
        (
            "- generated_quality_buckets: "
            f"{json.dumps(summary['before_generated_quality_buckets'], sort_keys=True)} -> "
            f"{json.dumps(summary['after_generated_quality_buckets'], sort_keys=True)}"
        ),
        (
            "- post-run inflation_flag_count: "
            f"{len(summary['after_style_metric_inflation_flags'])}"
        ),
        (
            "- post-run benchmark_anchor_warning_count: "
            f"{len(summary['after_benchmark_anchor_warnings'])}"
        ),
        (
            "- top_k_still_single_family_dominated: "
            f"{summary['top_k_still_single_family_dominated']}"
        ),
    ]
    style_deltas = summary.get("after_style_metric_deltas_vs_benchmark", {})
    if style_deltas:
        lines.extend(["", "## After vs Benchmark Style Deltas"])
        for key, payload in style_deltas.items():
            lines.append(
                "- "
                f"{key}: generated={payload.get('generated')} "
                f"benchmark={payload.get('benchmark')} "
                f"delta={payload.get('absolute_delta')}"
            )
    warnings = summary.get("after_benchmark_anchor_warnings", [])
    if warnings:
        lines.extend(["", "## Benchmark Anchor Warnings"])
        lines.extend(f"- {warning}" for warning in warnings)
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
    editorial_summary_json = json.dumps(editorial_summary, indent=2)
    editorial_summary_markdown = _editorial_recovery_markdown(editorial_summary)
    (args.output_dir / "before_after_editorial_recovery_summary.json").write_text(
        editorial_summary_json,
        encoding="utf-8",
    )
    (args.output_dir / "before_after_editorial_recovery_summary.md").write_text(
        editorial_summary_markdown,
        encoding="utf-8",
    )
    (args.output_dir / "before_after_editorial_recovery_v2_summary.json").write_text(
        editorial_summary_json,
        encoding="utf-8",
    )
    (args.output_dir / "before_after_editorial_recovery_v2_summary.md").write_text(
        editorial_summary_markdown,
        encoding="utf-8",
    )
    (args.output_dir / "before_after_editorial_polish_v3_summary.json").write_text(
        editorial_summary_json,
        encoding="utf-8",
    )
    (args.output_dir / "before_after_editorial_polish_v3_summary.md").write_text(
        editorial_summary_markdown,
        encoding="utf-8",
    )
    (args.output_dir / "before_after_editorial_polish_v4_summary.json").write_text(
        editorial_summary_json,
        encoding="utf-8",
    )
    (args.output_dir / "before_after_editorial_polish_v4_summary.md").write_text(
        editorial_summary_markdown,
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
                "editorial_recovery_v2_summary": str(
                    args.output_dir / "before_after_editorial_recovery_v2_summary.json"
                ),
                "editorial_polish_v3_summary": str(
                    args.output_dir / "before_after_editorial_polish_v3_summary.json"
                ),
                "editorial_polish_v4_summary": str(
                    args.output_dir / "before_after_editorial_polish_v4_summary.json"
                ),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
