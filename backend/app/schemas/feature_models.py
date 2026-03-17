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
