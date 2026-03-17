"""Mock solver backend used in demo mode."""

from __future__ import annotations

from app.domain.value_objects import GenerationContext
from app.schemas.puzzle_models import PuzzleCandidate, SolverResult
from app.solver.base import BaseSolverBackend


class MockSolverBackend(BaseSolverBackend):
    """Return the ground-truth puzzle grouping for demo verification."""

    backend_name = "mock_solver_backend"

    def solve(self, puzzle: PuzzleCandidate, context: GenerationContext) -> SolverResult:
        return SolverResult(
            backend_name=self.backend_name,
            solved=True,
            proposed_groups=[group.words for group in puzzle.groups],
            alternative_groupings_detected=0,
            notes=[
                "Baseline demo solver returns the composed grouping directly.",
                "This is not a substitute for a real ambiguity-aware solver.",
            ],
            raw_output={"baseline_only": True},
        )
