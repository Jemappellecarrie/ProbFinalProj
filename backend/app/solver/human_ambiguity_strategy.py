"""Human-owned ambiguity and leakage evaluation strategy.

File location:
    backend/app/solver/human_ambiguity_strategy.py

Purpose:
    Evaluate whether a composed puzzle permits alternative valid groupings or
    leaks enough signal across groups to feel unfair or unlike the target style.

Inputs:
    - `PuzzleCandidate`
    - `SolverResult`
    - `GenerationContext`
    - optional `EnsembleSolverResult`

Outputs:
    - `VerificationResult` with ambiguity metrics, rejection reasons, and notes.

Why this is intentionally unimplemented:
    Cross-group ambiguity reasoning is a project-defining differentiator and
    should remain human-owned rather than silently approximated.

TODO[HUMAN_CORE]:
    Implement alternative-grouping detection and leakage estimation.

TODO[HUMAN_RESEARCH]:
    Define the search strategy, solver ensemble, or heuristic probes used to
    detect ambiguous regroupings.

TODO[HUMAN_HEURISTIC]:
    Decide how to translate leakage signals into rejection or penalty behavior.

Acceptance criteria:
    - Distinguishes benign overlap from puzzle-breaking ambiguity.
    - Produces interpretable diagnostics for offline review.
    - Integrates cleanly with verifier and scorer interfaces.
"""

from __future__ import annotations

from app.domain.value_objects import GenerationContext
from app.schemas.evaluation_models import EnsembleSolverResult
from app.schemas.puzzle_models import PuzzleCandidate, SolverResult, VerificationResult
from app.solver.base import BaseAmbiguityEvaluator


class HumanAmbiguityEvaluator(BaseAmbiguityEvaluator):
    """Placeholder for the final ambiguity evaluator."""

    evaluator_name = "human_ambiguity_evaluator"

    def evaluate(
        self,
        puzzle: PuzzleCandidate,
        solver_result: SolverResult,
        context: GenerationContext,
        ensemble_result: EnsembleSolverResult | None = None,
    ) -> VerificationResult:
        raise NotImplementedError(
            "TODO[HUMAN_CORE]: implement ambiguity and leakage evaluation."
        )
