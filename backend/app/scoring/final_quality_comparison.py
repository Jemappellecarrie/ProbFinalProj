"""Comparison helpers for final-quality acceptance artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

COMPARISON_KEYS = [
    "total_puzzle_candidates_seen",
    "structurally_valid_count",
    "structurally_invalid_count",
    "unique_board_count",
    "unique_family_count",
    "selected_unique_board_count",
    "top_k_unique_count",
    "top_k_unique_family_count",
    "accepted_count",
    "borderline_count",
    "rejected_count",
    "repeated_theme_family_count",
    "repeated_surface_wordplay_family_count",
    "formulaic_board_rate",
    "repeated_family_rate",
    "top_editorial_family_share",
]


def build_before_after_funnel_comparison(
    before: dict[str, Any],
    after: dict[str, Any],
) -> dict[str, Any]:
    """Return a compact before/after comparison over the core funnel metrics."""

    metrics: dict[str, dict[str, int | float | None]] = {}
    for key in COMPARISON_KEYS:
        before_value = before.get(key)
        after_value = after.get(key)
        delta = None
        if isinstance(before_value, (int, float)) and isinstance(after_value, (int, float)):
            delta = after_value - before_value
        metrics[key] = {"before": before_value, "after": after_value, "delta": delta}
    changed = any(item["delta"] not in {0, None} for item in metrics.values())
    return {"changed": changed, "metrics": metrics}


def before_after_funnel_markdown(comparison: dict[str, Any]) -> str:
    """Render a compact markdown summary for the funnel comparison."""

    lines = ["# Before/After Funnel Comparison", ""]
    for key, payload in comparison["metrics"].items():
        lines.append(
            f"- {key}: before={payload['before']} after={payload['after']} delta={payload['delta']}"
        )
    return "\n".join(lines) + "\n"


def write_before_after_funnel_comparison(
    *,
    before_report: dict[str, Any],
    after_report: dict[str, Any],
    output_json: Path,
    output_markdown: Path,
) -> dict[str, Any]:
    """Build and persist the before/after funnel comparison."""

    comparison = build_before_after_funnel_comparison(before_report, after_report)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(comparison, indent=2), encoding="utf-8")
    output_markdown.write_text(before_after_funnel_markdown(comparison), encoding="utf-8")
    return comparison
