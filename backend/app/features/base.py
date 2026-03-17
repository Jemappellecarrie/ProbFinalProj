"""Base classes for feature extraction strategies."""

from __future__ import annotations

from abc import ABC

from app.domain.protocols import WordFeatureExtractor


class BaseWordFeatureExtractor(WordFeatureExtractor, ABC):
    """Convenience base class for feature extractors."""

    extractor_name = "base_word_feature_extractor"

    @staticmethod
    def _prefix(word: str, length: int = 2) -> str:
        return word[:length]

    @staticmethod
    def _suffix(word: str, length: int = 2) -> str:
        return word[-length:]

    @staticmethod
    def _rhyme_signature(word: str, length: int = 3) -> str:
        return word[-length:]
