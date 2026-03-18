"""Factory for the demo-mode pipeline wiring."""

from __future__ import annotations

from app.domain.value_objects import ComponentSelection
from app.features.mock_extractor import MockWordFeatureExtractor
from app.generators.registry import build_demo_generators
from app.pipeline.builder import BaselinePuzzleComposer
from app.pipeline.orchestration import PuzzleGenerationPipeline
from app.repositories.word_repository import FileBackedWordRepository
from app.scoring.mock_scorer import MockPuzzleScorer
from app.scoring.style_analysis import BaselineStyleAnalyzer
from app.solver.ensemble import EnsembleSolverCoordinator
from app.solver.registry import build_demo_solver_registry
from app.solver.verifier import BaselineAmbiguityEvaluator, BaselinePuzzleVerifier


def build_demo_pipeline(word_repository: FileBackedWordRepository) -> PuzzleGenerationPipeline:
    """Construct the complete demo-mode orchestration stack."""

    feature_extractor = MockWordFeatureExtractor()
    generators = build_demo_generators()
    composer = BaselinePuzzleComposer()
    style_analyzer = BaselineStyleAnalyzer()
    solver_registry = build_demo_solver_registry()
    solver = solver_registry.list_solvers()[0]
    solver_ensemble = EnsembleSolverCoordinator(solver_registry)
    verifier = BaselinePuzzleVerifier(
        solver=solver,
        solver_ensemble=solver_ensemble,
        ambiguity_evaluator=BaselineAmbiguityEvaluator(),
    )
    scorer = MockPuzzleScorer(style_analyzer=style_analyzer)
    components = ComponentSelection(
        feature_extractor=feature_extractor.extractor_name,
        generators=[generator.strategy_name for generator in generators],
        composer=composer.composer_name,
        solver=solver_ensemble.coordinator_name,
        verifier=verifier.verifier_name,
        scorer=scorer.scorer_name,
        solver_registry=solver_registry.names(),
        style_analyzer=style_analyzer.analyzer_name,
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
