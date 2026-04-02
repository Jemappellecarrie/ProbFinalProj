"""Stage 1 puzzle scoring and ranking breakdown."""

from __future__ import annotations

from statistics import mean

from app.core.enums import VerificationDecision
from app.core.stage1_quality import STAGE1_SCORING_WEIGHTS, clamp_unit
from app.core.stage3_style_policy import STAGE3_STYLE_SCORING_WEIGHTS
from app.domain.value_objects import GenerationContext
from app.schemas.puzzle_models import PuzzleCandidate, PuzzleScore, VerificationResult
from app.scoring.base import BasePuzzleScorer
from app.scoring.style_analysis import BaseStyleAnalyzer, HumanStyleAnalyzer


class HumanOwnedPuzzleScorer(BasePuzzleScorer):
    """Interpretable Stage 1 scorer for accepted and borderline puzzles."""

    scorer_name = "human_owned_puzzle_scorer"

    def __init__(self, style_analyzer: BaseStyleAnalyzer | None = None) -> None:
        self._style_analyzer = style_analyzer or HumanStyleAnalyzer()

    @staticmethod
    def _group_supports(verification: VerificationResult) -> list[float]:
        report = verification.ambiguity_report
        if report is None:
            return []
        return [summary.support_score for summary in report.evidence.group_coherence_summaries]

    @staticmethod
    def _shared_signal_density(verification: VerificationResult) -> float:
        report = verification.ambiguity_report
        if report is None:
            return 0.0
        values = []
        for summary in report.evidence.group_coherence_summaries:
            shared_signals = summary.metadata.get("shared_signals", [])
            values.append(min(1.0, len(shared_signals) / 2.0))
        return mean(values) if values else 0.0

    def score(
        self,
        puzzle: PuzzleCandidate,
        verification: VerificationResult,
        context: GenerationContext,
    ) -> PuzzleScore:
        style_analysis = verification.style_analysis or self._style_analyzer.analyze(
            puzzle, verification, context
        )
        group_supports = self._group_supports(verification)
        group_coherence = mean(group_supports) if group_supports else 0.0
        weakest_group_support = min(group_supports) if group_supports else 0.0
        board_balance = 1.0 - (
            (max(group_supports) - min(group_supports)) if len(group_supports) >= 2 else 0.0
        )
        evidence_quality = clamp_unit(
            (0.6 * self._shared_signal_density(verification))
            + (0.4 * (1.0 if group_supports else 0.0))
        )

        ambiguity_penalty = verification.ambiguity_score
        leakage_penalty = verification.leakage_estimate
        alternative_group_penalty = verification.summary_metrics.get(
            "max_alternative_group_pressure", 0.0
        )
        composer_ranking_score = float(puzzle.metadata.get("ranking_score", 0.0))
        board_style_summary = style_analysis.board_style_summary
        style_alignment_score = (
            board_style_summary.style_alignment_score if board_style_summary is not None else 0.0
        )
        style_metrics = board_style_summary.metrics if board_style_summary is not None else {}
        editorial_payoff_score = float(style_metrics.get("editorial_payoff_score", 0.0))
        label_naturalness_score = float(style_metrics.get("label_naturalness_score", 0.0))
        earned_wordplay_score = float(style_metrics.get("earned_wordplay_score", 0.0))
        formulaic_mix_score = float(style_metrics.get("formulaic_mix_score", 0.0))
        family_repetition_risk = float(style_metrics.get("family_repetition_risk", 0.0))
        surface_wordplay_score = float(style_metrics.get("surface_wordplay_score", 0.0))
        editorial_flatness_score = float(style_metrics.get("editorial_flatness_score", 0.0))
        microtheme_smallness = float(style_metrics.get("microtheme_smallness", 0.0))
        repeated_pattern_family_score = float(
            style_metrics.get("repeated_pattern_family_score", 0.0)
        )
        style_alignment_bonus = (
            STAGE3_STYLE_SCORING_WEIGHTS.style_alignment_bonus_weight
            * style_alignment_score
            * max(0.35, editorial_payoff_score)
        )
        editorial_payoff_bonus = (
            STAGE3_STYLE_SCORING_WEIGHTS.editorial_payoff_bonus_weight * editorial_payoff_score
        )
        label_naturalness_bonus = (
            STAGE3_STYLE_SCORING_WEIGHTS.label_naturalness_bonus_weight * label_naturalness_score
        )
        wordplay_bonus = STAGE3_STYLE_SCORING_WEIGHTS.wordplay_bonus_weight * (
            earned_wordplay_score * max(0.4, editorial_payoff_score)
        )
        phonetic_showcase_bonus = STAGE3_STYLE_SCORING_WEIGHTS.phonetic_showcase_bonus_weight * (
            float(style_metrics.get("phonetic_group_count", 0.0)) * earned_wordplay_score / 2.0
        )
        mixed_mechanism_bonus = STAGE3_STYLE_SCORING_WEIGHTS.mixed_mechanism_bonus_weight * (
            (float(style_metrics.get("unique_group_type_count", 0.0)) / 4.0)
            if (
                board_style_summary is not None
                and formulaic_mix_score < 0.85
                and family_repetition_risk < 0.85
                and editorial_flatness_score < 0.72
                and editorial_payoff_score >= 0.6
            )
            else 0.0
        )
        monotony_penalty = STAGE3_STYLE_SCORING_WEIGHTS.monotony_penalty_weight * (
            board_style_summary.monotony_score if board_style_summary is not None else 0.0
        )
        editorial_flags = (
            set(board_style_summary.editorial_flags) if board_style_summary is not None else set()
        )
        non_editorial_out_of_band_count = len(
            [flag for flag in style_analysis.out_of_band_flags if flag not in editorial_flags]
        )
        out_of_band_penalty = STAGE3_STYLE_SCORING_WEIGHTS.out_of_band_penalty_weight * (
            non_editorial_out_of_band_count
        )
        formulaic_mix_penalty = STAGE3_STYLE_SCORING_WEIGHTS.formulaic_mix_penalty_weight * max(
            0.0, formulaic_mix_score - 0.55
        )
        family_repetition_penalty = (
            STAGE3_STYLE_SCORING_WEIGHTS.family_repetition_penalty_weight
            * max(0.0, family_repetition_risk - 0.45)
        )
        surface_wordplay_penalty = (
            STAGE3_STYLE_SCORING_WEIGHTS.surface_wordplay_penalty_weight
            * max(0.0, surface_wordplay_score - 0.7)
        )
        editorial_flatness_penalty = (
            STAGE3_STYLE_SCORING_WEIGHTS.editorial_flatness_penalty_weight
            * max(0.0, editorial_flatness_score - 0.55)
        )
        microtheme_overuse_penalty = (
            STAGE3_STYLE_SCORING_WEIGHTS.microtheme_overuse_penalty_weight
            * max(0.0, microtheme_smallness - 0.6)
        )
        repeated_pattern_family_penalty = (
            STAGE3_STYLE_SCORING_WEIGHTS.repeated_pattern_family_penalty_weight
            * repeated_pattern_family_score
        )
        mild_borderline = (
            verification.decision is VerificationDecision.BORDERLINE
            and ambiguity_penalty <= 0.18
            and leakage_penalty <= 0.12
            and alternative_group_penalty <= 0.0
            and weakest_group_support >= 0.65
            and editorial_payoff_score >= 0.65
        )
        decision_penalty = (
            0.2
            if verification.decision is VerificationDecision.REJECT
            else (
                0.03
                if mild_borderline
                else (0.05 if verification.decision is VerificationDecision.BORDERLINE else 0.0)
            )
        )

        overall = clamp_unit(
            (
                STAGE1_SCORING_WEIGHTS.coherence_weight * group_coherence
                + STAGE1_SCORING_WEIGHTS.board_balance_weight * board_balance
                + STAGE1_SCORING_WEIGHTS.evidence_quality_weight * evidence_quality
                + STAGE1_SCORING_WEIGHTS.weakest_group_weight * weakest_group_support
                + style_alignment_bonus
                + editorial_payoff_bonus
                + label_naturalness_bonus
                + wordplay_bonus
                + phonetic_showcase_bonus
                + mixed_mechanism_bonus
            )
            - (
                STAGE1_SCORING_WEIGHTS.ambiguity_penalty_weight * ambiguity_penalty
                + STAGE1_SCORING_WEIGHTS.leakage_penalty_weight * leakage_penalty
                + STAGE1_SCORING_WEIGHTS.alternative_penalty_weight * alternative_group_penalty
                + monotony_penalty
                + out_of_band_penalty
                + formulaic_mix_penalty
                + family_repetition_penalty
                + surface_wordplay_penalty
                + editorial_flatness_penalty
                + microtheme_overuse_penalty
                + repeated_pattern_family_penalty
                + decision_penalty
            )
        )

        return PuzzleScore(
            scorer_name=self.scorer_name,
            overall=round(overall, 4),
            coherence=round(group_coherence, 4),
            ambiguity_penalty=round(ambiguity_penalty, 4),
            human_likeness=style_analysis.nyt_likeness.score,
            style_analysis=style_analysis,
            components={
                "group_coherence": round(group_coherence, 4),
                "board_balance": round(board_balance, 4),
                "evidence_quality": round(evidence_quality, 4),
                "weakest_group_support": round(weakest_group_support, 4),
                "ambiguity_penalty": round(ambiguity_penalty, 4),
                "leakage_penalty": round(leakage_penalty, 4),
                "alternative_group_penalty": round(alternative_group_penalty, 4),
                "composer_ranking_score": round(composer_ranking_score, 4),
                "style_alignment_bonus": round(style_alignment_bonus, 4),
                "editorial_payoff_bonus": round(editorial_payoff_bonus, 4),
                "label_naturalness_bonus": round(label_naturalness_bonus, 4),
                "wordplay_bonus": round(wordplay_bonus, 4),
                "phonetic_showcase_bonus": round(phonetic_showcase_bonus, 4),
                "mixed_mechanism_bonus": round(mixed_mechanism_bonus, 4),
                "style_monotony_penalty": round(monotony_penalty, 4),
                "style_out_of_band_penalty": round(out_of_band_penalty, 4),
                "formulaic_mix_penalty": round(formulaic_mix_penalty, 4),
                "family_repetition_penalty": round(family_repetition_penalty, 4),
                "surface_wordplay_penalty": round(surface_wordplay_penalty, 4),
                "editorial_flatness_penalty": round(editorial_flatness_penalty, 4),
                "microtheme_overuse_penalty": round(microtheme_overuse_penalty, 4),
                "repeated_pattern_family_penalty": round(repeated_pattern_family_penalty, 4),
                "decision_penalty": round(decision_penalty, 4),
            },
            notes=[
                "Stage 1 scorer favors coherent boards and penalizes ambiguity pressure.",
                (
                    "Stage 3 style hooks now treat editorial payoff as primary and "
                    "mechanism balance as a conditional bonus rather than a proxy for quality."
                ),
            ],
        )
