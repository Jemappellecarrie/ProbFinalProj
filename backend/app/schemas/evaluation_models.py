"""Typed models for ambiguity, solver ensemble, style analysis, and batch evaluation.

These models provide a second-stage quality-control scaffold around the core
generation pipeline. They are intentionally explicit about what is baseline
versus human-owned. The goal is traceability and offline inspection, not a
claim that ambiguity or style judgment has been solved.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AmbiguityRiskLevel(str, Enum):
    """Coarse ambiguity risk levels for scaffold reporting."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SolverDisagreementFlag(str, Enum):
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
    proposed_groups: list[list[str]] = Field(default_factory=list)
    matched_target_solution: bool = False
    overlap_ratio: float = 0.0
    notes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AmbiguityEvidence(BaseModel):
    """Structured evidence bundle used to justify ambiguity-related outcomes."""

    word_group_leakage: list[WordGroupLeakage] = Field(default_factory=list)
    cross_group_compatibility: list[CrossGroupCompatibility] = Field(default_factory=list)
    alternative_groupings: list[AlternativeGroupingCandidate] = Field(default_factory=list)
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
    board_words: list[str]
    group_labels: list[str] = Field(default_factory=list)
    group_types: list[str] = Field(default_factory=list)
    score_breakdown: ScoreBreakdownView
    ambiguity_risk_level: AmbiguityRiskLevel | None = None
    ambiguity_penalty_hint: float = 0.0
    solver_agreement_ratio: float | None = None
    solver_disagreement_flags: list[SolverDisagreementFlag] = Field(default_factory=list)
    style_archetype: str | None = None
    nyt_likeness_placeholder: float | None = None
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
    group_types: list[str]
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
    group_types: list[str]
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
