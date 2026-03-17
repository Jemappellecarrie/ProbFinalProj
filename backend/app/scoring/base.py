"""Base classes for scoring strategies."""

from __future__ import annotations

from abc import ABC

from app.domain.protocols import PuzzleScorer


class BasePuzzleScorer(PuzzleScorer, ABC):
    """Convenience base class for scorers."""

    scorer_name = "base_puzzle_scorer"
