"""Theme and trivia group generation strategies."""

from __future__ import annotations

from app.core.enums import GroupType
from app.domain.value_objects import GenerationContext
from app.generators.base import MockFeatureGroupedGenerator
from app.schemas.feature_models import WordEntry, WordFeatures
from app.schemas.puzzle_models import GroupCandidate


class MockThemeGroupGenerator(MockFeatureGroupedGenerator):
    """Baseline theme generator for demo mode."""

    group_type = GroupType.THEME
    hint_key = "theme"
    strategy_name = "mock_theme_group_generator"


class HumanThemeGroupGenerator(MockFeatureGroupedGenerator):
    """Placeholder for the final theme/trivia generator.

    File location:
        backend/app/generators/theme.py

    Expected inputs:
        - Seed words and curated theme/trivia features.

    Expected outputs:
        - Theme-aware `GroupCandidate` objects with clear labels and provenance.

    TODO[HUMAN_CORE]:
        Implement real theme/trivia group proposal logic.

    TODO[HUMAN_DATA_CURATION]:
        Build the source-of-truth workflow for maintaining theme knowledge.

    TODO[HUMAN_HEURISTIC]:
        Decide how broad or narrow trivia categories may be before rejection.
    """

    group_type = GroupType.THEME
    hint_key = "theme"
    strategy_name = "human_theme_group_generator"

    def generate(
        self,
        entries: list[WordEntry],
        features_by_word_id: dict[str, WordFeatures],
        context: GenerationContext,
    ) -> list[GroupCandidate]:
        raise NotImplementedError(
            "TODO[HUMAN_CORE]: implement theme and trivia group proposal quality logic."
        )
