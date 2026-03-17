"""HTTP request and response models."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.core.enums import GroupType
from app.schemas.puzzle_models import PuzzleCandidate, PuzzleScore, VerificationResult
from app.schemas.trace_models import GenerationTrace


class PuzzleGenerationRequest(BaseModel):
    """Request payload for generating a puzzle."""

    seed: int | None = Field(default=17, description="Optional deterministic seed for demo mode.")
    include_trace: bool = True
    developer_mode: bool = True
    requested_group_types: list[GroupType] = Field(default_factory=GroupType.ordered)


class GeneratedPuzzleResponse(BaseModel):
    """Envelope returned by sample and generation endpoints."""

    demo_mode: bool
    selected_components: dict[str, str | list[str]]
    warnings: list[str] = Field(default_factory=list)
    puzzle: PuzzleCandidate
    verification: VerificationResult
    score: PuzzleScore
    trace: GenerationTrace | None = None


class HealthResponse(BaseModel):
    """Health endpoint response."""

    status: str
    app_name: str
    environment: str
    demo_mode: bool


class DebugConfigResponse(BaseModel):
    """Subset of config surfaced in debug mode."""

    app_name: str
    environment: str
    demo_mode: bool
    debug: bool
    cors_origins: list[str]
    seed_words_path: str
    processed_features_path: str


class GroupTypeMetadata(BaseModel):
    """Frontend metadata for group types."""

    type: GroupType
    display_name: str
    description: str
