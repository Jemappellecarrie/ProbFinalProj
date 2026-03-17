"""Baseline scorer for demo mode."""

from __future__ import annotations

from app.domain.value_objects import GenerationContext
from app.schemas.puzzle_models import PuzzleCandidate, PuzzleScore, VerificationResult
from app.scoring.base import BasePuzzleScorer


class MockPuzzleScorer(BasePuzzleScorer):
    """Transparent baseline scorer for demo-mode ranking."""

    scorer_name = "mock_puzzle_scorer"

    def score(
        self,
        puzzle: PuzzleCandidate,
        verification: VerificationResult,
        context: GenerationContext,
    ) -> PuzzleScore:
        coherence = round(0.5 + (0.1 * len(puzzle.groups)), 3)
        ambiguity_penalty = round(verification.ambiguity_score, 3)
        overall = round(max(0.0, coherence - ambiguity_penalty), 3)
        return PuzzleScore(
            scorer_name=self.scorer_name,
            overall=overall,
            coherence=coherence,
            ambiguity_penalty=ambiguity_penalty,
            human_likeness=None,
            components={
                "group_count_bonus": 0.4,
                "baseline_coherence": coherence,
                "baseline_ambiguity_penalty": ambiguity_penalty,
            },
            notes=[
                "Baseline scorer is deterministic and intentionally simple.",
                "Use it for wiring, debugging, and regression tests only.",
            ],
        )
