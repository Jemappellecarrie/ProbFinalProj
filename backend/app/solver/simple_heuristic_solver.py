"""Baseline second solver used to exercise ensemble and ambiguity scaffolds.

This solver is intentionally weak. It exists to produce deterministic
agreement/disagreement scenarios for the quality-control pipeline without
pretending to solve puzzle verification.
"""

from __future__ import annotations

from app.domain.value_objects import GenerationContext
from app.schemas.puzzle_models import PuzzleCandidate, SolverResult
from app.solver.base import BaseSolverBackend


class SimpleHeuristicSolverBackend(BaseSolverBackend):
    """Deterministic low-quality solver for ensemble scaffolding."""

    backend_name = "simple_heuristic_solver_backend"

    @staticmethod
    def _checksum(words: list[str]) -> int:
        return sum(ord(character) for word in words for character in word)

    @staticmethod
    def _chunk(words: list[str]) -> list[list[str]]:
        return [words[index : index + 4] for index in range(0, min(len(words), 16), 4)]

    def solve(self, puzzle: PuzzleCandidate, context: GenerationContext) -> SolverResult:
        checksum = self._checksum(puzzle.board_words)
        mode = (context.seed if context.seed is not None else checksum) % 3

        if mode == 0:
            return SolverResult(
                backend_name=self.backend_name,
                solved=False,
                confidence=0.15,
                proposed_groups=[],
                alternative_groupings_detected=0,
                notes=[
                    "Baseline second solver abstained via a deterministic checksum gate.",
                    "This behavior exists only to exercise ensemble and batch scaffolding.",
                ],
                raw_output={"baseline_only": True, "mode": "abstain", "checksum": checksum},
            )

        if mode == 1:
            proposed_groups = self._chunk(list(puzzle.board_words))
            raw_mode = "board_quartiles"
        else:
            proposed_groups = self._chunk(sorted(puzzle.board_words))
            raw_mode = "alphabetical_quartiles"

        return SolverResult(
            backend_name=self.backend_name,
            solved=False,
            confidence=0.25,
            proposed_groups=proposed_groups,
            alternative_groupings_detected=mode,
            notes=[
                "Baseline second solver produced a deterministic alternative grouping.",
                "This is an intentionally low-quality heuristic, not a real solver.",
            ],
            raw_output={"baseline_only": True, "mode": raw_mode, "checksum": checksum},
        )
