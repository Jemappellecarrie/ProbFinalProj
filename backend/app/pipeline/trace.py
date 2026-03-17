"""Trace recording utilities."""

from __future__ import annotations

from app.core.enums import GenerationMode
from app.domain.value_objects import ComponentSelection
from app.schemas.trace_models import GenerationTrace, TraceEvent
from app.utils.ids import new_id


class TraceRecorder:
    """Collect lightweight pipeline events and build a trace payload."""

    def __init__(self, request_id: str, mode: GenerationMode, components: ComponentSelection) -> None:
        self._request_id = request_id
        self._mode = mode
        self._components = components
        self._events: list[TraceEvent] = []

    def add(self, stage: str, message: str, metadata: dict[str, object] | None = None) -> None:
        self._events.append(TraceEvent(stage=stage, message=message, metadata=metadata or {}))

    def build(self) -> GenerationTrace:
        return GenerationTrace(
            trace_id=new_id("trace"),
            request_id=self._request_id,
            mode=self._mode,
            feature_extractor=self._components.feature_extractor,
            generators=self._components.generators,
            solver_backend=self._components.solver,
            scorer=self._components.scorer,
            events=self._events,
            metadata={"verifier": self._components.verifier, "composer": self._components.composer},
        )
