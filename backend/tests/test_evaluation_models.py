"""Validation tests for evaluation and debug scaffolding models."""

from __future__ import annotations

from app.schemas.evaluation_models import (
    AmbiguityEvidence,
    AmbiguityReport,
    AmbiguityRiskLevel,
    BatchEvaluationConfig,
    ScoreBreakdownView,
)


def test_ambiguity_report_serializes_with_placeholder_evidence() -> None:
    report = AmbiguityReport(
        evaluator_name="baseline_ambiguity_evaluator",
        risk_level=AmbiguityRiskLevel.MEDIUM,
        penalty_hint=0.25,
        reject_recommended=False,
        summary="Placeholder ambiguity report.",
        evidence=AmbiguityEvidence(triggered_flags=["alternative_groupings_detected"]),
    )
    payload = report.model_dump(mode="json")
    assert payload["risk_level"] == "medium"
    assert payload["evidence"]["triggered_flags"] == ["alternative_groupings_detected"]


def test_batch_evaluation_config_defaults_are_stable() -> None:
    config = BatchEvaluationConfig()
    assert config.num_puzzles == 10
    assert config.top_k_size == 5
    assert config.demo_mode is True


def test_score_breakdown_view_captures_components() -> None:
    breakdown = ScoreBreakdownView(
        overall=0.8,
        coherence=0.9,
        ambiguity_penalty=0.1,
        human_likeness=0.4,
        components={"baseline_style_placeholder": 0.4},
    )
    assert breakdown.components["baseline_style_placeholder"] == 0.4
