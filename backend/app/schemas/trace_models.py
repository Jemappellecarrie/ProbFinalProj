"""Trace models for reproducible pipeline debugging."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from app.core.enums import GenerationMode


class TraceEvent(BaseModel):
    """Single pipeline event captured for developer-mode debugging."""

    stage: str
    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class GenerationTrace(BaseModel):
    """End-to-end pipeline trace for a single request."""

    trace_id: str
    request_id: str
    mode: GenerationMode
    feature_extractor: str
    generators: list[str]
    solver_backend: str
    scorer: str
    events: list[TraceEvent] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
