"""Reusable Stage 3 calibration helpers.

These helpers load the local style target bands, compare observed metrics
against them, and aggregate batch-evaluation slices into reproducible
machine-readable summaries.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterable, Sequence
from functools import lru_cache
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

from app.schemas.evaluation_models import (
    AcceptedPuzzleRecord,
    BatchSliceCalibrationSummary,
    CalibrationSummary,
    RejectedPuzzleRecord,
    StyleMetricComparison,
    ThresholdDiagnostic,
)

REFERENCE_STYLE_TARGETS_PATH = (
    Path(__file__).resolve().parents[3] / "data" / "reference" / "style_targets_v1.json"
)


@lru_cache(maxsize=8)
def _load_reference_payload(reference_path: str) -> dict[str, Any]:
    with Path(reference_path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_style_targets(reference_path: Path | None = None) -> dict[str, Any]:
    """Return the parsed Stage 3 style target payload."""

    path = reference_path or REFERENCE_STYLE_TARGETS_PATH
    return _load_reference_payload(str(path))


def compare_value_to_band(
    metric_name: str,
    actual_value: float,
    band: dict[str, Any],
) -> StyleMetricComparison:
    """Compare one observed value to an explicit target band."""

    target_min = band.get("min")
    target_max = band.get("max")
    description = str(band.get("description", "")).strip()
    if target_min is not None and actual_value < float(target_min):
        drift = "low"
        within_band = False
    elif target_max is not None and actual_value > float(target_max):
        drift = "high"
        within_band = False
    else:
        drift = "within_band"
        within_band = True

    explanation = description or f"Compared {metric_name} against the Stage 3 target band."
    return StyleMetricComparison(
        metric_name=metric_name,
        actual_value=round(actual_value, 4),
        target_min=float(target_min) if target_min is not None else None,
        target_max=float(target_max) if target_max is not None else None,
        within_band=within_band,
        drift=drift,
        explanation=explanation,
    )


def compare_metric_dict_to_targets(
    metrics: dict[str, float],
    target_bands: dict[str, Any],
    *,
    prefix: str = "",
) -> list[StyleMetricComparison]:
    """Compare a dictionary of observed metrics to explicit target bands."""

    comparisons: list[StyleMetricComparison] = []
    for metric_name, band in sorted(target_bands.items()):
        if metric_name not in metrics:
            continue
        scoped_name = f"{prefix}{metric_name}" if prefix else metric_name
        comparisons.append(compare_value_to_band(scoped_name, float(metrics[metric_name]), band))
    return comparisons


def _average_dict(values: Sequence[dict[str, float]]) -> dict[str, float]:
    if not values:
        return {}

    keys = sorted({key for value in values for key in value})
    return {key: round(mean(float(value.get(key, 0.0)) for value in values), 4) for key in keys}


def _label_shape_summary(
    records: Sequence[AcceptedPuzzleRecord | RejectedPuzzleRecord],
) -> dict[str, float]:
    token_counts = [
        float(len(label.split())) for record in records for label in record.group_labels
    ]
    if not token_counts:
        return {
            "label_token_mean": 0.0,
            "label_token_std": 0.0,
        }
    return {
        "label_token_mean": round(mean(token_counts), 4),
        "label_token_std": round(pstdev(token_counts), 4) if len(token_counts) > 1 else 0.0,
    }


def _style_metric_payload(record: AcceptedPuzzleRecord | RejectedPuzzleRecord) -> dict[str, float]:
    style_analysis = record.style_analysis
    if style_analysis is None or style_analysis.board_style_summary is None:
        return {}
    metrics = dict(style_analysis.board_style_summary.metrics)
    metrics["style_alignment_score"] = style_analysis.board_style_summary.style_alignment_score
    metrics["label_token_mean"] = style_analysis.board_style_summary.label_token_mean
    metrics["label_token_std"] = style_analysis.board_style_summary.label_token_std
    metrics["evidence_interpretability"] = (
        style_analysis.board_style_summary.evidence_interpretability
    )
    metrics["semantic_wordplay_balance"] = (
        style_analysis.board_style_summary.semantic_wordplay_balance
    )
    metrics["coherence_trickiness_balance"] = (
        style_analysis.board_style_summary.coherence_trickiness_balance
    )
    metrics["redundancy_score"] = style_analysis.board_style_summary.redundancy_score
    return {key: round(float(value), 4) for key, value in metrics.items()}


def _board_diversity_payload(
    record: AcceptedPuzzleRecord | RejectedPuzzleRecord,
) -> dict[str, float]:
    style_analysis = record.style_analysis
    if style_analysis is not None and style_analysis.mechanism_mix_profile is not None:
        return {
            "unique_group_type_count": float(
                style_analysis.mechanism_mix_profile.unique_group_type_count
            ),
            "semantic_group_count": float(
                style_analysis.mechanism_mix_profile.semantic_group_count
            ),
            "theme_group_count": float(style_analysis.mechanism_mix_profile.theme_group_count),
            "phonetic_group_count": float(
                style_analysis.mechanism_mix_profile.phonetic_group_count
            ),
            "wordplay_group_count": float(
                style_analysis.mechanism_mix_profile.wordplay_group_count
            ),
        }

    mechanism_mix_summary = record.mechanism_mix_summary
    wordplay_count = mechanism_mix_summary.get("lexical", 0) + mechanism_mix_summary.get(
        "phonetic", 0
    )
    return {
        "unique_group_type_count": float(len(mechanism_mix_summary)),
        "semantic_group_count": float(mechanism_mix_summary.get("semantic", 0)),
        "theme_group_count": float(mechanism_mix_summary.get("theme", 0)),
        "phonetic_group_count": float(mechanism_mix_summary.get("phonetic", 0)),
        "wordplay_group_count": float(wordplay_count),
    }


def build_batch_slice_summary(
    records: Sequence[AcceptedPuzzleRecord | RejectedPuzzleRecord],
    *,
    slice_name: str,
) -> BatchSliceCalibrationSummary:
    """Aggregate one evaluation slice into stable calibration statistics."""

    mechanism_mix_counts = Counter(
        group_type for record in records for group_type in record.group_types
    )
    board_type_signature_counts = Counter(
        "+".join(sorted(record.mechanism_mix_summary)) for record in records
    )
    decision_counts = Counter(record.verification_decision or "unknown" for record in records)
    board_diversity_values = [_board_diversity_payload(record) for record in records]
    style_metric_values = [_style_metric_payload(record) for record in records]
    scorer_component_values = [record.score_breakdown.components for record in records]
    board_archetype_counts = Counter(
        (
            record.style_analysis.board_style_summary.board_archetype
            if record.style_analysis is not None
            and record.style_analysis.board_style_summary is not None
            else "unknown"
        )
        for record in records
    )
    out_of_band_flag_counts = Counter(
        flag
        for record in records
        for flag in (
            record.style_analysis.out_of_band_flags if record.style_analysis is not None else []
        )
    )
    ambiguity_values = [float(record.score_breakdown.ambiguity_penalty) for record in records]

    group_type_counts_per_board = [
        {
            group_type: float(record.mechanism_mix_summary.get(group_type, 0))
            for group_type in sorted(mechanism_mix_counts)
        }
        for record in records
    ]

    return BatchSliceCalibrationSummary(
        slice_name=slice_name,
        puzzle_count=len(records),
        verification_decision_counts=dict(sorted(decision_counts.items())),
        mechanism_mix_counts=dict(sorted(mechanism_mix_counts.items())),
        average_group_type_counts=_average_dict(group_type_counts_per_board),
        board_type_signature_counts=dict(sorted(board_type_signature_counts.items())),
        mixed_board_rate=round(
            mean(1.0 if record.mixed_board else 0.0 for record in records),
            4,
        )
        if records
        else 0.0,
        ambiguity_metrics={
            "ambiguity_score": round(mean(ambiguity_values), 4) if ambiguity_values else 0.0,
        },
        scorer_component_averages=_average_dict(scorer_component_values),
        label_shape_summary=_label_shape_summary(records),
        board_diversity_summary=_average_dict(board_diversity_values),
        style_metric_averages=_average_dict(style_metric_values),
        board_archetype_counts=dict(sorted(board_archetype_counts.items())),
        out_of_band_flag_counts=dict(sorted(out_of_band_flag_counts.items())),
        notes=[
            f"Stage 3 calibration slice built from {slice_name} records.",
        ],
    )


def _distribution_comparisons(
    slice_name: str,
    counts: dict[str, int],
    targets: dict[str, Any],
    *,
    prefix: str,
) -> list[StyleMetricComparison]:
    total = sum(counts.values())
    if total <= 0:
        return []

    comparisons: list[StyleMetricComparison] = []
    for name, band in sorted(targets.items()):
        share = counts.get(name, 0) / total
        comparisons.append(
            StyleMetricComparison(
                metric_name=f"{slice_name}.{prefix}{name}_share",
                actual_value=round(share, 4),
                target_min=float(band.get("min_share"))
                if band.get("min_share") is not None
                else None,
                target_max=float(band.get("max_share"))
                if band.get("max_share") is not None
                else None,
                within_band=(
                    (band.get("min_share") is None or share >= float(band["min_share"]))
                    and (band.get("max_share") is None or share <= float(band["max_share"]))
                ),
                drift=(
                    "low"
                    if band.get("min_share") is not None and share < float(band["min_share"])
                    else (
                        "high"
                        if band.get("max_share") is not None and share > float(band["max_share"])
                        else "within_band"
                    )
                ),
                explanation=(
                    f"Compared {name} share in {slice_name} against the "
                    "Stage 3 distribution target."
                ),
            )
        )
    return comparisons


def _diagnostics_from_comparisons(
    comparisons: Iterable[StyleMetricComparison],
) -> list[ThresholdDiagnostic]:
    diagnostics: list[ThresholdDiagnostic] = []
    for comparison in comparisons:
        if comparison.within_band:
            continue
        diagnostics.append(
            ThresholdDiagnostic(
                code=f"{comparison.metric_name.replace('.', '_')}_{comparison.drift}",
                severity="warning",
                message=(
                    f"{comparison.metric_name} drifted {comparison.drift} relative to the "
                    "Stage 3 reference band."
                ),
                metric_name=comparison.metric_name,
                actual_value=comparison.actual_value,
                target_min=comparison.target_min,
                target_max=comparison.target_max,
            )
        )
    return diagnostics


def build_batch_calibration_summary(
    *,
    accepted_records: Sequence[AcceptedPuzzleRecord],
    rejected_records: Sequence[RejectedPuzzleRecord],
    top_k_records: Sequence[AcceptedPuzzleRecord],
    reference_path: Path | None = None,
) -> CalibrationSummary:
    """Build the Stage 3 batch calibration summary."""

    targets = load_style_targets(reference_path)
    accepted_summary = build_batch_slice_summary(accepted_records, slice_name="accepted")
    rejected_summary = build_batch_slice_summary(rejected_records, slice_name="rejected")
    top_k_summary = build_batch_slice_summary(top_k_records, slice_name="top_k")

    target_comparison: list[StyleMetricComparison] = []
    board_metric_targets = targets.get("board_metrics", {})
    for slice_name, summary in (
        ("accepted", accepted_summary),
        ("rejected", rejected_summary),
        ("top_k", top_k_summary),
    ):
        metric_source = {
            **summary.board_diversity_summary,
            **summary.label_shape_summary,
            **summary.style_metric_averages,
            **summary.ambiguity_metrics,
        }
        target_comparison.extend(
            compare_metric_dict_to_targets(
                metric_source,
                board_metric_targets,
                prefix=f"{slice_name}.",
            )
        )

    distribution_targets = targets.get("distribution_targets", {})
    mechanism_targets = distribution_targets.get("group_mechanisms", {})
    archetype_targets = distribution_targets.get("board_archetypes", {})
    for slice_name, summary in (
        ("accepted", accepted_summary),
        ("rejected", rejected_summary),
        ("top_k", top_k_summary),
    ):
        target_comparison.extend(
            _distribution_comparisons(
                slice_name,
                summary.mechanism_mix_counts,
                mechanism_targets,
                prefix="mechanism_",
            )
        )
        target_comparison.extend(
            _distribution_comparisons(
                slice_name,
                summary.board_archetype_counts,
                archetype_targets,
                prefix="archetype_",
            )
        )

    threshold_diagnostics = _diagnostics_from_comparisons(target_comparison)
    return CalibrationSummary(
        target_version=str(targets.get("version", "unknown")),
        accepted=accepted_summary,
        rejected=rejected_summary,
        top_k=top_k_summary,
        target_comparison=target_comparison,
        threshold_diagnostics=threshold_diagnostics,
        notes=[
            (
                "Stage 3 calibration summary compares batch slices against "
                "explicit local target bands."
            ),
            "These comparisons are intended for offline review, not hidden optimization.",
        ],
    )


def build_calibration_artifact_payloads(
    calibration_summary: CalibrationSummary,
) -> dict[str, object]:
    """Return the machine-readable Stage 3 artifact payloads."""

    style_summary = {
        "target_version": calibration_summary.target_version,
        "accepted": {
            "style_metric_averages": calibration_summary.accepted.style_metric_averages,
            "board_archetype_counts": calibration_summary.accepted.board_archetype_counts,
            "out_of_band_flag_counts": calibration_summary.accepted.out_of_band_flag_counts,
        },
        "rejected": {
            "style_metric_averages": calibration_summary.rejected.style_metric_averages,
            "board_archetype_counts": calibration_summary.rejected.board_archetype_counts,
            "out_of_band_flag_counts": calibration_summary.rejected.out_of_band_flag_counts,
        },
        "top_k": {
            "style_metric_averages": calibration_summary.top_k.style_metric_averages,
            "board_archetype_counts": calibration_summary.top_k.board_archetype_counts,
            "out_of_band_flag_counts": calibration_summary.top_k.out_of_band_flag_counts,
        },
    }
    mechanism_mix_summary = {
        "target_version": calibration_summary.target_version,
        "accepted": {
            "mechanism_mix_counts": calibration_summary.accepted.mechanism_mix_counts,
            "average_group_type_counts": calibration_summary.accepted.average_group_type_counts,
            "board_type_signature_counts": calibration_summary.accepted.board_type_signature_counts,
        },
        "rejected": {
            "mechanism_mix_counts": calibration_summary.rejected.mechanism_mix_counts,
            "average_group_type_counts": calibration_summary.rejected.average_group_type_counts,
            "board_type_signature_counts": calibration_summary.rejected.board_type_signature_counts,
        },
        "top_k": {
            "mechanism_mix_counts": calibration_summary.top_k.mechanism_mix_counts,
            "average_group_type_counts": calibration_summary.top_k.average_group_type_counts,
            "board_type_signature_counts": calibration_summary.top_k.board_type_signature_counts,
        },
    }
    threshold_diagnostics = [
        item.model_dump(mode="json") for item in calibration_summary.threshold_diagnostics
    ]
    return {
        "calibration_summary": calibration_summary.model_dump(mode="json"),
        "style_summary": style_summary,
        "mechanism_mix_summary": mechanism_mix_summary,
        "threshold_diagnostics": threshold_diagnostics,
    }
