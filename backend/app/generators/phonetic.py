"""Phonetic and wordplay group generation strategies."""

from __future__ import annotations

from app.core.enums import GroupType
from app.domain.value_objects import GenerationContext
from app.generators.base import MockFeatureGroupedGenerator
from app.schemas.feature_models import WordEntry, WordFeatures
from app.schemas.puzzle_models import GroupCandidate


class MockPhoneticGroupGenerator(MockFeatureGroupedGenerator):
    """Baseline phonetic generator for demo mode."""

    group_type = GroupType.PHONETIC
    hint_key = "phonetic"
    strategy_name = "mock_phonetic_group_generator"


class HumanPhoneticGroupGenerator(MockFeatureGroupedGenerator):
    """Placeholder for the final phonetic/wordplay generator.

    File location:
        backend/app/generators/phonetic.py

    Pipeline role:
        Propose puzzle-worthy wordplay groups from phonetic and orthographic
        features while avoiding shallow or brittle rhyme-only artifacts.

    TODO[HUMAN_CORE]:
        Implement a real phonetic and wordplay proposal strategy.

    TODO[HUMAN_RESEARCH]:
        Choose phonetic encodings and pun/homophone resources.

    TODO[HUMAN_HEURISTIC]:
        Decide which wordplay families should be allowed, discouraged, or
        rejected for style consistency with the target puzzle family.
    """

    group_type = GroupType.PHONETIC
    hint_key = "phonetic"
    strategy_name = "human_phonetic_group_generator"

    def generate(
        self,
        entries: list[WordEntry],
        features_by_word_id: dict[str, WordFeatures],
        context: GenerationContext,
    ) -> list[GroupCandidate]:
        raise NotImplementedError(
            "TODO[HUMAN_CORE]: implement phonetic and wordplay group proposal logic."
        )
