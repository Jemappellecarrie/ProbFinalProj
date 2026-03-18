"""Solver ensemble scaffold.

Role in pipeline:
    Run multiple solver adapters against the same puzzle and aggregate their
    agreement/disagreement into a typed summary that downstream verifier and
    evaluation layers can inspect.

Inputs:
    - `PuzzleCandidate`
    - `GenerationContext`
    - registered solver adapters

Outputs:
    - `EnsembleSolverResult`

Why core logic is intentionally deferred:
    Real solver weighting, confidence calibration, and acceptance policy are
    project-defining and remain human-owned. This module only provides the
    scaffold and a transparent baseline aggregation.

Acceptance criteria:
    - Supports 2+ solvers in principle.
    - Produces agreement/disagreement metadata in demo mode.
    - Avoids claiming that ensemble policy or solver confidence is final.
"""

from __future__ import annotations

from collections import Counter

from app.domain.value_objects import GenerationContext
from app.schemas.evaluation_models import (
    EnsembleSolverResult,
    SolverAgreementSummary,
    SolverDisagreementFlag,
    SolverVote,
)
from app.schemas.puzzle_models import PuzzleCandidate, SolverResult
from app.solver.registry import SolverRegistry


class EnsembleSolverCoordinator:
    """Aggregate multiple solver adapters into a typed ensemble result."""

    coordinator_name = "ensemble_solver_coordinator"

    def __init__(self, registry: SolverRegistry) -> None:
        self._registry = registry

    @staticmethod
    def _canonicalize(groups: list[list[str]]) -> tuple[tuple[str, ...], ...]:
        normalized_groups = [tuple(sorted(group)) for group in groups if group]
        return tuple(sorted(normalized_groups))

    def _matches_target(self, puzzle: PuzzleCandidate, result: SolverResult) -> bool:
        target = self._canonicalize([group.words for group in puzzle.groups])
        proposed = self._canonicalize(result.proposed_groups)
        return bool(proposed) and proposed == target

    def solve(self, puzzle: PuzzleCandidate, context: GenerationContext) -> EnsembleSolverResult:
        votes: list[SolverVote] = []
        proposed_signatures: Counter[tuple[tuple[str, ...], ...]] = Counter()

        for solver in self._registry.list_solvers():
            result = solver.solve(puzzle, context)
            matched_target = self._matches_target(puzzle, result)
            alternative_solution_proposed = bool(result.proposed_groups) and not matched_target
            signature = self._canonicalize(result.proposed_groups)
            if signature:
                proposed_signatures[signature] += 1

            votes.append(
                SolverVote(
                    solver_name=solver.backend_name,
                    matched_target_solution=matched_target,
                    alternative_solution_proposed=alternative_solution_proposed,
                    solved=result.solved,
                    confidence=result.confidence,
                    proposed_groups=result.proposed_groups,
                    notes=result.notes,
                    raw_output=result.raw_output,
                )
            )

        total_solvers = len(votes)
        matched_target_count = sum(1 for vote in votes if vote.matched_target_solution)
        alternative_solution_count = sum(1 for vote in votes if vote.alternative_solution_proposed)
        agreement_ratio = round(matched_target_count / total_solvers, 3) if total_solvers else 0.0

        disagreement_flags: list[SolverDisagreementFlag] = []
        if 0 < matched_target_count < total_solvers:
            disagreement_flags.append(SolverDisagreementFlag.TARGET_MISMATCH)
        if alternative_solution_count > 0:
            disagreement_flags.append(SolverDisagreementFlag.ALTERNATIVE_SOLUTION_PROPOSED)
        if len(proposed_signatures) > 1:
            disagreement_flags.append(SolverDisagreementFlag.STRUCTURAL_DISAGREEMENT)

        confidences = [vote.confidence for vote in votes if vote.confidence is not None]
        if confidences and max(confidences) - min(confidences) >= 0.5:
            disagreement_flags.append(SolverDisagreementFlag.CONFIDENCE_SPREAD)

        agreement_summary = SolverAgreementSummary(
            total_solvers=total_solvers,
            matched_target_count=matched_target_count,
            alternative_solution_count=alternative_solution_count,
            agreement_ratio=agreement_ratio,
            disagreement_flags=disagreement_flags,
            notes=[
                "Ensemble agreement is a scaffold metric only.",
                "Final solver weighting and acceptance policy remain human-owned.",
            ],
        )

        primary_solver_name = votes[0].solver_name if votes else None
        return EnsembleSolverResult(
            coordinator_name=self.coordinator_name,
            primary_solver_name=primary_solver_name,
            votes=votes,
            agreement_summary=agreement_summary,
            notes=[
                "Baseline ensemble aggregates registered solver adapters without learned weighting.",
            ],
            metadata={"solver_registry": self._registry.names(), "baseline_only": True},
        )
