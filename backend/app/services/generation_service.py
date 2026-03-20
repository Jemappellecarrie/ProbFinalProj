"""Application service for puzzle generation endpoints."""

from __future__ import annotations

from app.config.settings import Settings
from app.core.enums import GenerationMode
from app.domain.value_objects import GenerationContext
from app.pipeline.demo import build_demo_pipeline
from app.pipeline.orchestration import PipelineRunResult
from app.repositories.puzzle_repository import SamplePuzzleRepository
from app.repositories.word_repository import FileBackedWordRepository
from app.schemas.api import GeneratedPuzzleResponse, PuzzleGenerationRequest
from app.utils.ids import new_id


class GenerationService:
    """User-facing service for sample loading and puzzle generation."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._sample_repository = SamplePuzzleRepository(settings)
        self._word_repository = FileBackedWordRepository(settings)
        if settings.demo_mode:
            self._pipeline = build_demo_pipeline(self._word_repository)
        else:
            from app.pipeline.human_pipeline import build_human_pipeline

            self._pipeline = build_human_pipeline(self._word_repository)

    def load_sample_puzzle(self) -> GeneratedPuzzleResponse:
        """Return a repository-managed sample payload."""

        return self._sample_repository.load_sample_payload()

    def generate_puzzle(self, request: PuzzleGenerationRequest) -> GeneratedPuzzleResponse:
        """Run the generation pipeline and return the best available puzzle."""

        mode = GenerationMode.DEMO if self._settings.demo_mode else GenerationMode.HUMAN_MIXED
        context = GenerationContext(
            request_id=new_id("req"),
            mode=mode,
            demo_mode=self._settings.demo_mode,
            include_trace=request.include_trace,
            developer_mode=request.developer_mode,
            seed=request.seed,
            requested_group_types=request.requested_group_types,
        )
        result: PipelineRunResult = self._pipeline.run(context)
        return GeneratedPuzzleResponse(
            demo_mode=self._settings.demo_mode,
            selected_components={
                "feature_extractor": result.components.feature_extractor,
                "generators": result.components.generators,
                "composer": result.components.composer,
                "solver": result.components.solver,
                "solver_registry": result.components.solver_registry,
                "verifier": result.components.verifier,
                "scorer": result.components.scorer,
                "style_analyzer": result.components.style_analyzer or "not_configured",
            },
            warnings=result.warnings,
            puzzle=result.puzzle,
            verification=result.verification,
            score=result.score,
            trace=result.trace,
        )
