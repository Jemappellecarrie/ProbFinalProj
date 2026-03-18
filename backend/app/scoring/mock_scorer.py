"""Baseline scorer for demo mode."""

from __future__ import annotations

from app.domain.value_objects import GenerationContext
from app.schemas.puzzle_models import PuzzleCandidate, PuzzleScore, VerificationResult
from app.scoring.base import BasePuzzleScorer
from app.scoring.style_analysis import BaseStyleAnalyzer, BaselineStyleAnalyzer


class MockPuzzleScorer(BasePuzzleScorer):
    """Transparent baseline scorer for demo-mode ranking."""

    scorer_name = "mock_puzzle_scorer"

    def __init__(self, style_analyzer: BaseStyleAnalyzer | None = None) -> None:
        self._style_analyzer = style_analyzer or BaselineStyleAnalyzer()

    def score(
        self,
        puzzle: PuzzleCandidate,
        verification: VerificationResult,
        context: GenerationContext,
    ) -> PuzzleScore:
        style_analysis = self._style_analyzer.analyze(puzzle, verification, context)
        coherence = round(0.5 + (0.1 * len(puzzle.groups)), 3)
        ambiguity_penalty = round(verification.ambiguity_score, 3)
        overall = round(max(0.0, coherence - ambiguity_penalty), 3)
        return PuzzleScore(
            scorer_name=self.scorer_name,
            overall=overall,
            coherence=coherence,
            ambiguity_penalty=ambiguity_penalty,
            human_likeness=style_analysis.nyt_likeness.score,
            style_analysis=style_analysis,
            components={
                "group_count_bonus": 0.4,
                "baseline_coherence": coherence,
                "baseline_ambiguity_penalty": ambiguity_penalty,
                "baseline_style_placeholder": style_analysis.nyt_likeness.score or 0.0,
            },
            notes=[
                "Baseline scorer is deterministic and intentionally simple.",
                "Use it for wiring, debugging, and regression tests only.",
            ],
        )
