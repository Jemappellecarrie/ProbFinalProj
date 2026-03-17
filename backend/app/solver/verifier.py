"""Verification strategies for puzzle candidates."""

from __future__ import annotations

from collections import Counter

from app.core.enums import RejectReasonCode
from app.domain.value_objects import GenerationContext
from app.schemas.puzzle_models import PuzzleCandidate, RejectReason, SolverResult, VerificationResult
from app.solver.base import BaseAmbiguityEvaluator, BasePuzzleVerifier, BaseSolverBackend


class BaselineAmbiguityEvaluator(BaseAmbiguityEvaluator):
    """Simple ambiguity evaluator for demo mode."""

    evaluator_name = "baseline_ambiguity_evaluator"

    def evaluate(
        self,
        puzzle: PuzzleCandidate,
        solver_result: SolverResult,
        context: GenerationContext,
    ) -> VerificationResult:
        ambiguity_score = min(1.0, solver_result.alternative_groupings_detected * 0.25)
        return VerificationResult(
            passed=ambiguity_score < 0.5,
            leakage_estimate=ambiguity_score,
            ambiguity_score=ambiguity_score,
            notes=[
                "Baseline ambiguity evaluation uses solver-reported alternative grouping counts only.",
                "This is a transparent demo heuristic rather than the final logic.",
            ],
            metadata={"baseline_only": True},
        )


class BaselinePuzzleVerifier(BasePuzzleVerifier):
    """Demo verifier combining structural checks with a stub ambiguity evaluator."""

    verifier_name = "baseline_puzzle_verifier"

    def __init__(
        self,
        solver: BaseSolverBackend,
        ambiguity_evaluator: BaseAmbiguityEvaluator | None = None,
    ) -> None:
        self._solver = solver
        self._ambiguity_evaluator = ambiguity_evaluator or BaselineAmbiguityEvaluator()

    def verify(self, puzzle: PuzzleCandidate, context: GenerationContext) -> VerificationResult:
        reject_reasons: list[RejectReason] = []
        word_counts = Counter(puzzle.board_words)
        duplicates = sorted(word for word, count in word_counts.items() if count > 1)
        if duplicates:
            reject_reasons.append(
                RejectReason(
                    code=RejectReasonCode.DUPLICATE_WORD,
                    message="Puzzle contains duplicate board words.",
                    metadata={"duplicates": duplicates},
                )
            )

        solver_result = self._solver.solve(puzzle, context)
        ambiguity_result = self._ambiguity_evaluator.evaluate(puzzle, solver_result, context)
        reject_reasons.extend(ambiguity_result.reject_reasons)

        passed = not reject_reasons and solver_result.solved and ambiguity_result.passed
        notes = [
            "Baseline verifier performs structural checks and delegates ambiguity scoring to a stub evaluator."
        ]
        notes.extend(ambiguity_result.notes)

        return VerificationResult(
            passed=passed,
            reject_reasons=reject_reasons,
            leakage_estimate=ambiguity_result.leakage_estimate,
            ambiguity_score=ambiguity_result.ambiguity_score,
            notes=notes,
            metadata={
                "solver_backend": solver_result.backend_name,
                "solver_notes": solver_result.notes,
                "baseline_only": True,
            },
        )


class InternalPuzzleVerifier(BasePuzzleVerifier):
    """Placeholder for the final human-owned internal verifier.

    File location:
        backend/app/solver/verifier.py

    TODO[HUMAN_CORE]:
        Implement full puzzle verification including uniqueness, leakage,
        alternative grouping analysis, and fairness checks.

    TODO[HUMAN_HEURISTIC]:
        Define structural and stylistic rejection criteria that reflect the
        intended puzzle standard rather than demo constraints.

    Acceptance criteria:
        - Rejects structurally invalid or ambiguity-prone puzzles.
        - Emits actionable diagnostics for offline tuning.
        - Keeps the API contract stable as verification sophistication grows.
    """

    verifier_name = "internal_puzzle_verifier"

    def verify(self, puzzle: PuzzleCandidate, context: GenerationContext) -> VerificationResult:
        raise NotImplementedError(
            "TODO[HUMAN_CORE]: implement the human-owned internal puzzle verifier."
        )
