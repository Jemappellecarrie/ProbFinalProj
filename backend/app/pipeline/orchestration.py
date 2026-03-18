"""End-to-end pipeline orchestration."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.protocols import PuzzleComposer, PuzzleScorer, PuzzleVerifier, WordFeatureExtractor, WordRepository
from app.domain.value_objects import ComponentSelection, GenerationContext
from app.generators.base import BaseGroupGenerator
from app.pipeline.trace import TraceRecorder
from app.schemas.puzzle_models import PuzzleCandidate, PuzzleScore, VerificationResult
from app.schemas.trace_models import GenerationTrace


@dataclass(slots=True)
class PipelineRunResult:
    """Aggregate result returned by the orchestration layer."""

    puzzle: PuzzleCandidate
    verification: VerificationResult
    score: PuzzleScore
    trace: GenerationTrace | None
    warnings: list[str]
    components: ComponentSelection


class PuzzleGenerationPipeline:
    """Coordinate repositories, feature extraction, generation, verification, and scoring."""

    def __init__(
        self,
        word_repository: WordRepository,
        feature_extractor: WordFeatureExtractor,
        generators: list[BaseGroupGenerator],
        composer: PuzzleComposer,
        verifier: PuzzleVerifier,
        scorer: PuzzleScorer,
        components: ComponentSelection,
    ) -> None:
        self._word_repository = word_repository
        self._feature_extractor = feature_extractor
        self._generators = generators
        self._composer = composer
        self._verifier = verifier
        self._scorer = scorer
        self._components = components

    def run(self, context: GenerationContext) -> PipelineRunResult:
        trace_recorder = TraceRecorder(context.request_id, context.mode, self._components)
        warnings = [
            "Demo mode is active.",
            "Baseline/mock components are being used for generation, verification, and scoring.",
            "Ambiguity, solver ensemble, and style-analysis outputs are scaffold reports only.",
        ]

        entries = self._word_repository.list_entries()
        trace_recorder.add("seed_load", "Loaded seed entries.", {"count": len(entries)})

        features = self._feature_extractor.extract_features(entries)
        features_by_word_id = {feature.word_id: feature for feature in features}
        trace_recorder.add("feature_extraction", "Extracted feature records.", {"count": len(features)})

        groups_by_type: dict[str, list] = {}
        for generator in self._generators:
            candidates = generator.generate(entries, features_by_word_id, context)
            groups_by_type[generator.group_type.value] = candidates
            trace_recorder.add(
                "group_generation",
                f"Generated candidates for {generator.group_type.value}.",
                {
                    "group_type": generator.group_type.value,
                    "strategy": generator.strategy_name,
                    "candidate_count": len(candidates),
                },
            )

        puzzles = self._composer.compose(groups_by_type, context)
        trace_recorder.add("composition", "Composed puzzle candidates.", {"count": len(puzzles)})
        if not puzzles:
            raise RuntimeError(
                "No puzzle candidates were produced. Check demo seed data or generator wiring."
            )

        ranked: list[tuple[PuzzleCandidate, VerificationResult, PuzzleScore]] = []
        for puzzle in puzzles:
            verification = self._verifier.verify(puzzle, context)
            score = self._scorer.score(puzzle, verification, context)
            ranked.append((puzzle, verification, score))

        ranked.sort(key=lambda item: (item[1].passed, item[2].overall), reverse=True)
        selected_puzzle, selected_verification, selected_score = ranked[0]
        trace_recorder.add(
            "ranking",
            "Selected top puzzle candidate.",
            {
                "puzzle_id": selected_puzzle.puzzle_id,
                "passed_verification": selected_verification.passed,
                "overall_score": selected_score.overall,
                "ambiguity_risk": (
                    selected_verification.ambiguity_report.risk_level.value
                    if selected_verification.ambiguity_report is not None
                    else None
                ),
            },
        )

        trace = (
            trace_recorder.build(
                ambiguity_report=selected_verification.ambiguity_report,
                ensemble_result=selected_verification.ensemble_result,
                style_analysis=selected_score.style_analysis,
            )
            if context.include_trace
            else None
        )
        return PipelineRunResult(
            puzzle=selected_puzzle,
            verification=selected_verification,
            score=selected_score,
            trace=trace,
            warnings=warnings,
            components=self._components,
        )
