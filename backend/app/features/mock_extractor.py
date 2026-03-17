"""Baseline feature extraction used in demo mode.

This implementation is intentionally modest. It surfaces deterministic, auditable
signals from seed metadata and shallow string heuristics so the pipeline can run
without implying that the project-defining feature engineering has been solved.
"""

from __future__ import annotations

from app.features.base import BaseWordFeatureExtractor
from app.schemas.feature_models import WordEntry, WordFeatures


class MockWordFeatureExtractor(BaseWordFeatureExtractor):
    """Baseline feature extractor for demo mode."""

    extractor_name = "mock_word_feature_extractor"

    def extract_features(self, words: list[WordEntry]) -> list[WordFeatures]:
        records: list[WordFeatures] = []
        for entry in words:
            normalized = entry.normalized
            semantic_tags = list(entry.metadata.get("semantic_tags", []))
            lexical_signals = list(entry.metadata.get("lexical_signals", []))
            phonetic_signals = list(entry.metadata.get("phonetic_signals", []))
            theme_tags = list(entry.metadata.get("theme_tags", []))

            lexical_signals.extend(
                [
                    f"prefix:{self._prefix(normalized)}",
                    f"suffix:{self._suffix(normalized)}",
                    f"length:{len(normalized)}",
                ]
            )
            phonetic_signals.append(f"rhyme:{self._rhyme_signature(normalized)}")

            for hint_key, hint_value in entry.known_group_hints.items():
                if hint_key == "semantic":
                    semantic_tags.append(hint_value)
                elif hint_key == "lexical":
                    lexical_signals.append(f"bucket:{hint_value}")
                elif hint_key == "phonetic":
                    phonetic_signals.append(f"bucket:{hint_value}")
                elif hint_key == "theme":
                    theme_tags.append(hint_value)

            records.append(
                WordFeatures(
                    word_id=entry.word_id,
                    normalized=normalized,
                    semantic_tags=sorted(set(semantic_tags)),
                    lexical_signals=sorted(set(lexical_signals)),
                    phonetic_signals=sorted(set(phonetic_signals)),
                    theme_tags=sorted(set(theme_tags)),
                    extraction_mode="mock_demo",
                    provenance=["seed_metadata", "string_heuristics"],
                    debug_attributes={
                        "baseline_only": True,
                        "group_hints": entry.known_group_hints,
                    },
                )
            )
        return records
