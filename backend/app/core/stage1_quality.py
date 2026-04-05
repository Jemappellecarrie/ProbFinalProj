"""Central Stage 1 quality-control thresholds and ranking helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass

STAGE1_SELECTION_POLICY = [
    "verification_decision",
    "scorer_overall",
    "semantic_majority_preference",
    "ambiguity_penalty",
    "composer_ranking_score",
    "puzzle_id",
]

STAGE1_TOP_K_POLICY = [
    "verification_decision",
    "overall_score",
    "ambiguity_penalty",
    "composer_ranking_score",
    "puzzle_id",
]


@dataclass(frozen=True, slots=True)
class Stage1Thresholds:
    """Explainable thresholds for the first quality-control policy layer."""

    word_leakage_high_fit: float = 0.84
    word_leakage_medium_fit: float = 0.7
    word_leakage_high_margin: float = 0.14
    word_leakage_medium_margin: float = 0.26

    alternative_group_borderline: float = 0.68
    alternative_group_reject: float = 0.8
    alternative_group_limit: int = 8

    cross_group_borderline: float = 0.64
    cross_group_reject: float = 0.78

    board_pressure_borderline: float = 0.48
    board_pressure_reject: float = 0.7

    weak_group_support_borderline: float = 0.78
    weak_group_support_reject: float = 0.58

    high_leakage_word_borderline: int = 2
    high_leakage_word_reject: int = 4


@dataclass(frozen=True, slots=True)
class Stage1ScoringWeights:
    """Transparent weights for Stage 1 ranking components."""

    coherence_weight: float = 0.5
    board_balance_weight: float = 0.2
    evidence_quality_weight: float = 0.15
    weakest_group_weight: float = 0.15

    ambiguity_penalty_weight: float = 0.15
    leakage_penalty_weight: float = 0.1
    alternative_penalty_weight: float = 0.1


STAGE1_THRESHOLDS = Stage1Thresholds()
STAGE1_SCORING_WEIGHTS = Stage1ScoringWeights()


def stage1_threshold_snapshot() -> dict[str, float | int]:
    """Return a serializable snapshot of Stage 1 thresholds."""

    return asdict(STAGE1_THRESHOLDS)


def stage1_scoring_weight_snapshot() -> dict[str, float]:
    """Return a serializable snapshot of Stage 1 scoring weights."""

    return asdict(STAGE1_SCORING_WEIGHTS)


def verification_decision_rank(decision: str | None) -> int:
    """Return a sortable rank for Stage 1 verification classes."""

    if decision == "accept":
        return 2
    if decision == "borderline":
        return 1
    return 0


def clamp_unit(value: float) -> float:
    """Clamp a floating-point value into the closed unit interval."""

    return max(0.0, min(1.0, value))
