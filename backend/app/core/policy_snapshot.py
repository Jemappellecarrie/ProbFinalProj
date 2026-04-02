"""Helpers for serializing and diffing calibration-policy knobs."""

from __future__ import annotations

from app.core.stage1_quality import stage1_scoring_weight_snapshot, stage1_threshold_snapshot
from app.core.stage2_composer_policy import stage2_composer_policy_snapshot
from app.core.stage3_style_policy import (
    stage3_editorial_selection_snapshot,
    stage3_scoring_weight_snapshot,
    stage3_verifier_threshold_snapshot,
)


def current_policy_snapshot() -> dict[str, dict[str, float | int]]:
    """Return the current policy snapshot across the calibrated layers."""

    return {
        "stage1_thresholds": stage1_threshold_snapshot(),
        "stage1_scoring": stage1_scoring_weight_snapshot(),
        "stage2_composer": stage2_composer_policy_snapshot(),
        "stage3_scoring": stage3_scoring_weight_snapshot(),
        "stage3_verifier": stage3_verifier_threshold_snapshot(),
        "stage3_editorial_selection": stage3_editorial_selection_snapshot(),
    }


def diff_policy_snapshots(
    before: dict[str, dict[str, float | int]],
    after: dict[str, dict[str, float | int]],
) -> dict[str, object]:
    """Return a compact nested diff for changed policy values only."""

    changes: dict[str, dict[str, dict[str, float | int]]] = {}
    for section in sorted(set(before) | set(after)):
        section_before = before.get(section, {})
        section_after = after.get(section, {})
        section_changes: dict[str, dict[str, float | int]] = {}
        for key in sorted(set(section_before) | set(section_after)):
            before_value = section_before.get(key)
            after_value = section_after.get(key)
            if before_value == after_value:
                continue
            section_changes[key] = {"before": before_value, "after": after_value}
        if section_changes:
            changes[section] = section_changes
    return {"changed": bool(changes), "changes": changes}
