"""Repository for static sample puzzle payloads."""

from __future__ import annotations

import json

from app.config.settings import Settings
from app.schemas.api import GeneratedPuzzleResponse


class SamplePuzzleRepository:
    """Load versioned sample assets used by the sample endpoint."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def load_sample_payload(self) -> GeneratedPuzzleResponse:
        with self._settings.sample_puzzle_path.open("r", encoding="utf-8") as handle:
            return GeneratedPuzzleResponse.model_validate(json.load(handle))
