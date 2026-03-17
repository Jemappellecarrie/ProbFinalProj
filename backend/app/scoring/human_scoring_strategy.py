"""Human-owned final scoring strategy.

File location:
    backend/app/scoring/human_scoring_strategy.py

Purpose:
    Implement the final ranking formulas for coherence, ambiguity, style, and
    overall puzzle quality.

Inputs:
    - `PuzzleCandidate`
    - `VerificationResult`
    - `GenerationContext`

Outputs:
    - `PuzzleScore`

Why this is intentionally unimplemented:
    Final puzzle ranking is part of the project-defining quality logic and
    should remain under direct human ownership.

TODO[HUMAN_CORE]:
    Implement the final coherence, ambiguity, and style scoring formulas.

TODO[HUMAN_RESEARCH]:
    Decide how scores should be calibrated, benchmarked, and compared offline.

TODO[HUMAN_HEURISTIC]:
    Define the human-likeness/style criteria that separate acceptable puzzles
    from genuinely strong ones.

Acceptance criteria:
    - Produces interpretable component scores and a stable ranking output.
    - Supports offline evaluation and ablation studies.
    - Penalizes ambiguity without over-rejecting creative but fair puzzles.
"""

from __future__ import annotations

from app.domain.value_objects import GenerationContext
from app.schemas.puzzle_models import PuzzleCandidate, PuzzleScore, VerificationResult
from app.scoring.base import BasePuzzleScorer


class HumanOwnedPuzzleScorer(BasePuzzleScorer):
    """Placeholder for the final puzzle ranking strategy."""

    scorer_name = "human_owned_puzzle_scorer"

    def score(
        self,
        puzzle: PuzzleCandidate,
        verification: VerificationResult,
        context: GenerationContext,
    ) -> PuzzleScore:
        raise NotImplementedError(
            "TODO[HUMAN_CORE]: implement the human-owned final scoring strategy."
        )
