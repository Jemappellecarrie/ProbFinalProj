"""Tests documenting intentionally unimplemented human-owned strategies."""

from __future__ import annotations

import pytest

from app.core.enums import GenerationMode
from app.domain.value_objects import GenerationContext
from app.features.human_feature_strategy import HumanCuratedFeatureExtractor
from app.generators.semantic import HumanSemanticGroupGenerator
from app.scoring.human_scoring_strategy import HumanOwnedPuzzleScorer
from app.schemas.feature_models import WordEntry


def test_human_feature_extractor_is_explicitly_unimplemented() -> None:
    extractor = HumanCuratedFeatureExtractor()
    with pytest.raises(NotImplementedError):
        extractor.extract_features(
            [WordEntry(word_id="w1", surface_form="TEST", normalized="test")]
        )


def test_human_semantic_generator_is_explicitly_unimplemented() -> None:
    generator = HumanSemanticGroupGenerator()
    context = GenerationContext(
        request_id="req_1",
        mode=GenerationMode.HUMAN_MIXED,
        demo_mode=False,
        include_trace=False,
        developer_mode=True,
    )
    with pytest.raises(NotImplementedError):
        generator.generate([], {}, context)


@pytest.mark.skip(
    reason="TODO[HUMAN_CORE]: replace with acceptance tests once the final ranking logic exists."
)
def test_human_scorer_acceptance_contract_placeholder() -> None:
    scorer = HumanOwnedPuzzleScorer()
    assert scorer.scorer_name == "human_owned_puzzle_scorer"
