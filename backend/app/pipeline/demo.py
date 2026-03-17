"""Factory for the demo-mode pipeline wiring."""

from __future__ import annotations

from app.domain.value_objects import ComponentSelection
from app.features.mock_extractor import MockWordFeatureExtractor
from app.generators.registry import build_demo_generators
from app.pipeline.builder import BaselinePuzzleComposer
from app.pipeline.orchestration import PuzzleGenerationPipeline
from app.repositories.word_repository import FileBackedWordRepository
from app.scoring.mock_scorer import MockPuzzleScorer
from app.solver.mock_solver import MockSolverBackend
from app.solver.verifier import BaselineAmbiguityEvaluator, BaselinePuzzleVerifier


def build_demo_pipeline(word_repository: FileBackedWordRepository) -> PuzzleGenerationPipeline:
    """Construct the complete demo-mode orchestration stack."""

    feature_extractor = MockWordFeatureExtractor()
    generators = build_demo_generators()
    composer = BaselinePuzzleComposer()
    solver = MockSolverBackend()
    verifier = BaselinePuzzleVerifier(solver=solver, ambiguity_evaluator=BaselineAmbiguityEvaluator())
    scorer = MockPuzzleScorer()
    components = ComponentSelection(
        feature_extractor=feature_extractor.extractor_name,
        generators=[generator.strategy_name for generator in generators],
        composer=composer.composer_name,
        solver=solver.backend_name,
        verifier=verifier.verifier_name,
        scorer=scorer.scorer_name,
    )
    return PuzzleGenerationPipeline(
        word_repository=word_repository,
        feature_extractor=feature_extractor,
        generators=generators,
        composer=composer,
        verifier=verifier,
        scorer=scorer,
        components=components,
    )
