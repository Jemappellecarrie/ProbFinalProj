"""Factory for the human-mode pipeline wiring."""

from __future__ import annotations

from app.domain.value_objects import ComponentSelection
from app.features.human_feature_strategy import HumanCuratedFeatureExtractor
from app.generators.lexical import MockLexicalGroupGenerator
from app.generators.phonetic import MockPhoneticGroupGenerator
from app.generators.semantic import HumanSemanticGroupGenerator
from app.generators.theme import MockThemeGroupGenerator
from app.pipeline.builder import HumanPuzzleComposer
from app.pipeline.orchestration import PuzzleGenerationPipeline
from app.repositories.word_repository import FileBackedWordRepository
from app.scoring.human_scoring_strategy import HumanOwnedPuzzleScorer
from app.scoring.style_analysis import BaselineStyleAnalyzer
from app.solver.ensemble import EnsembleSolverCoordinator
from app.solver.human_ambiguity_strategy import HumanAmbiguityEvaluator
from app.solver.registry import build_demo_solver_registry
from app.solver.verifier import InternalPuzzleVerifier


def build_human_pipeline(word_repository: FileBackedWordRepository) -> PuzzleGenerationPipeline:
    """Construct the human-mode orchestration stack with real ML components."""

    feature_extractor = HumanCuratedFeatureExtractor()
    generators = [
        HumanSemanticGroupGenerator(),
        MockLexicalGroupGenerator(),
        MockPhoneticGroupGenerator(),
        MockThemeGroupGenerator(),
    ]
    composer = HumanPuzzleComposer()
    style_analyzer = BaselineStyleAnalyzer()
    solver_registry = build_demo_solver_registry()
    solver = solver_registry.list_solvers()[0]
    solver_ensemble = EnsembleSolverCoordinator(solver_registry)
    ambiguity_evaluator = HumanAmbiguityEvaluator()
    verifier = InternalPuzzleVerifier(
        solver=solver,
        solver_ensemble=solver_ensemble,
        ambiguity_evaluator=ambiguity_evaluator,
    )
    scorer = HumanOwnedPuzzleScorer(style_analyzer=style_analyzer)
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
