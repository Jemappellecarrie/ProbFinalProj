"""Centralized Stage 3 style-policy weights and thresholds."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class Stage3StyleScoringWeights:
    """Small additive weights for style-aware ranking adjustments."""

    style_alignment_bonus_weight: float = 0.025
    editorial_payoff_bonus_weight: float = 0.085
    label_naturalness_bonus_weight: float = 0.04
    wordplay_bonus_weight: float = 0.004
    phonetic_showcase_bonus_weight: float = 0.01
    mixed_mechanism_bonus_weight: float = 0.015
    semantic_majority_bonus_weight: float = 0.07
    monotony_penalty_weight: float = 0.05
    out_of_band_penalty_weight: float = 0.04
    formulaic_mix_penalty_weight: float = 0.14
    family_repetition_penalty_weight: float = 0.18
    family_saturation_penalty_weight: float = 0.11
    surface_wordplay_penalty_weight: float = 0.12
    repeated_surface_wordplay_penalty_weight: float = 0.1
    editorial_flatness_penalty_weight: float = 0.12
    microtheme_overuse_penalty_weight: float = 0.15
    repeated_pattern_family_penalty_weight: float = 0.13


@dataclass(frozen=True, slots=True)
class Stage3StyleVerifierThresholds:
    """Conservative verifier thresholds for Stage 3 style hooks."""

    monotony_warning_threshold: float = 0.7
    low_alignment_borderline_threshold: float = 0.4
    severe_out_of_band_flag_count: int = 3
    single_mechanism_unique_type_count: int = 1
    formulaic_mix_warning_threshold: float = 0.52
    editorial_flatness_borderline_threshold: float = 0.48
    family_repetition_warning_threshold: float = 0.5
    surface_wordplay_warning_threshold: float = 0.6
    microtheme_trivia_warning_threshold: float = 0.5
    weak_label_naturalness_warning_threshold: float = 0.35


@dataclass(frozen=True, slots=True)
class Stage3EditorialSelectionPolicy:
    """Small diversity caps for composer and top-k editorial families."""

    composer_editorial_family_cap: int = 1
    composer_theme_family_cap: int = 1
    composer_surface_wordplay_family_cap: int = 1
    composer_balanced_mixed_template_cap: int = 1
    top_k_editorial_family_cap: int = 1
    top_k_theme_family_cap: int = 1
    top_k_surface_wordplay_family_cap: int = 1
    top_k_balanced_mixed_template_cap: int = 1


STAGE3_STYLE_SCORING_WEIGHTS = Stage3StyleScoringWeights()
STAGE3_STYLE_VERIFIER_THRESHOLDS = Stage3StyleVerifierThresholds()
STAGE3_EDITORIAL_SELECTION_POLICY = Stage3EditorialSelectionPolicy()


def stage3_scoring_weight_snapshot() -> dict[str, float]:
    """Return a serializable snapshot of Stage 3 style-scoring weights."""

    return asdict(STAGE3_STYLE_SCORING_WEIGHTS)


def stage3_verifier_threshold_snapshot() -> dict[str, float | int]:
    """Return a serializable snapshot of Stage 3 verifier thresholds."""

    return asdict(STAGE3_STYLE_VERIFIER_THRESHOLDS)


def stage3_editorial_selection_snapshot() -> dict[str, int]:
    """Return a serializable snapshot of editorial family-selection caps."""

    return asdict(STAGE3_EDITORIAL_SELECTION_POLICY)
