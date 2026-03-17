"""Semantic group generation strategies.

File location:
    backend/app/generators/semantic.py

This module contains:
    - A baseline demo generator that groups words using explicit seed hints.
    - A human-owned generator placeholder for real semantic category proposal.

The human-owned strategy is intentionally unimplemented because semantic group
quality is a defining part of the final product.
"""

from __future__ import annotations

from app.core.enums import GroupType
from app.domain.value_objects import GenerationContext
from app.generators.base import MockFeatureGroupedGenerator
from app.schemas.feature_models import WordEntry, WordFeatures
from app.schemas.puzzle_models import GroupCandidate


class MockSemanticGroupGenerator(MockFeatureGroupedGenerator):
    """Baseline semantic generator for demo mode."""

    group_type = GroupType.SEMANTIC
    hint_key = "semantic"
    strategy_name = "mock_semantic_group_generator"


class HumanSemanticGroupGenerator(MockFeatureGroupedGenerator):
    """Placeholder for the final semantic grouping strategy.

    TODO[HUMAN_CORE]:
        Replace seed-hint grouping with real semantic category proposal logic.

    TODO[HUMAN_RESEARCH]:
        Decide how semantic ontologies, embeddings, and lexical resources should
        be combined or evaluated.

    TODO[HUMAN_HEURISTIC]:
        Design a proposal strategy that balances category coherence with puzzle
        freshness and human-recognizable category naming.

    Acceptance criteria:
        - Produces category candidates that are coherent to humans, not just
          nearest-neighbor artifacts.
        - Surfaces enough metadata for downstream ambiguity analysis.
        - Supports future ranking experiments without changing the interface.
    """

    group_type = GroupType.SEMANTIC
    hint_key = "semantic"
    strategy_name = "human_semantic_group_generator"

    def generate(
        self,
        entries: list[WordEntry],
        features_by_word_id: dict[str, WordFeatures],
        context: GenerationContext,
    ) -> list[GroupCandidate]:
        raise NotImplementedError(
            "TODO[HUMAN_CORE]: implement semantic group proposal quality logic."
        )
