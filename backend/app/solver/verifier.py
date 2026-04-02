"""Verification strategies for puzzle candidates."""

from __future__ import annotations

from collections import Counter

from app.core.enums import RejectReasonCode, VerificationDecision
from app.core.stage1_quality import STAGE1_THRESHOLDS
from app.core.stage3_style_policy import STAGE3_STYLE_VERIFIER_THRESHOLDS
from app.domain.value_objects import GenerationContext
from app.schemas.evaluation_models import EnsembleSolverResult
from app.schemas.puzzle_models import (
    PuzzleCandidate,
    RejectReason,
    SolverResult,
    VerificationResult,
)
from app.scoring.style_analysis import BaseStyleAnalyzer, HumanStyleAnalyzer
from app.solver.ambiguity_models import build_mock_ambiguity_report
from app.solver.base import BaseAmbiguityEvaluator, BasePuzzleVerifier, BaseSolverBackend
from app.solver.ensemble import EnsembleSolverCoordinator
from app.solver.human_ambiguity_strategy import HumanAmbiguityEvaluator


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
                    message=(
                        "Baseline ambiguity scaffold flagged the puzzle for "
                        "elevated ambiguity risk."
                    ),
                    metadata={
                        "risk_level": ambiguity_report.risk_level.value,
                        "triggered_flags": ambiguity_report.evidence.triggered_flags,
                        "baseline_only": True,
                    },
                )
            )
        return VerificationResult(
            passed=not ambiguity_report.reject_recommended,
            decision=(
                VerificationDecision.REJECT
                if ambiguity_report.reject_recommended
                else VerificationDecision.ACCEPT
            ),
            reject_reasons=reject_reasons,
            leakage_estimate=ambiguity_score,
            ambiguity_score=ambiguity_score,
            summary_metrics={"board_pressure": ambiguity_score},
            evidence_refs=["ambiguity_report"] if reject_reasons else [],
            ambiguity_report=ambiguity_report,
            ensemble_result=ensemble_result,
            notes=[
                (
                    "Baseline ambiguity evaluation converts solver disagreement "
                    "into structured placeholder evidence."
                ),
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
            self._solver_ensemble.solve(puzzle, context)
            if self._solver_ensemble is not None
            else None
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
            (
                "Baseline verifier performs structural checks and delegates "
                "ambiguity scoring to a stub evaluator."
            )
        ]
        notes.extend(ambiguity_result.notes)

        return VerificationResult(
            passed=passed,
            decision=VerificationDecision.ACCEPT if passed else VerificationDecision.REJECT,
            reject_reasons=reject_reasons,
            leakage_estimate=ambiguity_result.leakage_estimate,
            ambiguity_score=ambiguity_result.ambiguity_score,
            warning_flags=ambiguity_result.warning_flags,
            summary_metrics=ambiguity_result.summary_metrics,
            evidence_refs=ambiguity_result.evidence_refs,
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
    """Stage 1 internal verifier for mixed semantic/lexical/theme puzzles."""

    verifier_name = "internal_puzzle_verifier"

    def __init__(
        self,
        solver: BaseSolverBackend,
        solver_ensemble: EnsembleSolverCoordinator | None = None,
        ambiguity_evaluator: BaseAmbiguityEvaluator | None = None,
        style_analyzer: BaseStyleAnalyzer | None = None,
    ) -> None:
        self._solver = solver
        self._solver_ensemble = solver_ensemble
        self._ambiguity_evaluator = ambiguity_evaluator or HumanAmbiguityEvaluator()
        self._style_analyzer = style_analyzer or HumanStyleAnalyzer()

    def verify(self, puzzle: PuzzleCandidate, context: GenerationContext) -> VerificationResult:
        reject_reasons: list[RejectReason] = []
        warning_flags: list[str] = []
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

        if len(puzzle.groups) != 4:
            reject_reasons.append(
                RejectReason(
                    code=RejectReasonCode.INSUFFICIENT_GROUPS,
                    message="Puzzle must contain exactly four groups.",
                    metadata={"group_count": len(puzzle.groups)},
                )
            )

        solver_result = self._solver.solve(puzzle, context)
        ensemble_result = (
            self._solver_ensemble.solve(puzzle, context)
            if self._solver_ensemble is not None
            else None
        )
        ambiguity_result = self._ambiguity_evaluator.evaluate(
            puzzle,
            solver_result,
            context,
            ensemble_result=ensemble_result,
        )
        reject_reasons.extend(ambiguity_result.reject_reasons)
        warning_flags.extend(ambiguity_result.warning_flags)

        if not solver_result.solved:
            reject_reasons.append(
                RejectReason(
                    code=RejectReasonCode.LOW_COHERENCE,
                    message="Primary solver could not recover the intended grouping.",
                    metadata={
                        "solver_backend": solver_result.backend_name,
                        "solver_confidence": solver_result.confidence,
                    },
                )
            )

        group_summaries = (
            ambiguity_result.ambiguity_report.evidence.group_coherence_summaries
            if ambiguity_result.ambiguity_report is not None
            else []
        )
        weak_groups_reject = [
            summary.group_label
            for summary in group_summaries
            if summary.support_score < STAGE1_THRESHOLDS.weak_group_support_reject
        ]
        weak_groups_borderline = [
            summary.group_label
            for summary in group_summaries
            if summary.support_score < STAGE1_THRESHOLDS.weak_group_support_borderline
        ]
        if weak_groups_reject:
            reject_reasons.append(
                RejectReason(
                    code=RejectReasonCode.LOW_COHERENCE,
                    message="One or more groups have unusably weak Stage 1 support.",
                    metadata={"weak_groups": weak_groups_reject},
                )
            )
        elif weak_groups_borderline:
            warning_flags.append("weak_group_support")

        if ensemble_result is not None and ensemble_result.agreement_summary.disagreement_flags:
            warning_flags.append("solver_ensemble_disagreement")

        decision = ambiguity_result.decision
        if reject_reasons:
            decision = VerificationDecision.REJECT
        elif decision is VerificationDecision.BORDERLINE or weak_groups_borderline:
            decision = VerificationDecision.BORDERLINE
        else:
            decision = VerificationDecision.ACCEPT

        summary_metrics = dict(ambiguity_result.summary_metrics)
        if ensemble_result is not None:
            summary_metrics["solver_agreement_ratio"] = (
                ensemble_result.agreement_summary.agreement_ratio
            )

        evidence_refs = list(ambiguity_result.evidence_refs)
        evidence_refs.extend(f"group:{label}" for label in weak_groups_borderline)
        if ensemble_result is not None and ensemble_result.agreement_summary.disagreement_flags:
            evidence_refs.append("ensemble:disagreement")

        notes = [
            (
                "InternalPuzzleVerifier applies the repository's Stage 1 structural, "
                "ambiguity, and group-support policy."
            )
        ]
        notes.extend(ambiguity_result.notes)

        provisional_result = VerificationResult(
            passed=decision is not VerificationDecision.REJECT,
            decision=decision,
            reject_reasons=reject_reasons,
            warning_flags=sorted(set(warning_flags)),
            leakage_estimate=ambiguity_result.leakage_estimate,
            ambiguity_score=ambiguity_result.ambiguity_score,
            summary_metrics=summary_metrics,
            evidence_refs=sorted(set(evidence_refs)),
            ambiguity_report=ambiguity_result.ambiguity_report,
            ensemble_result=ensemble_result,
            notes=notes,
            metadata={
                "solver_backend": solver_result.backend_name,
                "solver_notes": solver_result.notes,
                "solver_confidence": solver_result.confidence,
                "decision": decision.value,
            },
        )
        style_analysis = self._style_analyzer.analyze(puzzle, provisional_result, context)
        board_style_summary = style_analysis.board_style_summary
        if board_style_summary is not None:
            summary_metrics["style_alignment_score"] = board_style_summary.style_alignment_score
            summary_metrics["formulaic_mix_score"] = float(
                board_style_summary.metrics.get("formulaic_mix_score", 0.0)
            )
            summary_metrics["family_repetition_risk"] = float(
                board_style_summary.metrics.get("family_repetition_risk", 0.0)
            )
            summary_metrics["editorial_flatness_score"] = float(
                board_style_summary.metrics.get("editorial_flatness_score", 0.0)
            )
            summary_metrics["surface_wordplay_score"] = float(
                board_style_summary.metrics.get("surface_wordplay_score", 0.0)
            )
            summary_metrics["microtheme_smallness"] = float(
                board_style_summary.metrics.get("microtheme_smallness", 0.0)
            )
            summary_metrics["label_naturalness_score"] = float(
                board_style_summary.metrics.get("label_naturalness_score", 0.0)
            )
            summary_metrics["earned_wordplay_score"] = float(
                board_style_summary.metrics.get("earned_wordplay_score", 0.0)
            )
            summary_metrics["editorial_payoff_score"] = float(
                board_style_summary.metrics.get("editorial_payoff_score", 0.0)
            )
            if (
                board_style_summary.monotony_score
                >= STAGE3_STYLE_VERIFIER_THRESHOLDS.monotony_warning_threshold
            ):
                warning_flags.append("style_monotony")
            if (
                board_style_summary.metrics.get("formulaic_mix_score", 0.0)
                >= STAGE3_STYLE_VERIFIER_THRESHOLDS.formulaic_mix_warning_threshold
            ):
                warning_flags.append("too_formulaic")
            if (
                board_style_summary.metrics.get("family_repetition_risk", 0.0)
                >= STAGE3_STYLE_VERIFIER_THRESHOLDS.family_repetition_warning_threshold
            ):
                warning_flags.append("family_repetition")
            if (
                board_style_summary.metrics.get("surface_wordplay_score", 0.0)
                >= STAGE3_STYLE_VERIFIER_THRESHOLDS.surface_wordplay_warning_threshold
            ):
                warning_flags.append("overly_surface_wordplay")
            if (
                board_style_summary.metrics.get("microtheme_smallness", 0.0)
                >= STAGE3_STYLE_VERIFIER_THRESHOLDS.microtheme_trivia_warning_threshold
            ):
                warning_flags.append("microtheme_trivia_smallness")
            if (
                1.0 - board_style_summary.metrics.get("label_naturalness_score", 1.0)
                >= STAGE3_STYLE_VERIFIER_THRESHOLDS.weak_label_naturalness_warning_threshold
            ):
                warning_flags.append("weak_label_naturalness")
            if style_analysis.out_of_band_flags:
                warning_flags.append("style_out_of_band")
                evidence_refs.extend(f"style:{flag}" for flag in style_analysis.out_of_band_flags)
            if (
                not reject_reasons
                and decision is VerificationDecision.ACCEPT
                and (
                    (
                        board_style_summary.style_alignment_score
                        < STAGE3_STYLE_VERIFIER_THRESHOLDS.low_alignment_borderline_threshold
                        and board_style_summary.mechanism_mix_profile.unique_group_type_count
                        <= STAGE3_STYLE_VERIFIER_THRESHOLDS.single_mechanism_unique_type_count
                    )
                    or (
                        board_style_summary.metrics.get("editorial_flatness_score", 0.0)
                        >= STAGE3_STYLE_VERIFIER_THRESHOLDS.editorial_flatness_borderline_threshold
                        and board_style_summary.metrics.get("editorial_payoff_score", 0.0) < 0.6
                    )
                )
            ):
                decision = VerificationDecision.BORDERLINE
                notes.append(
                    "Stage 3 editorial policy downgraded an otherwise acceptable "
                    "board to borderline due to editorial flatness or weak style support."
                )
            if (
                not reject_reasons
                and decision is VerificationDecision.BORDERLINE
                and "weak_group_support" in warning_flags
                and summary_metrics.get("board_pressure", 1.0) <= 0.18
                and summary_metrics.get("max_alternative_group_pressure", 1.0) < 0.2
                and summary_metrics.get("max_cross_group_pressure", 1.0) < 0.2
                and summary_metrics.get("weakest_group_support", 0.0) >= 0.65
                and board_style_summary.mechanism_mix_profile.phonetic_group_count >= 1
                and board_style_summary.metrics.get("earned_wordplay_score", 0.0) >= 0.4
                and board_style_summary.metrics.get("editorial_payoff_score", 0.0) >= 0.78
            ):
                decision = VerificationDecision.ACCEPT
                notes.append(
                    "Stage 3 editorial policy restored a marginal weak-support phonetic "
                    "board to accept because the structural risk stayed low and the "
                    "wordplay payoff was meaningfully stronger."
                )
            if (
                len(style_analysis.out_of_band_flags)
                >= STAGE3_STYLE_VERIFIER_THRESHOLDS.severe_out_of_band_flag_count
            ):
                warning_flags.append("style_drift")

        return VerificationResult(
            passed=decision is not VerificationDecision.REJECT,
            decision=decision,
            reject_reasons=reject_reasons,
            warning_flags=sorted(set(warning_flags)),
            leakage_estimate=ambiguity_result.leakage_estimate,
            ambiguity_score=ambiguity_result.ambiguity_score,
            summary_metrics=summary_metrics,
            evidence_refs=sorted(set(evidence_refs)),
            ambiguity_report=ambiguity_result.ambiguity_report,
            ensemble_result=ensemble_result,
            style_analysis=style_analysis,
            notes=notes,
            metadata={
                "solver_backend": solver_result.backend_name,
                "solver_notes": solver_result.notes,
                "solver_confidence": solver_result.confidence,
                "decision": decision.value,
            },
        )
