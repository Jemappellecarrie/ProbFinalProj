"""Lightweight value objects shared across pipeline components."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.enums import GenerationMode, GroupType


@dataclass(slots=True)
class GenerationContext:
    """Context propagated through pipeline execution for reproducibility."""

    request_id: str
    mode: GenerationMode
    demo_mode: bool
    include_trace: bool
    developer_mode: bool
    seed: int | None = None
    requested_group_types: list[GroupType] = field(default_factory=GroupType.ordered)
    run_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ComponentSelection:
    """Named component selection used in debug payloads and traces."""

    feature_extractor: str
    generators: list[str]
    composer: str
    solver: str
    verifier: str
    scorer: str
