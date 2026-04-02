"""Typed models for ambiguity, solver ensemble, style analysis, and batch evaluation.

These models provide a second-stage quality-control scaffold around the core
generation pipeline. They are intentionally explicit about what is baseline
versus human-owned. The goal is traceability and offline inspection, not a
claim that ambiguity or style judgment has been solved.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class AmbiguityRiskLevel(StrEnum):
    """Coarse ambiguity risk levels for scaffold reporting."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SolverDisagreementFlag(StrEnum):
    """Machine-readable disagreement categories for solver ensemble reporting."""

    TARGET_MISMATCH = "target_mismatch"
    ALTERNATIVE_SOLUTION_PROPOSED = "alternative_solution_proposed"
    STRUCTURAL_DISAGREEMENT = "structural_disagreement"
    CONFIDENCE_SPREAD = "confidence_spread"


class WordGroupLeakage(BaseModel):
    """Placeholder evidence that a word may appear compatible with another group."""

    word: str
    word_id: str | None = None
    source_group_label: str
    target_group_label: str
    leakage_kind: str
    evidence_strength: float = 0.0
    notes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WordFitSummary(BaseModel):
    """Per-word fit summary used for Stage 1 leakage analysis."""

    word: str
    word_id: str | None = None
    assigned_group_label: str
    assigned_support: float = 0.0
    strongest_competing_group_label: str | None = None
    strongest_competing_support: float = 0.0
    leakage_margin: float = 0.0
    severity: str = "low"
    notes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GroupCoherenceSummary(BaseModel):
    """Compact support summary for one true group."""

    group_label: str
    support_score: float = 0.0
    mean_pairwise_similarity: float = 0.0
    weakest_member_support: float = 0.0
    strongest_competing_fit: float = 0.0
    notes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CrossGroupCompatibility(BaseModel):
    """Pairwise compatibility record for groups that may leak into each other."""

    left_group_label: str
    right_group_label: str
    compatibility_kind: str
    shared_signals: list[str] = Field(default_factory=list)
    risk_weight: float = 0.0
    notes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AlternativeGroupingCandidate(BaseModel):
    """Alternative partition candidate surfaced by a baseline or real solver."""

    candidate_id: str
    source_solver: str
    words: list[str] = Field(default_factory=list)
    word_ids: list[str] = Field(default_factory=list)
    proposed_groups: list[list[str]] = Field(default_factory=list)
    matched_target_solution: bool = False
    overlap_ratio: float = 0.0
    label_hint: str | None = None
    coherence_score: float = 0.0
    shared_signal_score: float = 0.0
    source_group_count: int = 0
    suspicion_score: float = 0.0
    notes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BoardAmbiguitySummary(BaseModel):
    """Board-level ambiguity summary consumed by verifier and scorer."""

    board_pressure: float = 0.0
    max_alternative_group_pressure: float = 0.0
    high_leakage_word_count: int = 0
    strongest_confusing_pair: str | None = None
    severity: str = "low"
    warning_flags: list[str] = Field(default_factory=list)
    metrics: dict[str, float] = Field(default_factory=dict)


class AmbiguityEvidence(BaseModel):
    """Structured evidence bundle used to justify ambiguity-related outcomes."""

    group_coherence_summaries: list[GroupCoherenceSummary] = Field(default_factory=list)
    word_fit_summaries: list[WordFitSummary] = Field(default_factory=list)
    word_group_leakage: list[WordGroupLeakage] = Field(default_factory=list)
    cross_group_compatibility: list[CrossGroupCompatibility] = Field(default_factory=list)
    alternative_groupings: list[AlternativeGroupingCandidate] = Field(default_factory=list)
    board_summary: BoardAmbiguitySummary | None = None
    triggered_flags: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class AmbiguityReport(BaseModel):
    """Summary of ambiguity-related evidence and provisional scaffold verdicts."""

    evaluator_name: str
    risk_level: AmbiguityRiskLevel
    penalty_hint: float = 0.0
    reject_recommended: bool = False
    summary: str
    evidence: AmbiguityEvidence = Field(default_factory=AmbiguityEvidence)
    notes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SolverVote(BaseModel):
    """Per-solver vote captured by the ensemble coordinator."""

    solver_name: str
    matched_target_solution: bool
    alternative_solution_proposed: bool
    solved: bool
    confidence: float | None = None
    proposed_groups: list[list[str]] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    raw_output: dict[str, Any] = Field(default_factory=dict)


class SolverAgreementSummary(BaseModel):
    """Aggregate agreement summary across solver votes."""

    total_solvers: int
    matched_target_count: int
    alternative_solution_count: int
    agreement_ratio: float
    disagreement_flags: list[SolverDisagreementFlag] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class EnsembleSolverResult(BaseModel):
    """Aggregate result produced by the solver ensemble scaffold."""

    coordinator_name: str
    primary_solver_name: str | None = None
    votes: list[SolverVote] = Field(default_factory=list)
    agreement_summary: SolverAgreementSummary
    notes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class StyleSignal(BaseModel):
    """Single style-oriented placeholder signal."""

    signal_name: str
    value: float
    interpretation: str
    source: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class PuzzleArchetypeSummary(BaseModel):
    """Coarse placeholder label for the apparent puzzle archetype."""

    label: str
    rationale: str
    flags: list[str] = Field(default_factory=list)


class NYTLikenessPlaceholderScore(BaseModel):
    """Explicitly provisional style score for debugging only."""

    score: float | None = None
    notes: list[str] = Field(default_factory=list)


class StyleMetricComparison(BaseModel):
    """Comparison between an observed style metric and a reference band."""

    metric_name: str
    actual_value: float
    target_min: float | None = None
    target_max: float | None = None
    within_band: bool = True
    drift: str = "within_band"
    explanation: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class GroupStyleSummary(BaseModel):
    """Interpretable style summary for one group."""

    group_label: str
    group_type: str
    archetype: str
    label_token_count: int = 0
    label_clarity: float = 0.0
    label_specificity: float = 0.0
    evidence_interpretability: float = 0.0
    wordplay_indicator: float = 0.0
    redundancy_flags: list[str] = Field(default_factory=list)
    novelty_flags: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MechanismMixProfile(BaseModel):
    """Board-level mix summary over the supported generator families."""

    counts: dict[str, int] = Field(default_factory=dict)
    shares: dict[str, float] = Field(default_factory=dict)
    unique_group_type_count: int = 0
    semantic_group_count: int = 0
    lexical_group_count: int = 0
    phonetic_group_count: int = 0
    theme_group_count: int = 0
    wordplay_group_count: int = 0
    mixed_board: bool = False


class BoardStyleSummary(BaseModel):
    """Interpretable board-level style summary."""

    board_archetype: str
    mechanism_mix_profile: MechanismMixProfile
    group_archetypes: list[str] = Field(default_factory=list)
    label_token_mean: float = 0.0
    label_token_std: float = 0.0
    label_consistency: float = 0.0
    evidence_interpretability: float = 0.0
    semantic_wordplay_balance: float = 0.0
    archetype_diversity: float = 0.0
    redundancy_score: float = 0.0
    monotony_score: float = 0.0
    coherence_trickiness_balance: float = 0.0
    style_alignment_score: float = 0.0
    group_family_signatures: list[str] = Field(default_factory=list)
    board_family_signature: str | None = None
    editorial_family_signature: str | None = None
    editorial_flags: list[str] = Field(default_factory=list)
    out_of_band_flags: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    metrics: dict[str, float] = Field(default_factory=dict)


class StyleAnalysisReport(BaseModel):
    """Style-analysis scaffold output.

    This report is intentionally provisional. It records style-oriented signals
    for debugging and future offline analysis without claiming to measure true
    NYT-likeness.
    """

    analyzer_name: str
    archetype: PuzzleArchetypeSummary
    nyt_likeness: NYTLikenessPlaceholderScore
    signals: list[StyleSignal] = Field(default_factory=list)
    group_style_summaries: list[GroupStyleSummary] = Field(default_factory=list)
    board_style_summary: BoardStyleSummary | None = None
    mechanism_mix_profile: MechanismMixProfile | None = None
    style_target_comparison: list[StyleMetricComparison] = Field(default_factory=list)
    out_of_band_flags: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScoreBreakdownView(BaseModel):
    """Compact score snapshot for ranking and debug panels."""

    overall: float
    coherence: float
    ambiguity_penalty: float
    human_likeness: float | None = None
    components: dict[str, float] = Field(default_factory=dict)


class RankedPuzzleRecord(BaseModel):
    """Compact ranked puzzle view for top-k browsing and batch summaries."""

    rank: int
    puzzle_id: str
    accepted: bool
    verification_decision: str | None = None
    board_words: list[str]
    group_labels: list[str] = Field(default_factory=list)
    group_word_sets: list[list[str]] = Field(default_factory=list)
    group_types: list[str] = Field(default_factory=list)
    mechanism_mix_summary: dict[str, int] = Field(default_factory=dict)
    mixed_board: bool = False
    group_family_signatures: list[str] = Field(default_factory=list)
    board_family_signature: str | None = None
    editorial_family_signature: str | None = None
    theme_family_signatures: list[str] = Field(default_factory=list)
    surface_wordplay_family_signatures: list[str] = Field(default_factory=list)
    editorial_flags: list[str] = Field(default_factory=list)
    score_breakdown: ScoreBreakdownView
    ambiguity_risk_level: AmbiguityRiskLevel | None = None
    ambiguity_penalty_hint: float = 0.0
    solver_agreement_ratio: float | None = None
    solver_disagreement_flags: list[SolverDisagreementFlag] = Field(default_factory=list)
    style_archetype: str | None = None
    nyt_likeness_placeholder: float | None = None
    style_alignment_score: float | None = None
    style_out_of_band_flags: list[str] = Field(default_factory=list)
    ranking_influence_notes: list[str] = Field(default_factory=list)
    trace_id: str | None = None
    reject_risk_flags: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class TopKSummary(BaseModel):
    """Summary of the best accepted puzzles from a batch evaluation run."""

    requested_k: int
    returned_count: int
    ranked_puzzles: list[RankedPuzzleRecord] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class AcceptedPuzzleRecord(BaseModel):
    """Persisted record for an accepted puzzle in batch evaluation."""

    iteration_index: int
    request_seed: int
    puzzle_id: str
    board_words: list[str]
    group_labels: list[str]
    group_word_sets: list[list[str]] = Field(default_factory=list)
    group_types: list[str]
    mechanism_mix_summary: dict[str, int] = Field(default_factory=dict)
    mixed_board: bool = False
    group_family_signatures: list[str] = Field(default_factory=list)
    board_family_signature: str | None = None
    editorial_family_signature: str | None = None
    theme_family_signatures: list[str] = Field(default_factory=list)
    surface_wordplay_family_signatures: list[str] = Field(default_factory=list)
    editorial_flags: list[str] = Field(default_factory=list)
    verification_decision: str | None = None
    score_breakdown: ScoreBreakdownView
    ambiguity_report: AmbiguityReport | None = None
    ensemble_result: EnsembleSolverResult | None = None
    style_analysis: StyleAnalysisReport | None = None
    trace_id: str | None = None
    warnings: list[str] = Field(default_factory=list)
    selected_components: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class RejectedPuzzleRecord(BaseModel):
    """Persisted record for a rejected puzzle in batch evaluation."""

    iteration_index: int
    request_seed: int
    puzzle_id: str
    board_words: list[str]
    group_labels: list[str]
    group_word_sets: list[list[str]] = Field(default_factory=list)
    group_types: list[str]
    mechanism_mix_summary: dict[str, int] = Field(default_factory=dict)
    mixed_board: bool = False
    group_family_signatures: list[str] = Field(default_factory=list)
    board_family_signature: str | None = None
    editorial_family_signature: str | None = None
    theme_family_signatures: list[str] = Field(default_factory=list)
    surface_wordplay_family_signatures: list[str] = Field(default_factory=list)
    editorial_flags: list[str] = Field(default_factory=list)
    verification_decision: str | None = None
    score_breakdown: ScoreBreakdownView
    reject_reasons: list[str] = Field(default_factory=list)
    ambiguity_report: AmbiguityReport | None = None
    ensemble_result: EnsembleSolverResult | None = None
    style_analysis: StyleAnalysisReport | None = None
    trace_id: str | None = None
    warnings: list[str] = Field(default_factory=list)
    selected_components: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class RejectReasonHistogram(BaseModel):
    """Histogram of reject reason counts."""

    counts: dict[str, int] = Field(default_factory=dict)


class GeneratorMixSummary(BaseModel):
    """Counts describing which generator families and strategies appeared."""

    group_type_counts: dict[str, int] = Field(default_factory=dict)
    generator_strategy_counts: dict[str, int] = Field(default_factory=dict)
    board_mix_counts: dict[str, int] = Field(default_factory=dict)
    board_type_signature_counts: dict[str, int] = Field(default_factory=dict)


class ScoreDistributionSummary(BaseModel):
    """Lightweight score distribution summary for batch runs."""

    average_overall: float = 0.0
    average_coherence: float = 0.0
    average_ambiguity_penalty: float = 0.0
    average_human_likeness: float = 0.0
    min_overall: float = 0.0
    max_overall: float = 0.0


class SolverAgreementStatistics(BaseModel):
    """Aggregate solver agreement statistics across a batch run."""

    total_ensemble_runs: int = 0
    unanimous_target_match_count: int = 0
    disagreement_count: int = 0
    average_agreement_ratio: float = 0.0


class BatchEvaluationConfig(BaseModel):
    """Configuration for an offline batch evaluation run."""

    num_puzzles: int = 10
    output_dir: str | None = None
    demo_mode: bool = True
    save_traces: bool = True
    top_k_size: int = 5
    base_seed: int = 17


class CandidatePoolPuzzleRecord(BaseModel):
    """Persisted record for one ranked candidate surfaced within a request."""

    iteration_index: int
    request_seed: int
    request_rank: int
    selected: bool = False
    puzzle_id: str
    board_words: list[str]
    group_labels: list[str]
    group_word_sets: list[list[str]] = Field(default_factory=list)
    group_types: list[str]
    mechanism_mix_summary: dict[str, int] = Field(default_factory=dict)
    mixed_board: bool = False
    group_family_signatures: list[str] = Field(default_factory=list)
    board_family_signature: str | None = None
    editorial_family_signature: str | None = None
    theme_family_signatures: list[str] = Field(default_factory=list)
    surface_wordplay_family_signatures: list[str] = Field(default_factory=list)
    editorial_flags: list[str] = Field(default_factory=list)
    verification_decision: str | None = None
    score_breakdown: ScoreBreakdownView
    reject_reasons: list[str] = Field(default_factory=list)
    ambiguity_report: AmbiguityReport | None = None
    ensemble_result: EnsembleSolverResult | None = None
    style_analysis: StyleAnalysisReport | None = None
    trace_id: str | None = None
    warnings: list[str] = Field(default_factory=list)
    selected_components: dict[str, Any] = Field(default_factory=dict)
    candidate_source: str = "request_candidate_pool"
    notes: list[str] = Field(default_factory=list)


class FinalQualityBatchConfig(BaseModel):
    """Deterministic batch config for the final quality acceptance sprint."""

    num_requests: int = 200
    output_dir: str
    demo_mode: bool = False
    save_traces: bool = False
    top_k_size: int = 20
    base_seed: int = 17
    candidate_pool_limit: int = 10


class BatchSliceCalibrationSummary(BaseModel):
    """Aggregate summary for one batch slice such as accepted or top-k."""

    slice_name: str
    puzzle_count: int = 0
    verification_decision_counts: dict[str, int] = Field(default_factory=dict)
    mechanism_mix_counts: dict[str, int] = Field(default_factory=dict)
    average_group_type_counts: dict[str, float] = Field(default_factory=dict)
    board_type_signature_counts: dict[str, int] = Field(default_factory=dict)
    mixed_board_rate: float = 0.0
    ambiguity_metrics: dict[str, float] = Field(default_factory=dict)
    scorer_component_averages: dict[str, float] = Field(default_factory=dict)
    label_shape_summary: dict[str, float] = Field(default_factory=dict)
    board_diversity_summary: dict[str, float] = Field(default_factory=dict)
    style_metric_averages: dict[str, float] = Field(default_factory=dict)
    board_archetype_counts: dict[str, int] = Field(default_factory=dict)
    out_of_band_flag_counts: dict[str, int] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class ThresholdDiagnostic(BaseModel):
    """Evidence-backed diagnostic surfaced by batch calibration."""

    code: str
    severity: str = "info"
    message: str
    metric_name: str | None = None
    actual_value: float | None = None
    target_min: float | None = None
    target_max: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CalibrationSummary(BaseModel):
    """Top-level batch calibration summary tied to a reference target version."""

    target_version: str
    accepted: BatchSliceCalibrationSummary
    rejected: BatchSliceCalibrationSummary
    top_k: BatchSliceCalibrationSummary
    target_comparison: list[StyleMetricComparison] = Field(default_factory=list)
    threshold_diagnostics: list[ThresholdDiagnostic] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class BatchEvaluationSummary(BaseModel):
    """High-level summary persisted for an evaluation run."""

    run_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    total_generated: int
    accepted_count: int
    rejected_count: int
    acceptance_rate: float
    reject_reason_histogram: RejectReasonHistogram
    generator_mix: GeneratorMixSummary
    score_distribution: ScoreDistributionSummary
    ambiguity_risk_distribution: dict[str, int] = Field(default_factory=dict)
    solver_agreement_statistics: SolverAgreementStatistics
    top_k: TopKSummary
    calibration_summary: CalibrationSummary | None = None
    output_dir: str
    notes: list[str] = Field(default_factory=list)


class BatchEvaluationRun(BaseModel):
    """Full persisted batch evaluation payload."""

    run_id: str
    config: BatchEvaluationConfig
    summary: BatchEvaluationSummary
    accepted_records: list[AcceptedPuzzleRecord] = Field(default_factory=list)
    rejected_records: list[RejectedPuzzleRecord] = Field(default_factory=list)
    output_files: dict[str, str] = Field(default_factory=dict)


class DebugComparisonView(BaseModel):
    """Developer-facing view for recent batch evaluation inspection."""

    run_id: str
    summary: BatchEvaluationSummary
    top_k: TopKSummary
    notes: list[str] = Field(default_factory=list)
