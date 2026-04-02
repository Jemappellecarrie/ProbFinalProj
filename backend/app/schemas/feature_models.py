"""Typed models for words and feature records."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class WordEntry(BaseModel):
    """Canonical representation of a seed word."""

    word_id: str
    surface_form: str
    normalized: str
    source: str = "seed"
    lemma: str | None = None
    notes: list[str] = Field(default_factory=list)
    known_group_hints: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CanonicalFormEvidence(BaseModel):
    """Canonicalization details attached to semantic baseline feature records."""

    original_surface: str
    display_form: str
    normalized_source: str
    canonical_normalized: str
    tokenized_words: list[str] = Field(default_factory=list)
    collision_count: int = 1
    colliding_word_ids: list[str] = Field(default_factory=list)


class RawSemanticSourceFacts(BaseModel):
    """Raw metadata facts preserved before baseline derivation."""

    semantic_metadata: list[str] = Field(default_factory=list)
    theme_metadata: list[str] = Field(default_factory=list)
    lexical_metadata: list[str] = Field(default_factory=list)
    phonetic_metadata: list[str] = Field(default_factory=list)
    group_hints: dict[str, str] = Field(default_factory=dict)
    label_hint_sources: list[str] = Field(default_factory=list)


class SemanticSupportSummary(BaseModel):
    """Coarse support accounting for explainability and sparse-feature honesty."""

    semantic_signal_count: int = 0
    theme_signal_count: int = 0
    label_hint_count: int = 0
    support_level: str = "surface_only"
    notes: list[str] = Field(default_factory=list)


class WordFeatures(BaseModel):
    """Normalized feature bundle for a single word."""

    word_id: str
    normalized: str
    semantic_tags: list[str] = Field(default_factory=list)
    lexical_signals: list[str] = Field(default_factory=list)
    phonetic_signals: list[str] = Field(default_factory=list)
    theme_tags: list[str] = Field(default_factory=list)
    extraction_mode: str
    feature_version: str = "0.1.0"
    provenance: list[str] = Field(default_factory=list)
    debug_attributes: dict[str, Any] = Field(default_factory=dict)
