"""Typed models for groups, puzzles, verification, and scoring."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.core.enums import GroupType, RejectReasonCode
from app.schemas.evaluation_models import AmbiguityReport, EnsembleSolverResult, StyleAnalysisReport


class GroupCandidate(BaseModel):
    """A four-word candidate group proposed by a generator."""

    candidate_id: str
    group_type: GroupType
    label: str
    rationale: str
    words: list[str]
    word_ids: list[str]
    source_strategy: str
    extraction_mode: str
    confidence: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("words")
    @classmethod
    def validate_word_count(cls, value: list[str]) -> list[str]:
        if len(value) != 4:
            raise ValueError("GroupCandidate.words must contain exactly four items.")
        return value


class PuzzleCandidate(BaseModel):
    """A composed puzzle candidate containing exactly four groups."""

    puzzle_id: str
    board_words: list[str]
    groups: list[GroupCandidate]
    compatibility_notes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("board_words")
    @classmethod
    def validate_board_word_count(cls, value: list[str]) -> list[str]:
        if len(value) != 16:
            raise ValueError("PuzzleCandidate.board_words must contain exactly sixteen items.")
        return value

    @field_validator("groups")
    @classmethod
    def validate_group_count(cls, value: list[GroupCandidate]) -> list[GroupCandidate]:
        if len(value) != 4:
            raise ValueError("PuzzleCandidate.groups must contain exactly four groups.")
        return value


class RejectReason(BaseModel):
    """Structured rejection reason for filtering or verification."""

    code: RejectReasonCode
    message: str
    severity: str = "warning"
    metadata: dict[str, Any] = Field(default_factory=dict)


class SolverResult(BaseModel):
    """Output of a solver backend used for verification."""

    backend_name: str
    solved: bool
    confidence: float | None = None
    proposed_groups: list[list[str]] = Field(default_factory=list)
    alternative_groupings_detected: int = 0
    notes: list[str] = Field(default_factory=list)
    raw_output: dict[str, Any] = Field(default_factory=dict)


class VerificationResult(BaseModel):
    """Verifier output including rejection reasons and ambiguity metrics."""

    passed: bool
    reject_reasons: list[RejectReason] = Field(default_factory=list)
    leakage_estimate: float = 0.0
    ambiguity_score: float = 0.0
    ambiguity_report: AmbiguityReport | None = None
    ensemble_result: EnsembleSolverResult | None = None
    notes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PuzzleScore(BaseModel):
    """Score breakdown for ranking and debugging."""

    scorer_name: str
    overall: float
    coherence: float
    ambiguity_penalty: float
    human_likeness: float | None = None
    style_analysis: StyleAnalysisReport | None = None
    components: dict[str, float] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
