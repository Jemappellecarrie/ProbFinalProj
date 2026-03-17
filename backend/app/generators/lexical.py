"""Lexical/pattern group generation strategies."""

from __future__ import annotations

from app.core.enums import GroupType
from app.domain.value_objects import GenerationContext
from app.generators.base import MockFeatureGroupedGenerator
from app.schemas.feature_models import WordEntry, WordFeatures
from app.schemas.puzzle_models import GroupCandidate


class MockLexicalGroupGenerator(MockFeatureGroupedGenerator):
    """Baseline lexical generator for demo mode."""

    group_type = GroupType.LEXICAL
    hint_key = "lexical"
    strategy_name = "mock_lexical_group_generator"


class HumanLexicalGroupGenerator(MockFeatureGroupedGenerator):
    """Placeholder for human-owned lexical group proposal logic.

    File location:
        backend/app/generators/lexical.py

    Expected inputs:
        - Seed words and extracted lexical features.

    Expected outputs:
        - Ranked `GroupCandidate` objects representing plausible lexical or
          orthographic pattern groups.

    Why unimplemented:
        The project-defining pattern-discovery heuristics should remain
        human-owned and research-driven.

    TODO[HUMAN_CORE]:
        Implement robust lexical grouping proposals.

    TODO[HUMAN_HEURISTIC]:
        Handle edge cases such as overlapping affixes, orthographic traps, and
        misleading superficial patterns that feel unlike NYT-quality puzzles.
    """

    group_type = GroupType.LEXICAL
    hint_key = "lexical"
    strategy_name = "human_lexical_group_generator"

    def generate(
        self,
        entries: list[WordEntry],
        features_by_word_id: dict[str, WordFeatures],
        context: GenerationContext,
    ) -> list[GroupCandidate]:
        raise NotImplementedError(
            "TODO[HUMAN_CORE]: implement lexical group proposal quality logic."
        )
