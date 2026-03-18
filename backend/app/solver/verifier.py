"""Verification strategies for puzzle candidates."""

from __future__ import annotations

from collections import Counter

from app.core.enums import RejectReasonCode
from app.domain.value_objects import GenerationContext
from app.schemas.evaluation_models import EnsembleSolverResult
from app.schemas.puzzle_models import PuzzleCandidate, RejectReason, SolverResult, VerificationResult
from app.solver.ambiguity_models import build_mock_ambiguity_report
from app.solver.base import BaseAmbiguityEvaluator, BasePuzzleVerifier, BaseSolverBackend
from app.solver.ensemble import EnsembleSolverCoordinator


class BaselineAmbiguityEvaluator(BaseAmbiguityEvaluator):
    """Structured but provisional ambiguity evaluator for demo mode."""

    evaluator_name = "baseline_ambiguity_evaluator"

    def evaluate(
        self,
        puzzle: PuzzleCandidate,
        solver_result: SolverResult,
        context: GenerationContext,
        ensemble_result: EnsembleSolverResult | None = None,
    ) -> VerificationResult:
        ambiguity_report = build_mock_ambiguity_report(puzzle, ensemble_result)
        ambiguity_score = ambiguity_report.penalty_hint
        reject_reasons: list[RejectReason] = []
        if ambiguity_report.reject_recommended:
            reject_reasons.append(
                RejectReason(
                    code=RejectReasonCode.AMBIGUOUS_GROUPING,
                    message="Baseline ambiguity scaffold flagged the puzzle for elevated ambiguity risk.",
                    metadata={
                        "risk_level": ambiguity_report.risk_level.value,
                        "triggered_flags": ambiguity_report.evidence.triggered_flags,
                        "baseline_only": True,
                    },
                )
            )
        return VerificationResult(
            passed=not ambiguity_report.reject_recommended,
            reject_reasons=reject_reasons,
            leakage_estimate=ambiguity_score,
            ambiguity_score=ambiguity_score,
            ambiguity_report=ambiguity_report,
            ensemble_result=ensemble_result,
            notes=[
                "Baseline ambiguity evaluation converts solver disagreement into structured placeholder evidence.",
                "This is a transparent demo scaffold rather than the final logic.",
            ],
            metadata={"baseline_only": True},
        )


class BaselinePuzzleVerifier(BasePuzzleVerifier):
    """Demo verifier combining structural checks with a stub ambiguity evaluator."""

    verifier_name = "baseline_puzzle_verifier"

    def __init__(
        self,
        solver: BaseSolverBackend,
        solver_ensemble: EnsembleSolverCoordinator | None = None,
        ambiguity_evaluator: BaseAmbiguityEvaluator | None = None,
    ) -> None:
        self._solver = solver
        self._solver_ensemble = solver_ensemble
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
        ensemble_result = (
            self._solver_ensemble.solve(puzzle, context) if self._solver_ensemble is not None else None
        )
        ambiguity_result = self._ambiguity_evaluator.evaluate(
            puzzle,
            solver_result,
            context,
            ensemble_result=ensemble_result,
        )
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
            ambiguity_report=ambiguity_result.ambiguity_report,
            ensemble_result=ensemble_result,
            notes=notes,
            metadata={
                "solver_backend": solver_result.backend_name,
                "solver_notes": solver_result.notes,
                "ensemble_summary": (
                    ensemble_result.agreement_summary.model_dump(mode="json")
                    if ensemble_result is not None
                    else None
                ),
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
