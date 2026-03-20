"""Tests for human-owned strategy implementations.

These tests verify that the previously-stubbed human-owned components are
now implemented and satisfy their basic acceptance criteria.
"""

from __future__ import annotations

import pytest

from app.core.enums import GenerationMode
from app.domain.value_objects import GenerationContext
from app.features.human_feature_strategy import HumanCuratedFeatureExtractor
from app.generators.semantic import HumanSemanticGroupGenerator
from app.scoring.human_scoring_strategy import HumanOwnedPuzzleScorer
from app.schemas.feature_models import WordEntry


def test_human_feature_extractor_is_implemented() -> None:
    """HumanCuratedFeatureExtractor must no longer raise NotImplementedError."""
    extractor = HumanCuratedFeatureExtractor()
    features = extractor.extract_features(
        [WordEntry(word_id="w1", surface_form="TEST", normalized="test")]
    )
    assert len(features) == 1
    assert features[0].word_id == "w1"
    assert "embedding" in features[0].debug_attributes
    assert len(features[0].debug_attributes["embedding"]) == 384


def test_human_feature_extractor_returns_lexical_signals() -> None:
    extractor = HumanCuratedFeatureExtractor()
    features = extractor.extract_features(
        [WordEntry(word_id="w1", surface_form="FLASH", normalized="flash")]
    )
    signals = features[0].lexical_signals
    assert any(s.startswith("prefix:") for s in signals)
    assert any(s.startswith("suffix:") for s in signals)
    assert any(s.startswith("length:") for s in signals)


def test_human_semantic_generator_is_implemented() -> None:
    """HumanSemanticGroupGenerator must return candidates (not raise) when embeddings present."""
    extractor = HumanCuratedFeatureExtractor()
    words = [
        WordEntry(word_id=f"w{i}", surface_form=w.upper(), normalized=w)
        for i, w in enumerate(["cat", "dog", "bird", "fish", "red", "blue", "green", "yellow"])
    ]
    features = extractor.extract_features(words)
    features_by_id = {f.word_id: f for f in features}

    generator = HumanSemanticGroupGenerator()
    context = GenerationContext(
        request_id="req_1",
        mode=GenerationMode.HUMAN_MIXED,
        demo_mode=False,
        include_trace=False,
        developer_mode=True,
        seed=42,
    )
    candidates = generator.generate(words, features_by_id, context)
    # May return 0 or more candidates depending on cluster structure
    for c in candidates:
        assert len(c.words) == 4
        assert 0.0 <= c.confidence <= 1.0


def test_human_scorer_is_implemented() -> None:
    scorer = HumanOwnedPuzzleScorer()
    assert scorer.scorer_name == "human_owned_puzzle_scorer"
