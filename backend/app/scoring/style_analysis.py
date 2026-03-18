"""Style-analysis scaffold.

Role in pipeline:
    Attach lightweight, explicitly provisional style metadata to a puzzle so
    ranking, batch evaluation, and debug views can inspect style-oriented
    signals without claiming that true NYT-likeness has been solved.

Inputs:
    - `PuzzleCandidate`
    - `VerificationResult`
    - `GenerationContext`

Outputs:
    - `StyleAnalysisReport`

Why core logic is intentionally deferred:
    Real style calibration and NYT-likeness evaluation are project-defining and
    remain human-owned.

Acceptance criteria:
    - Demo mode emits transparent placeholder style signals.
    - Reports can flow through score payloads and batch summaries.
    - Human-owned style analysis remains stubbed.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.core.enums import GroupType
from app.domain.value_objects import GenerationContext
from app.schemas.evaluation_models import (
    NYTLikenessPlaceholderScore,
    PuzzleArchetypeSummary,
    StyleAnalysisReport,
    StyleSignal,
)
from app.schemas.puzzle_models import PuzzleCandidate, VerificationResult


class BaseStyleAnalyzer(ABC):
    """Strategy interface for provisional and future style analyzers."""

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
                    interpretation="Count of board entries that look like phrases rather than single words.",
                    source="baseline_style_analyzer",
                ),
            ],
            notes=[
                "Baseline style analysis is intentionally provisional.",
                "Use these signals to inspect scaffolding, not to claim NYT-likeness.",
            ],
            metadata={"baseline_only": True},
        )


class HumanStyleAnalyzer(BaseStyleAnalyzer):
    """Placeholder for the final human-owned style analysis.

    TODO[HUMAN_CORE]:
        Implement real style analysis and NYT-likeness judgment.

    TODO[HUMAN_RESEARCH]:
        Define which style signals should be calibrated against human examples.

    TODO[HUMAN_HEURISTIC]:
        Decide how style interacts with ambiguity and ranking policy.

    TODO[HUMAN_DATA_CURATION]:
        Curate any benchmark sets or editorial annotations needed for style work.
    """

    analyzer_name = "human_style_analyzer"

    def analyze(
        self,
        puzzle: PuzzleCandidate,
        verification: VerificationResult,
        context: GenerationContext,
    ) -> StyleAnalysisReport:
        raise NotImplementedError(
            "TODO[HUMAN_CORE]: implement human-owned style analysis."
        )
