"""Pipeline orchestration tests using demo-mode components."""

from __future__ import annotations

from app.config.settings import Settings
from app.schemas.api import PuzzleGenerationRequest
from app.services.generation_service import GenerationService


def test_demo_pipeline_generates_complete_puzzle() -> None:
    service = GenerationService(Settings())
    response = service.generate_puzzle(PuzzleGenerationRequest())

    assert response.demo_mode is True
    assert len(response.puzzle.groups) == 4
    assert len(response.puzzle.board_words) == 16
    assert len(set(response.puzzle.board_words)) == 16
    assert response.score.overall >= 0.0
    assert response.verification.ambiguity_report is not None
    assert response.verification.ensemble_result is not None
    assert response.score.style_analysis is not None
