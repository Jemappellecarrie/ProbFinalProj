"""Interpretable style-analysis strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import Counter
from statistics import mean, pstdev

from app.core.editorial_quality import (
    build_editorial_family_metadata,
    group_earned_wordplay_score,
    group_is_clue_like_label,
    group_is_taxonomy_like_label,
    group_microtheme_smallness,
    group_phrase_template_payoff_score,
    group_surface_wordplay_score,
)
from app.core.enums import GroupType
from app.core.stage1_quality import clamp_unit
from app.core.stage3_style_policy import STAGE3_STYLE_VERIFIER_THRESHOLDS
from app.domain.value_objects import GenerationContext
from app.schemas.evaluation_models import (
    BoardStyleSummary,
    GroupStyleSummary,
    MechanismMixProfile,
    NYTLikenessPlaceholderScore,
    PuzzleArchetypeSummary,
    StyleAnalysisReport,
    StyleMetricComparison,
    StyleSignal,
)
from app.schemas.puzzle_models import PuzzleCandidate, VerificationResult
from app.scoring.calibration import compare_metric_dict_to_targets, load_style_targets

GENERIC_LABELS = {"thing", "things", "item", "items", "stuff", "words"}


class BaseStyleAnalyzer(ABC):
    """Strategy interface for provisional and calibrated style analyzers."""

    analyzer_name = "base_style_analyzer"

    @abstractmethod
    def analyze(
        self,
        puzzle: PuzzleCandidate,
        verification: VerificationResult,
        context: GenerationContext,
    ) -> StyleAnalysisReport:
        raise NotImplementedError


class BaselineStyleAnalyzer(BaseStyleAnalyzer):
    """Transparent placeholder analyzer for demo mode."""

    analyzer_name = "baseline_style_analyzer"

    def analyze(
        self,
        puzzle: PuzzleCandidate,
        verification: VerificationResult,
        context: GenerationContext,
    ) -> StyleAnalysisReport:
        group_types = [group.group_type for group in puzzle.groups]
        unique_group_type_count = len(set(group_types))
        lexical_or_phonetic_count = sum(
            1 for group_type in group_types if group_type in {GroupType.LEXICAL, GroupType.PHONETIC}
        )
        phrase_word_count = sum(1 for word in puzzle.board_words if " " in word or "-" in word)
        mechanism_counts = Counter(group_type.value for group_type in group_types)
        mechanism_mix_profile = MechanismMixProfile(
            counts=dict(sorted(mechanism_counts.items())),
            shares={
                key: round(value / max(len(group_types), 1), 4)
                for key, value in sorted(mechanism_counts.items())
            },
            unique_group_type_count=unique_group_type_count,
            semantic_group_count=mechanism_counts.get(GroupType.SEMANTIC.value, 0),
            lexical_group_count=mechanism_counts.get(GroupType.LEXICAL.value, 0),
            phonetic_group_count=mechanism_counts.get(GroupType.PHONETIC.value, 0),
            theme_group_count=mechanism_counts.get(GroupType.THEME.value, 0),
            wordplay_group_count=(
                mechanism_counts.get(GroupType.LEXICAL.value, 0)
                + mechanism_counts.get(GroupType.PHONETIC.value, 0)
            ),
            mixed_board=unique_group_type_count > 1,
        )

        archetype_label = "balanced_demo_mix" if unique_group_type_count >= 3 else "narrow_demo_mix"
        placeholder_score = round(
            min(
                1.0,
                0.2
                + (unique_group_type_count * 0.15)
                + (0.1 if GroupType.THEME in group_types else 0.0)
                + (0.05 if GroupType.PHONETIC in group_types else 0.0)
                - (verification.ambiguity_score * 0.1),
            ),
            3,
        )
        metrics = {
            "unique_group_type_count": float(unique_group_type_count),
            "wordplay_group_count": float(mechanism_mix_profile.wordplay_group_count),
            "ambiguity_score": float(verification.ambiguity_score),
            "style_alignment_score": placeholder_score,
        }

        return StyleAnalysisReport(
            analyzer_name=self.analyzer_name,
            archetype=PuzzleArchetypeSummary(
                label=archetype_label,
                rationale=(
                    "Baseline archetype label is derived from group-type diversity and does not "
                    "measure real editorial style."
                ),
                flags=[
                    "contains_theme_group" if GroupType.THEME in group_types else "no_theme_group",
                    (
                        "contains_wordplay_group"
                        if GroupType.PHONETIC in group_types
                        else "no_wordplay_group"
                    ),
                ],
            ),
            nyt_likeness=NYTLikenessPlaceholderScore(
                score=placeholder_score,
                notes=[
                    "Placeholder score is for debugging and batch comparisons only.",
                    "TODO[HUMAN_CORE]: replace with real style calibration.",
                ],
            ),
            signals=[
                StyleSignal(
                    signal_name="group_type_diversity",
                    value=float(unique_group_type_count),
                    interpretation="Number of distinct generator families present in the puzzle.",
                    source="baseline_style_analyzer",
                ),
                StyleSignal(
                    signal_name="theme_presence",
                    value=1.0 if GroupType.THEME in group_types else 0.0,
                    interpretation="Whether a theme/trivia group is present.",
                    source="baseline_style_analyzer",
                ),
                StyleSignal(
                    signal_name="wordplay_presence",
                    value=1.0 if GroupType.PHONETIC in group_types else 0.0,
                    interpretation="Whether a phonetic/wordplay group is present.",
                    source="baseline_style_analyzer",
                ),
                StyleSignal(
                    signal_name="mechanical_pattern_share",
                    value=round(lexical_or_phonetic_count / max(len(group_types), 1), 3),
                    interpretation="Rough share of lexical/phonetic pattern groups.",
                    source="baseline_style_analyzer",
                ),
                StyleSignal(
                    signal_name="phrase_word_count",
                    value=float(phrase_word_count),
                    interpretation=(
                        "Count of board entries that look like phrases rather than single words."
                    ),
                    source="baseline_style_analyzer",
                ),
            ],
            board_style_summary=BoardStyleSummary(
                board_archetype=archetype_label,
                mechanism_mix_profile=mechanism_mix_profile,
                evidence_interpretability=0.5,
                semantic_wordplay_balance=round(
                    mechanism_mix_profile.wordplay_group_count / max(len(group_types), 1),
                    3,
                ),
                label_consistency=0.8,
                archetype_diversity=round(unique_group_type_count / max(len(group_types), 1), 3),
                redundancy_score=0.0 if unique_group_type_count >= 3 else 0.4,
                monotony_score=0.0 if unique_group_type_count >= 3 else 0.6,
                coherence_trickiness_balance=round(1.0 - verification.ambiguity_score, 3),
                style_alignment_score=placeholder_score,
                metrics=metrics,
                notes=["Baseline style analysis still uses provisional demo heuristics."],
            ),
            mechanism_mix_profile=mechanism_mix_profile,
            notes=[
                "Baseline style analysis is intentionally provisional.",
                "Use these signals to inspect scaffolding, not to claim NYT-likeness.",
            ],
            metadata={"baseline_only": True},
        )


class HumanStyleAnalyzer(BaseStyleAnalyzer):
    """Interpretable Stage 3 style analyzer backed by local target bands."""

    analyzer_name = "human_style_analyzer"

    @staticmethod
    def _label_token_count(label: str) -> int:
        return len([token for token in label.replace("-", " ").replace('"', " ").split() if token])

    @classmethod
    def _group_archetype(cls, group) -> str:
        if group.group_type is GroupType.SEMANTIC:
            return "semantic_category"
        if group.group_type is GroupType.THEME:
            return "curated_theme"
        if group.group_type is GroupType.LEXICAL:
            pattern_type = group.metadata.get("pattern_type", "lexical_pattern")
            return f"lexical_{pattern_type}"
        pattern_type = group.metadata.get("phonetic_pattern_type", "phonetic_wordplay")
        return f"phonetic_{pattern_type}"

    @classmethod
    def _label_scores(cls, label: str) -> tuple[float, float]:
        token_count = cls._label_token_count(label)
        normalized_tokens = {token.lower() for token in label.replace("-", " ").split() if token}
        generic_penalty = 0.35 if normalized_tokens & GENERIC_LABELS else 0.0
        clarity = 1.0
        if token_count == 0:
            clarity = 0.0
        elif token_count == 1:
            clarity = 0.82
        elif token_count > 4:
            clarity = 0.58
        specificity = 0.85 if token_count <= 4 else 0.62
        return max(0.0, clarity - generic_penalty), max(0.0, specificity - generic_penalty)

    @staticmethod
    def _evidence_interpretability(group) -> float:
        evidence = group.metadata.get("evidence", {})
        score = 0.0
        if evidence:
            score += 0.45
        if group.metadata.get("rule_signature"):
            score += 0.2
        if group.metadata.get("shared_tags"):
            score += 0.15
        if group.group_type is GroupType.PHONETIC and evidence.get("pronunciation_membership"):
            score += 0.2
        elif group.group_type is GroupType.THEME and evidence.get("membership"):
            score += 0.15
        elif group.group_type is GroupType.LEXICAL and evidence.get("word_matches"):
            score += 0.15
        elif group.group_type is GroupType.SEMANTIC and evidence.get("member_scores"):
            score += 0.15
        return round(min(score, 1.0), 4)

    @classmethod
    def _group_summary(cls, group) -> GroupStyleSummary:
        label_clarity, label_specificity = cls._label_scores(group.label)
        evidence_interpretability = cls._evidence_interpretability(group)
        redundancy_flags: list[str] = []
        novelty_flags: list[str] = []
        clue_like_label = group_is_clue_like_label(group)
        taxonomy_like_label = group_is_taxonomy_like_label(group)
        if group.group_type is GroupType.PHONETIC:
            novelty_flags.append("wordplay_showcase")
        if group.group_type is GroupType.THEME:
            novelty_flags.append("curated_theme")
        if (
            group.group_type is GroupType.SEMANTIC
            and group.metadata.get("normalized_label") in GENERIC_LABELS
        ):
            redundancy_flags.append("generic_semantic_label")
        if taxonomy_like_label:
            redundancy_flags.append("taxonomy_like_label")
        if clue_like_label:
            novelty_flags.append("clue_like_label")

        return GroupStyleSummary(
            group_label=group.label,
            group_type=group.group_type.value,
            archetype=cls._group_archetype(group),
            label_token_count=cls._label_token_count(group.label),
            label_clarity=round(label_clarity, 4),
            label_specificity=round(label_specificity, 4),
            evidence_interpretability=evidence_interpretability,
            wordplay_indicator=(
                1.0
                if group.group_type is GroupType.PHONETIC
                else (0.6 if group.group_type is GroupType.LEXICAL else 0.0)
            ),
            redundancy_flags=redundancy_flags,
            novelty_flags=novelty_flags,
            notes=[f"Group archetype classified as {cls._group_archetype(group)}."],
            metadata={
                "source_strategy": group.source_strategy,
                "rule_signature": group.metadata.get("rule_signature"),
                "clue_like_label": clue_like_label,
                "taxonomy_like_label": taxonomy_like_label,
                "label_polish_applied": bool(group.metadata.get("label_polish_applied", False)),
                "phrase_payoff_score": round(group_phrase_template_payoff_score(group), 4),
            },
        )

    @staticmethod
    def _mechanism_mix_profile(puzzle: PuzzleCandidate) -> MechanismMixProfile:
        counts = Counter(group.group_type.value for group in puzzle.groups)
        total = max(len(puzzle.groups), 1)
        return MechanismMixProfile(
            counts=dict(sorted(counts.items())),
            shares={key: round(value / total, 4) for key, value in sorted(counts.items())},
            unique_group_type_count=len(counts),
            semantic_group_count=counts.get(GroupType.SEMANTIC.value, 0),
            lexical_group_count=counts.get(GroupType.LEXICAL.value, 0),
            phonetic_group_count=counts.get(GroupType.PHONETIC.value, 0),
            theme_group_count=counts.get(GroupType.THEME.value, 0),
            wordplay_group_count=counts.get(GroupType.LEXICAL.value, 0)
            + counts.get(GroupType.PHONETIC.value, 0),
            mixed_board=len(counts) > 1,
        )

    @staticmethod
    def _board_archetype(
        profile: MechanismMixProfile,
        *,
        formulaic_mix_score: float,
        editorial_payoff_score: float,
    ) -> str:
        if (
            profile.semantic_group_count >= 3
            or (
                profile.semantic_group_count >= 2
                and profile.wordplay_group_count <= 1
                and profile.theme_group_count <= 1
            )
        ):
            return "semantic_heavy"
        if (
            profile.unique_group_type_count >= 3
            and profile.theme_group_count >= 1
            and profile.wordplay_group_count >= 1
        ):
            return "balanced_mixed"
        if profile.wordplay_group_count >= 2 or profile.phonetic_group_count >= 1:
            return "wordplay_showcase"
        return "mixed_standard"

    @staticmethod
    def _metric_flag(comparison: StyleMetricComparison) -> str:
        return f"{comparison.metric_name}_{comparison.drift}"

    def analyze(
        self,
        puzzle: PuzzleCandidate,
        verification: VerificationResult,
        context: GenerationContext,
    ) -> StyleAnalysisReport:
        group_summaries = [self._group_summary(group) for group in puzzle.groups]
        mechanism_mix_profile = self._mechanism_mix_profile(puzzle)
        editorial_metadata = build_editorial_family_metadata(puzzle.groups)
        label_counts = [summary.label_token_count for summary in group_summaries]
        label_token_mean = mean(label_counts) if label_counts else 0.0
        label_token_std = pstdev(label_counts) if len(label_counts) > 1 else 0.0
        label_consistency = max(0.0, min(1.0, 1.0 - (label_token_std / 2.0)))
        base_label_naturalness_score = (
            mean(
                (summary.label_clarity + summary.label_specificity) / 2.0
                for summary in group_summaries
            )
            if group_summaries
            else 0.0
        )
        clue_like_label_count = float(
            sum(bool(summary.metadata.get("clue_like_label")) for summary in group_summaries)
        )
        taxonomy_like_label_count = float(
            sum(bool(summary.metadata.get("taxonomy_like_label")) for summary in group_summaries)
        )
        label_polish_applied = float(
            sum(bool(summary.metadata.get("label_polish_applied")) for summary in group_summaries)
        )
        label_naturalness_score = clamp_unit(
            base_label_naturalness_score
            + (0.06 * (clue_like_label_count / max(len(group_summaries), 1)))
            + (0.04 * (label_polish_applied / max(len(group_summaries), 1)))
            - (0.16 * (taxonomy_like_label_count / max(len(group_summaries), 1)))
        )
        evidence_interpretability = (
            mean(summary.evidence_interpretability for summary in group_summaries)
            if group_summaries
            else 0.0
        )
        semantic_wordplay_balance = mechanism_mix_profile.wordplay_group_count / max(
            mechanism_mix_profile.wordplay_group_count + mechanism_mix_profile.semantic_group_count,
            1,
        )
        archetype_diversity = len({summary.archetype for summary in group_summaries}) / max(
            len(group_summaries),
            1,
        )
        repeated_groups = sum(max(0, count - 1) for count in mechanism_mix_profile.counts.values())
        repeated_archetypes = sum(
            max(0, count - 1)
            for count in Counter(summary.archetype for summary in group_summaries).values()
        )
        redundancy_score = min(
            1.0,
            0.2 * repeated_groups + 0.15 * repeated_archetypes + (label_token_std * 0.1),
        )
        monotony_score = max(
            0.0,
            1.0 - (mechanism_mix_profile.unique_group_type_count / max(len(group_summaries), 1)),
        )
        trickiness_score = min(
            1.0,
            0.2 * mechanism_mix_profile.wordplay_group_count
            + 0.1 * mechanism_mix_profile.theme_group_count
            + float(verification.ambiguity_score),
        )
        coherence_score = max(0.0, 1.0 - float(verification.ambiguity_score))
        coherence_trickiness_balance = max(0.0, 1.0 - abs(coherence_score - trickiness_score))
        surface_wordplay_group_count = float(
            len(editorial_metadata["surface_wordplay_family_signatures"])
        )
        surface_wordplay_scores = [
            group_surface_wordplay_score(group)
            for group in puzzle.groups
            if group.group_type in {GroupType.LEXICAL, GroupType.PHONETIC}
        ]
        surface_wordplay_score = mean(surface_wordplay_scores) if surface_wordplay_scores else 0.0
        earned_wordplay_scores = [
            group_earned_wordplay_score(group)
            for group in puzzle.groups
            if group.group_type in {GroupType.LEXICAL, GroupType.PHONETIC}
        ]
        earned_wordplay_score = mean(earned_wordplay_scores) if earned_wordplay_scores else 0.0
        phrase_template_scores = [
            group_phrase_template_payoff_score(group) for group in puzzle.groups
        ]
        phrase_template_group_count = float(sum(score >= 0.7 for score in phrase_template_scores))
        phrase_payoff_score = mean(phrase_template_scores) if phrase_template_scores else 0.0
        microtheme_scores = [
            group_microtheme_smallness(group)
            for group in puzzle.groups
            if group.group_type is GroupType.THEME
        ]
        microtheme_smallness = mean(microtheme_scores) if microtheme_scores else 0.0
        low_payoff_pattern_flags = float(
            sum(
                group_surface_wordplay_score(group) >= 0.7
                and group_phrase_template_payoff_score(group) < 0.35
                for group in puzzle.groups
                if group.group_type in {GroupType.LEXICAL, GroupType.PHONETIC}
            )
        )
        clue_payoff_bonus_applied = clamp_unit(
            max(
                0.0,
                phrase_payoff_score
                - max(earned_wordplay_score, surface_wordplay_score * 0.65)
                - (0.08 * min(1.0, low_payoff_pattern_flags)),
            )
        )
        surface_wordplay_penalty_applied = clamp_unit(
            max(
                0.0,
                surface_wordplay_score
                - max(earned_wordplay_score, phrase_payoff_score)
                + (0.08 * min(1.0, low_payoff_pattern_flags / 2.0))
                + (0.08 * min(1.0, taxonomy_like_label_count / max(len(group_summaries), 1))),
            )
        )
        repeated_pattern_family_score = clamp_unit(
            max(0.0, len(editorial_metadata["low_payoff_surface_wordplay_families"]) - 1) / 2.0
        )
        formulaic_mix_score = clamp_unit(
            (0.42 if bool(editorial_metadata.get("balanced_mixed_board")) else 0.0)
            + (
                0.32
                * max(
                    0.0,
                    1.0 - min(1.0, mechanism_mix_profile.semantic_group_count / 3.0),
                )
            )
            + (0.24 * min(1.0, surface_wordplay_group_count))
            + (0.24 * microtheme_smallness)
            + (0.2 * surface_wordplay_penalty_applied)
            + (0.12 * min(1.0, taxonomy_like_label_count / max(len(group_summaries), 1)))
            + (0.12 * min(1.0, low_payoff_pattern_flags / 2.0))
            + (0.12 if "formulaic_mixed_template" in editorial_metadata["editorial_flags"] else 0.0)
            + (
                0.14
                if (
                    mechanism_mix_profile.semantic_group_count <= 1
                    and mechanism_mix_profile.theme_group_count >= 1
                    and mechanism_mix_profile.wordplay_group_count >= 1
                )
                else 0.0
            )
        )
        editorial_payoff_score = clamp_unit(
            (0.32 * label_naturalness_score)
            + (0.32 * evidence_interpretability)
            + (0.14 * max(earned_wordplay_score, phrase_payoff_score))
            + (0.18 * clue_payoff_bonus_applied)
            + (0.08 * (1.0 - microtheme_smallness))
        )
        family_repetition_risk = clamp_unit(
            (0.48 * formulaic_mix_score)
            + (0.28 * repeated_pattern_family_score)
            + (0.34 * microtheme_smallness)
            + (0.18 if bool(editorial_metadata.get("microtheme_plus_wordplay")) else 0.0)
        )
        editorial_flatness_score = clamp_unit(
            (0.48 * formulaic_mix_score)
            + (0.34 * surface_wordplay_score)
            + (0.18 * (1.0 - label_naturalness_score))
            + (0.12 * (1.0 - editorial_payoff_score))
            + (0.12 * min(1.0, taxonomy_like_label_count / max(len(group_summaries), 1)))
        )
        weak_label_naturalness_score = clamp_unit(1.0 - label_naturalness_score)
        family_saturation = clamp_unit(
            (0.62 * family_repetition_risk)
            + (0.38 * min(1.0, surface_wordplay_group_count / 2.0))
        )
        board_archetype = self._board_archetype(
            mechanism_mix_profile,
            formulaic_mix_score=formulaic_mix_score,
            editorial_payoff_score=editorial_payoff_score,
        )

        metrics = {
            "unique_group_type_count": float(mechanism_mix_profile.unique_group_type_count),
            "semantic_group_count": float(mechanism_mix_profile.semantic_group_count),
            "theme_group_count": float(mechanism_mix_profile.theme_group_count),
            "phonetic_group_count": float(mechanism_mix_profile.phonetic_group_count),
            "wordplay_group_count": float(mechanism_mix_profile.wordplay_group_count),
            "surface_wordplay_group_count": surface_wordplay_group_count,
            "label_token_mean": round(label_token_mean, 4),
            "label_token_std": round(label_token_std, 4),
            "label_naturalness_score": round(label_naturalness_score, 4),
            "clue_like_label_count": round(clue_like_label_count, 4),
            "taxonomy_like_label_count": round(taxonomy_like_label_count, 4),
            "label_polish_applied": round(label_polish_applied, 4),
            "evidence_interpretability": round(evidence_interpretability, 4),
            "semantic_wordplay_balance": round(semantic_wordplay_balance, 4),
            "coherence_trickiness_balance": round(coherence_trickiness_balance, 4),
            "ambiguity_score": round(float(verification.ambiguity_score), 4),
            "redundancy_score": round(redundancy_score, 4),
            "surface_wordplay_score": round(surface_wordplay_score, 4),
            "earned_wordplay_score": round(earned_wordplay_score, 4),
            "phrase_template_group_count": round(phrase_template_group_count, 4),
            "phrase_payoff_score": round(phrase_payoff_score, 4),
            "clue_payoff_bonus_applied": round(clue_payoff_bonus_applied, 4),
            "surface_wordplay_penalty_applied": round(surface_wordplay_penalty_applied, 4),
            "low_payoff_pattern_flags": round(low_payoff_pattern_flags, 4),
            "microtheme_smallness": round(microtheme_smallness, 4),
            "formulaic_mix_score": round(formulaic_mix_score, 4),
            "family_repetition_risk": round(family_repetition_risk, 4),
            "editorial_flatness_score": round(editorial_flatness_score, 4),
            "editorial_payoff_score": round(editorial_payoff_score, 4),
            "repeated_pattern_family_score": round(repeated_pattern_family_score, 4),
            "weak_label_naturalness_score": round(weak_label_naturalness_score, 4),
            "family_saturation": round(family_saturation, 4),
            "phrase_template_payoff_score": round(phrase_payoff_score, 4),
        }

        targets = load_style_targets()
        metric_targets = dict(targets.get("board_metrics", {}))
        style_alignment_band = metric_targets.pop("style_alignment_score", None)
        comparisons = compare_metric_dict_to_targets(metrics, metric_targets)
        critical_metric_weights = {
            "semantic_group_count": 2.5,
            "theme_group_count": 2.1,
            "wordplay_group_count": 2.4,
            "unique_group_type_count": 2.0,
            "surface_wordplay_score": 2.2,
            "formulaic_mix_score": 2.2,
            "family_saturation": 1.8,
            "editorial_flatness_score": 1.8,
            "label_token_mean": 1.2,
            "label_token_std": 1.1,
            "label_naturalness_score": 1.6,
            "clue_payoff_bonus_applied": 1.6,
            "taxonomy_like_label_count": 1.7,
        }
        total_weight = sum(
            critical_metric_weights.get(comparison.metric_name, 1.0)
            for comparison in comparisons
        )
        style_alignment_score = (
            round(
                sum(
                    critical_metric_weights.get(comparison.metric_name, 1.0)
                    if comparison.within_band
                    else 0.0
                    for comparison in comparisons
                )
                / max(total_weight, 1.0),
                4,
            )
            if comparisons
            else 0.0
        )
        metrics["style_alignment_score"] = style_alignment_score
        if style_alignment_band is not None:
            comparisons.extend(
                compare_metric_dict_to_targets(
                    {"style_alignment_score": style_alignment_score},
                    {"style_alignment_score": style_alignment_band},
                )
            )

        out_of_band_flags = [
            self._metric_flag(comparison)
            for comparison in comparisons
            if not comparison.within_band
        ]
        editorial_warning_flags: list[str] = []
        if formulaic_mix_score >= STAGE3_STYLE_VERIFIER_THRESHOLDS.formulaic_mix_warning_threshold:
            editorial_warning_flags.append("too_formulaic")
        if (
            family_repetition_risk
            >= STAGE3_STYLE_VERIFIER_THRESHOLDS.family_repetition_warning_threshold
        ):
            editorial_warning_flags.append("family_repetition")
        if (
            surface_wordplay_score
            >= STAGE3_STYLE_VERIFIER_THRESHOLDS.surface_wordplay_warning_threshold
        ):
            editorial_warning_flags.append("overly_surface_wordplay")
        if (
            editorial_flatness_score
            >= STAGE3_STYLE_VERIFIER_THRESHOLDS.editorial_flatness_borderline_threshold
        ):
            editorial_warning_flags.append("editorial_flatness")
        if (
            microtheme_smallness
            >= STAGE3_STYLE_VERIFIER_THRESHOLDS.microtheme_trivia_warning_threshold
        ):
            editorial_warning_flags.append("microtheme_trivia_smallness")
        if (
            weak_label_naturalness_score
            >= STAGE3_STYLE_VERIFIER_THRESHOLDS.weak_label_naturalness_warning_threshold
        ):
            editorial_warning_flags.append("weak_label_naturalness")
        if taxonomy_like_label_count >= 2:
            editorial_warning_flags.append("taxonomy_like_labels")
        out_of_band_flags = sorted(set(out_of_band_flags + editorial_warning_flags))
        board_style_summary = BoardStyleSummary(
            board_archetype=board_archetype,
            mechanism_mix_profile=mechanism_mix_profile,
            group_archetypes=[summary.archetype for summary in group_summaries],
            label_token_mean=round(label_token_mean, 4),
            label_token_std=round(label_token_std, 4),
            label_consistency=round(label_consistency, 4),
            evidence_interpretability=round(evidence_interpretability, 4),
            semantic_wordplay_balance=round(semantic_wordplay_balance, 4),
            archetype_diversity=round(archetype_diversity, 4),
            redundancy_score=round(redundancy_score, 4),
            monotony_score=round(monotony_score, 4),
            coherence_trickiness_balance=round(coherence_trickiness_balance, 4),
            style_alignment_score=style_alignment_score,
            group_family_signatures=list(editorial_metadata["group_family_signatures"]),
            board_family_signature=str(editorial_metadata["board_family_signature"]),
            editorial_family_signature=str(editorial_metadata["editorial_family_signature"]),
            editorial_flags=sorted(
                set(editorial_metadata["editorial_flags"] + editorial_warning_flags)
            ),
            out_of_band_flags=out_of_band_flags,
            notes=[
                (
                    "Stage 3 board style summary is built from interpretable "
                    "mechanism, label, ambiguity, and editorial-family signals."
                ),
            ],
            metrics=metrics,
        )
        style_signals = [
            StyleSignal(
                signal_name=metric_name,
                value=value,
                interpretation=(
                    "Observed board-level style metric compared against the Stage 3 reference band."
                ),
                source=self.analyzer_name,
            )
            for metric_name, value in sorted(metrics.items())
        ]

        return StyleAnalysisReport(
            analyzer_name=self.analyzer_name,
            archetype=PuzzleArchetypeSummary(
                label=board_archetype,
                rationale=(
                    "Archetype is inferred from the board's mechanism mix and the presence of "
                    "wordplay or theme groups."
                ),
                flags=out_of_band_flags,
            ),
            nyt_likeness=NYTLikenessPlaceholderScore(
                score=style_alignment_score,
                notes=[
                    "Stage 3 style alignment is a local calibration-band fit score.",
                    "It is not a claim that editorial style or NYT-likeness has been solved.",
                ],
            ),
            signals=style_signals,
            group_style_summaries=group_summaries,
            board_style_summary=board_style_summary,
            mechanism_mix_profile=mechanism_mix_profile,
            style_target_comparison=comparisons,
            out_of_band_flags=out_of_band_flags,
            notes=[
                "Style analysis is now an interpretable feature layer rather than a placeholder.",
                "Target bands remain local, explicit, and provisional.",
            ],
            metadata={
                "target_version": targets.get("version", "unknown"),
                "mixed_board": mechanism_mix_profile.mixed_board,
                "group_family_signatures": editorial_metadata["group_family_signatures"],
                "board_family_signature": editorial_metadata["board_family_signature"],
                "editorial_family_signature": editorial_metadata["editorial_family_signature"],
            },
        )
