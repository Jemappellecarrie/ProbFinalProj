"""Application service for puzzle generation endpoints."""

from __future__ import annotations

from app.config.settings import Settings
from app.core.enums import GenerationMode
from app.domain.value_objects import GenerationContext
from app.pipeline.demo import build_demo_pipeline
from app.pipeline.orchestration import PipelineRunResult
from app.pipeline.semantic_pipeline import build_semantic_baseline_pipeline
from app.repositories.puzzle_repository import SamplePuzzleRepository
from app.repositories.word_repository import FileBackedWordRepository
from app.schemas.api import GeneratedPuzzleResponse, PuzzleGenerationRequest
from app.utils.ids import new_id, stable_id


class GenerationService:
    """User-facing service for sample loading and puzzle generation."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._sample_repository = SamplePuzzleRepository(settings)
        self._word_repository = FileBackedWordRepository(settings)
        self._pipeline = (
            build_demo_pipeline(self._word_repository)
            if settings.demo_mode
            else build_semantic_baseline_pipeline(self._word_repository)
        )

    def load_sample_puzzle(self) -> GeneratedPuzzleResponse:
        """Return a repository-managed sample payload."""

        return self._sample_repository.load_sample_payload()

    def _context_for_request(
        self,
        request: PuzzleGenerationRequest,
        *,
        run_metadata: dict[str, object] | None = None,
    ) -> GenerationContext:
        request_id = (
            stable_id(
                "req",
                self._settings.demo_mode,
                request.seed,
                [group_type.value for group_type in request.requested_group_types],
                request.include_trace,
                request.developer_mode,
            )
            if not self._settings.demo_mode and request.seed is not None
            else new_id("req")
        )
        return GenerationContext(
            request_id=request_id,
            mode=GenerationMode.DEMO if self._settings.demo_mode else GenerationMode.HUMAN_MIXED,
            demo_mode=self._settings.demo_mode,
            include_trace=request.include_trace,
            developer_mode=request.developer_mode,
            seed=request.seed,
            requested_group_types=request.requested_group_types,
            run_metadata=dict(run_metadata or {}),
        )

    def run_generation(
        self,
        request: PuzzleGenerationRequest,
        *,
        run_metadata: dict[str, object] | None = None,
    ) -> PipelineRunResult:
        """Run the pipeline and return the full internal result bundle."""

        return self._pipeline.run(self._context_for_request(request, run_metadata=run_metadata))

    def generate_puzzle(self, request: PuzzleGenerationRequest) -> GeneratedPuzzleResponse:
        """Run the generation pipeline and return the best available puzzle."""

        result = self.run_generation(request)
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
