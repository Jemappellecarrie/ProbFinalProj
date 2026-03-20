"""Human-owned final scoring strategy.

File location:
    backend/app/scoring/human_scoring_strategy.py

Scoring formula:
    coherence       = mean(group.confidence for each group)   [0, 1]
    ambiguity_pen   = verification.ambiguity_score            [0, 1]
    human_likeness  = 0.5 * group_type_diversity + 0.5 * word_length_score
    overall         = max(0, 0.5 * coherence + 0.3 * human_likeness - 0.2 * ambiguity_pen)
"""

from __future__ import annotations

import numpy as np

from app.domain.value_objects import GenerationContext
from app.schemas.puzzle_models import PuzzleCandidate, PuzzleScore, VerificationResult
from app.scoring.base import BasePuzzleScorer
from app.scoring.style_analysis import BaselineStyleAnalyzer


class HumanOwnedPuzzleScorer(BasePuzzleScorer):
    """Embedding-coherence and diversity scorer for the human pipeline."""

    scorer_name = "human_owned_puzzle_scorer"

    def __init__(self, style_analyzer: BaselineStyleAnalyzer | None = None) -> None:
        self._style_analyzer = style_analyzer or BaselineStyleAnalyzer()

    def score(
        self,
        puzzle: PuzzleCandidate,
        verification: VerificationResult,
        context: GenerationContext,
    ) -> PuzzleScore:
        group_confidences = [g.confidence for g in puzzle.groups]
        coherence = float(np.mean(group_confidences)) if group_confidences else 0.0

        ambiguity_pen = verification.ambiguity_score

        # human_likeness: group type diversity + avg word length signal
        group_types = [g.group_type for g in puzzle.groups]
        type_diversity = len(set(group_types)) / max(len(group_types), 1)
        avg_word_length = (
            sum(len(w) for w in puzzle.board_words) / max(len(puzzle.board_words), 1)
        )
        length_score = min(1.0, avg_word_length / 8.0)
        human_likeness = 0.5 * type_diversity + 0.5 * length_score

        overall = max(
            0.0, 0.5 * coherence + 0.3 * human_likeness - 0.2 * ambiguity_pen
        )

        style_analysis = self._style_analyzer.analyze(puzzle, verification, context)

        return PuzzleScore(
            scorer_name=self.scorer_name,
            overall=round(overall, 4),
            coherence=round(coherence, 4),
            ambiguity_penalty=round(ambiguity_pen, 4),
            human_likeness=round(human_likeness, 4),
            style_analysis=style_analysis,
            components={
                "coherence": round(coherence, 4),
                "ambiguity_penalty": round(ambiguity_pen, 4),
                "type_diversity": round(type_diversity, 4),
                "length_score": round(length_score, 4),
                "human_likeness": round(human_likeness, 4),
            },
            notes=[
                "coherence = mean pairwise cosine similarity across groups",
                "human_likeness = 0.5 * group_type_diversity + 0.5 * word_length_score",
                "overall = 0.5 * coherence + 0.3 * human_likeness - 0.2 * ambiguity_penalty",
            ],
        )
