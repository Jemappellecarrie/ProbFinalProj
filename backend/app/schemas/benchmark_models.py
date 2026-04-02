"""Typed contracts for NYT benchmark normalization, audit, and blind review."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class BenchmarkGroupRecord(BaseModel):
    """One normalized four-word benchmark group."""

    group_label: str
    level: int | None = None
    color: str | None = None
    words: list[str] = Field(default_factory=list)
    original_positions: list[dict[str, Any]] = Field(default_factory=list)
    mechanism_type: str = "semantic"
    mechanism_confidence: float = 0.0
    mechanism_rationale: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("group_label")
    @classmethod
    def validate_group_label(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("BenchmarkGroupRecord.group_label must be non-empty.")
        return cleaned

    @field_validator("words")
    @classmethod
    def validate_words(cls, value: list[str]) -> list[str]:
        if len(value) != 4:
            raise ValueError("BenchmarkGroupRecord.words must contain exactly four items.")
        if len(set(value)) != 4:
            raise ValueError("BenchmarkGroupRecord.words must contain four unique items.")
        return value


class NormalizedBenchmarkBoard(BaseModel):
    """Canonical board-level benchmark record."""

    benchmark_board_id: str
    source_dataset: str
    source_provenance: list[str] = Field(default_factory=list)
    source_game_id: str
    puzzle_date: str
    board_words: list[str] = Field(default_factory=list)
    original_tile_positions: list[dict[str, Any]] = Field(default_factory=list)
    groups: list[BenchmarkGroupRecord] = Field(default_factory=list)
    board_signature: str
    solution_signature: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("board_words")
    @classmethod
    def validate_board_words(cls, value: list[str]) -> list[str]:
        if len(value) != 16:
            raise ValueError("NormalizedBenchmarkBoard.board_words must contain sixteen items.")
        if len(set(value)) != 16:
            raise ValueError(
                "NormalizedBenchmarkBoard.board_words must contain sixteen unique items."
            )
        return value

    @field_validator("groups")
    @classmethod
    def validate_groups(cls, value: list[BenchmarkGroupRecord]) -> list[BenchmarkGroupRecord]:
        if len(value) != 4:
            raise ValueError("NormalizedBenchmarkBoard.groups must contain exactly four groups.")
        return value

    @model_validator(mode="after")
    def validate_group_words_match_board(self) -> NormalizedBenchmarkBoard:
        grouped_words = [word for group in self.groups for word in group.words]
        if sorted(grouped_words) != sorted(self.board_words):
            raise ValueError(
                "NormalizedBenchmarkBoard.groups must flatten to the same 16 board words."
            )
        return self


class BenchmarkSplitManifest(BaseModel):
    """Deterministic split manifest over normalized benchmark board ids."""

    split_name: str
    policy: str
    board_ids: list[str] = Field(default_factory=list)
    count: int = 0
    start_date: str | None = None
    end_date: str | None = None
    notes: list[str] = Field(default_factory=list)


class BenchmarkManifest(BaseModel):
    """Machine-readable summary of the normalized public benchmark bundle."""

    benchmark_version: str = "boards_v1"
    primary_source_dataset: str
    board_count: int
    primary_board_count: int
    supplement_board_count: int = 0
    repaired_board_count: int = 0
    invalid_board_ids: list[str] = Field(default_factory=list)
    load_notes: list[str] = Field(default_factory=list)
    date_min: str | None = None
    date_max: str | None = None
    split_policy: str = ""
    artifact_paths: dict[str, str] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class BenchmarkNormalizationResult(BaseModel):
    """In-memory result of benchmark normalization and split construction."""

    manifest: BenchmarkManifest
    boards: list[NormalizedBenchmarkBoard] = Field(default_factory=list)
    calibration_split: BenchmarkSplitManifest
    holdout_split: BenchmarkSplitManifest
    freshness_split: BenchmarkSplitManifest | None = None
    output_files: dict[str, str] = Field(default_factory=dict)


class ComparablePuzzleRecord(BaseModel):
    """Lightweight record shape reused for benchmark-side audit summaries."""

    puzzle_id: str
    board_words: list[str] = Field(default_factory=list)
    group_labels: list[str] = Field(default_factory=list)
    group_word_sets: list[list[str]] = Field(default_factory=list)
    group_types: list[str] = Field(default_factory=list)
    mechanism_mix_summary: dict[str, int] = Field(default_factory=dict)
    mixed_board: bool = False
    verification_decision: str | None = None
    score_breakdown: dict[str, Any] = Field(default_factory=dict)
    ambiguity_report: dict[str, Any] | None = None
    style_analysis: dict[str, Any] | None = None
    reject_reasons: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class QualityAuditReport(BaseModel):
    """Top-level machine-readable result of the NYT benchmark quality audit."""

    report_version: str = "quality_audit_v1"
    generated_run_id: str
    generated_top_k_count: int
    benchmark_calibration_count: int
    benchmark_holdout_count: int
    split_policy: str
    generated_quality_buckets: dict[str, int] = Field(default_factory=dict)
    benchmark_quality_buckets: dict[str, int] = Field(default_factory=dict)
    comparison_sections: dict[str, Any] = Field(default_factory=dict)
    quality_gate_summary: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class BlindReviewSolutionGroup(BaseModel):
    """Reviewer-facing solved group view."""

    label: str
    words: list[str] = Field(default_factory=list)


class BlindReviewPacketEntry(BaseModel):
    """One source-hidden board in the reviewer packet."""

    packet_board_id: str
    review_order: int
    board_words: list[str] = Field(default_factory=list)
    solution_groups: list[BlindReviewSolutionGroup] = Field(default_factory=list)
    review_fields: list[str] = Field(default_factory=list)


class BlindReviewPacket(BaseModel):
    """Reviewer-facing blind review packet."""

    packet_name: str
    seed: int
    entries: list[BlindReviewPacketEntry] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class BlindReviewHiddenSource(BaseModel):
    """Hidden source metadata kept out of the reviewer-facing packet."""

    source_label: str
    source_board_id: str
    source_run_id: str | None = None


class BlindReviewAnswerKeyEntry(BaseModel):
    """Answer-key row mapping one blind packet id back to its source."""

    packet_board_id: str
    hidden_source: BlindReviewHiddenSource


class BlindReviewAnswerKey(BaseModel):
    """Source map stored separately from the reviewer packet."""

    packet_name: str
    entries: list[BlindReviewAnswerKeyEntry] = Field(default_factory=list)


class BlindReviewPacketBundle(BaseModel):
    """Combined reviewer packet and hidden answer key."""

    packet: BlindReviewPacket
    answer_key: BlindReviewAnswerKey
    output_files: dict[str, str] = Field(default_factory=dict)


class QualityGateResult(BaseModel):
    """Honest pass/fail decision for the human review threshold."""

    gate_name: str
    threshold_rate: float
    actual_rate: float | None = None
    passed: bool | None = None
    resolved: bool = True
    evaluated_board_count: int
    notes: list[str] = Field(default_factory=list)


class BlindReviewScoringSummary(BaseModel):
    """Aggregate results from one or more blind review forms."""

    generated_publishable_rate: float
    benchmark_publishable_rate: float
    inter_rater_agreement: dict[str, float] = Field(default_factory=dict)
    failure_modes: dict[str, int] = Field(default_factory=dict)
    final_quality_gate: QualityGateResult
    output_files: dict[str, str] = Field(default_factory=dict)
