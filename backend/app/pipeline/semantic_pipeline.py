"""Factory for the semantic baseline pipeline wiring."""

from __future__ import annotations

from app.domain.value_objects import ComponentSelection
from app.features.human_feature_strategy import HumanCuratedFeatureExtractor
from app.generators.lexical import HumanLexicalGroupGenerator
from app.generators.phonetic import HumanPhoneticGroupGenerator
from app.generators.semantic import HumanSemanticGroupGenerator
from app.generators.theme import HumanThemeGroupGenerator
from app.pipeline.builder import HumanPuzzleComposer
from app.pipeline.orchestration import PuzzleGenerationPipeline
from app.repositories.word_repository import FileBackedWordRepository
from app.scoring.human_scoring_strategy import HumanOwnedPuzzleScorer
from app.scoring.style_analysis import HumanStyleAnalyzer
from app.solver.ensemble import EnsembleSolverCoordinator
from app.solver.human_ambiguity_strategy import HumanAmbiguityEvaluator
from app.solver.registry import build_demo_solver_registry
from app.solver.verifier import InternalPuzzleVerifier


def build_semantic_baseline_pipeline(
    word_repository: FileBackedWordRepository,
) -> PuzzleGenerationPipeline:
    """Construct the non-demo semantic baseline pipeline."""

    feature_extractor = HumanCuratedFeatureExtractor()
    generators = [
        HumanSemanticGroupGenerator(),
        HumanLexicalGroupGenerator(),
        HumanPhoneticGroupGenerator(),
        HumanThemeGroupGenerator(),
    ]
    composer = HumanPuzzleComposer()
    style_analyzer = HumanStyleAnalyzer()
    solver_registry = build_demo_solver_registry()
    solver = solver_registry.list_solvers()[0]
    solver_ensemble = EnsembleSolverCoordinator(solver_registry)
    verifier = InternalPuzzleVerifier(
        solver=solver,
        solver_ensemble=solver_ensemble,
        ambiguity_evaluator=HumanAmbiguityEvaluator(),
        style_analyzer=style_analyzer,
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
